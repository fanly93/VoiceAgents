# gstack iOS / Mobile Device Skills 分析报告

本报告基于本地 checkout `./.agents/skills/gstack`，范围限定为：

- `ios-qa/SKILL.md`
- `ios-fix/SKILL.md`
- `ios-design-review/SKILL.md`
- `ios-clean/SKILL.md`
- `ios-sync/SKILL.md`
- 直接引用的 iOS 文档和脚本：`docs/howto-ios-testing-with-gstack.md`、`ios-qa/docs/tailscale-acl-example.md`、`bin/gstack-ios-qa-daemon`、`bin/gstack-ios-qa-mint`、`ios-qa/daemon/src/*`、`ios-qa/scripts/gen-accessors*`、`ios-qa/templates/*`

## 总体架构

这组技能服务于真实 iPhone 上的 SwiftUI/iOS 应用测试，而不是模拟器、XCTest 或 WebDriverAgent。

核心链路：

1. iOS App 在 Debug 构建中嵌入 `DebugBridge` SPM 包。
2. App 内 `StateServer` 在设备侧启动 HTTP surface，端口默认 `9999`。
3. Mac 侧 `gstack-ios-qa-daemon` 通过 Xcode/CoreDevice USB IPv6 tunnel 访问设备。
4. 本地 agent 访问 Mac daemon 的 loopback listener，默认端口 `9099`。
5. 可选 `--tailnet` 模式让远程 agent 经 Tailscale 访问 Mac daemon，再由 daemon 转发到设备。

关键边界：

- iOS `StateServer` 受 `#if DEBUG` 和 SwiftPM Debug-only 依赖保护。
- Tailnet 入口只在 Mac daemon 层开放，iPhone 不直接暴露到 tailnet。
- Tailnet 请求按 capability 分层：`observe < interact < mutate < restore`。
- `@Snapshotable` 是状态快照白名单，未标记字段不会出现在 `/state/snapshot`。

一个实现细节值得注意：文档常说 `StateServer` 只绑定 `::1` 和 `127.0.0.1`，但当前 `StateServer.swift.template` 的实现为了支持 CoreDevice tunnel，实际用 `NWListener` 监听端口后按 peer address 过滤，只接受 loopback 或 RFC 4193 ULA (`fc00::/7`, `fd*`) 来源。安全意图仍是“不接受公网/局域网普通入口”，但描述上比“纯 loopback bind”更复杂。

## 共同前置条件

- macOS。
- Xcode 16.0+，`xcrun devicectl --version` 可运行。
- Swift toolchain，skill 要求 `swift --version >= 5.9`。
- Bun 在 `PATH` 上，Mac daemon 通过 `bun run ios-qa/daemon/src/index.ts` 启动。
- 真实 iPhone，iOS 16+，USB 连接，已配对、已信任，Developer Mode 已开启。
- Apple developer team ID。免费个人团队可用于 debug deploy，构建命令会使用 `-allowProvisioningUpdates -allowProvisioningDeviceRegistration`。
- App 源码在本机可读，且至少有一个 `@Observable` class；需要可快照字段时要标 `@Snapshotable`。
- 可选远程模式需要 Tailscale，且运行 daemon 的用户能读取 `/var/run/tailscale.sock`。

项目级使用时还要注意本仓库的 `AGENTS.md` 约束：手动运行 gstack 命令应带项目级 `HOME/GSTACK_HOME/GSTACK_STATE_DIR`，避免写入用户级目录。不过这些 skill 文件本身仍包含较多 `~/.claude/skills/gstack` 和 `~/.gstack` 路径，是生成后的通用内容。

## 相关 bin 命令

### `gstack-ios-qa-daemon`

用途：Mac 侧代理，连接 USB/CoreDevice 上的 iOS `StateServer`，并可选开放 tailnet listener。

入口：

```bash
gstack-ios-qa-daemon
gstack-ios-qa-daemon --tailnet
```

环境变量：

```bash
GSTACK_IOS_DAEMON_PORT=9099
GSTACK_IOS_TARGET_UDID=<device-udid>
GSTACK_IOS_TARGET_BUNDLE_ID=<bundle-id>
```

行为：

- 单实例，通过 `~/.gstack/ios-qa-daemon.pid` 控制。第二个进程会发现已有 daemon 并打印已有端口。
- ready 协议是 stdout 输出 `READY: port=<n> pid=<pid>`。
- loopback listener 绑定 `127.0.0.1`，并尽量绑定 `::1`。
- `--tailnet` 只有在 Tailscale LocalAPI probe 成功时才开放额外 listener；失败时 loopback 仍运行，tailnet fail closed。
- CLI 默认 bundle id 是 `com.gstack.iosqa.fixture`，真实项目通常要显式设置 `GSTACK_IOS_TARGET_BUNDLE_ID`。

### `gstack-ios-qa-mint`

用途：管理 tailnet allowlist，给远程 agent 授权。

示例：

```bash
gstack-ios-qa-mint grant --remote 'alice@example.com' --capability interact
gstack-ios-qa-mint grant --remote 'tag:ci' --capability mutate --ttl 86400 --note 'nightly run'
gstack-ios-qa-mint revoke --remote 'alice@example.com'
gstack-ios-qa-mint list
```

行为：

- allowlist 文件：`~/.gstack/ios-qa-allowlist.json`，写入 mode `0600`，目录 mode `0700`。
- `grant` 默认 capability 是 `interact`。
- self-service `/auth/mint` 不会自动 allowlist，必须先由 Mac owner 通过 CLI grant。

### `gstack-ios-qa-regen`

`ios-sync/SKILL.md` 提到可运行 `gstack-ios-qa-regen`，但当前 checkout 未找到对应 `bin/gstack-ios-qa-regen` 文件。可用的明确路径是文档中的 SwiftPM 工具：

```bash
swift run --package-path "$GSTACK_HOME/ios-qa/scripts/gen-accessors-tool" \
  gen-accessors --input "$APP_SOURCE_DIR" --output "$APP_SOURCE_DIR/DebugBridgeGenerated"
```

另有 TypeScript 版 `ios-qa/scripts/gen-accessors.ts`，用于更快解析常见情况和测试缓存逻辑，但 skill 文档首选 SwiftPM tool。

## `/ios-qa`

### 用途

真实 iPhone 上的 live-device QA。它读取 Swift 源码，生成 typed state accessors，安装 DebugBridge，部署 Debug app，然后运行“截图 -> 分析 -> 决策 -> 操作 -> 验证”的闭环。

触发语义：

- `ios qa`
- `test my iPhone app`
- `find bugs on the device`
- `qa the iOS app`

### 前置条件

- 共同前置条件全部满足。
- App 中有 `@Observable` class。
- 需要可恢复/可断言状态时，字段必须显式 `@Snapshotable`。
- 若远程 agent 要操作设备，Mac 需 Tailscale 登录，且 owner 已用 `gstack-ios-qa-mint` grant 对方 identity。

### 工作流

1. Warm start：如果 `~/.gstack/ios-qa-session.json` 存在且 daemon/device/accessor hash 仍有效，可跳过 bootstrap。
2. 读取源码：扫描 `@Observable`，识别 `@Snapshotable` 字段。
3. 生成 accessors：通过 `swift run --package-path $GSTACK_HOME/ios-qa/scripts/gen-accessors-tool gen-accessors --input <source-dir>`。
4. AskUserQuestion 确认是否安装 `DebugBridge` SPM dependency。
5. 修改 app：
   - 添加 `DebugBridge` SPM package。
   - App target Debug-only 依赖 `DebugBridgeUI`。
   - 在 `@main` App init 中 `#if DEBUG` 调用 `StateServer.shared.start()` 和 `DebugBridgeUIWiring.installAll()`。
6. 构建安装：`xcodebuild -scheme <SchemeName> -destination 'platform=iOS,id=<UDID>' build install`。
7. 启动：`devicectl device process launch --device <UDID> --console <bundle-id>`。
8. daemon 获取 boot token，立即调用 `/auth/rotate`，换成内存 token。
9. QA loop：
   - `GET /screenshot`
   - `GET /elements`
   - `GET /state/snapshot`
   - `POST /session/acquire`
   - `POST /tap`、`/swipe`、`/type` 或 `POST /state/<key>`
   - 重新截图，记录 bug
   - `POST /session/release`

### 能验证什么

- 真实设备上的渲染、布局、触控和键盘输入。
- SwiftUI Button 是否真正响应合成触摸。模板中的 Objective-C touch bridge 针对 iOS 18+ `_UIHitTestContext` 做了处理。
- 可访问性树和可见元素。
- `@Snapshotable` 状态字段的读取、局部写入、整快照 restore。
- USB/CoreDevice 隧道和 app 内 StateServer 是否联通。
- Debug 构建下的端到端用户流程。

### 不能验证什么

- 不能替代 Release/TestFlight/App Store 包的真实发布审计。
- 不覆盖未标记 `@Snapshotable` 的私有状态、token、PII 或 auth state。
- 不等同于 XCTest 单元/集成测试，不会天然覆盖无 UI 的纯逻辑路径。
- 不使用模拟器，因此不适合只在 CI 无设备环境跑。
- 对 iOS 17 或更早版本，文档列出 SwiftUI Button tap 可能因 `_UIHitTestContext` 不存在而无法触发，可能只能可靠操作 UIKit control。
- 远程模式只验证 tailnet 可达路径，不能证明公网安全配置无误。

### 编辑行为

- 可能编辑 `Package.swift`。
- 可能编辑 `@main` App 初始化入口。
- 写入 `DebugBridgeGenerated/` 或本地 `DebugBridge/` SPM package 文件。
- 写入生成的 accessor 文件和 `.gstack-version`。
- 不应修改业务逻辑，除非后续进入 `/ios-fix`。

### 生成物

- App 内 DebugBridge 源码：`StateServer.swift`、`DebugBridgeManager.swift`、`Bridges.swift`、`DebugOverlay.swift`、`DebugBridgeTouch.m/.h`、`Package.swift`。
- 生成 accessor：`StateAccessor.swift` 或 `DebugBridgeGenerated/*`。
- iOS 临时 boot token：`NSTemporaryDirectory()/gstack-ios-qa.token`，daemon rotate 后应被清理或失效。
- Mac session cache：`~/.gstack/ios-qa-session.json`。
- daemon pidfile：`~/.gstack/ios-qa-daemon.pid`。
- Tailnet allowlist：`~/.gstack/ios-qa-allowlist.json`。
- 安全日志：`~/.gstack/security/ios-qa-audit.jsonl` 和 `~/.gstack/security/attempts.jsonl`。

### 安全与风险

- `StateServer` 是 Debug-only，但仍是 app 内 HTTP 控制面。必须保证 Release build 不链接 `DebugBridge*`。
- boot token 会写临时文件并打一条公开 os_log；设计依赖 daemon 在约 5 秒内 rotate。
- Tailnet `/auth/mint` 对同 identity 有 10 次/60 秒限流。
- Tailnet body 上限 1MB，截图响应文档称有 10MB 上限。
- Mutating tailnet 请求会写 audit row；拒绝请求写 attempts row，attempt identity 使用 salted sha256 存储，避免直接记录 raw identity。
- Demo mode 禁止用 `/state/*` 跳步，必须通过可见 UI 操作，避免演示误导。

### 示例调用

```bash
# 本地 USB 模式
gstack-ios-qa-daemon

# 指定设备和 bundle
GSTACK_IOS_TARGET_UDID=<udid> \
GSTACK_IOS_TARGET_BUNDLE_ID=com.example.app \
gstack-ios-qa-daemon

# 远程 tailnet 模式
gstack-ios-qa-daemon --tailnet
gstack-ios-qa-mint grant --remote 'alice@example.com' --capability interact
```

在 Codex/gstack skill 层面的自然语言调用：

```text
/ios-qa test my iPhone app
/gstack-ios-qa qa the iOS app
```

### 非 iOS 项目何时忽略

如果项目不是 iOS/SwiftUI app、没有 Xcode 构建、没有真实 iPhone、没有 `@Observable` app state，或只需要 Web/Android/后端测试，应忽略 `/ios-qa`。

## `/ios-fix`

### 用途

接收 `/ios-qa` 找到的 bug，复现、定位、修改 Swift 源码、重建部署，并在真实设备上验证修复。核心规则是“没有 reproducing snapshot 就不修”。

### 前置条件

- `/ios-qa` 已安装并可运行。
- 真实设备和 daemon 可用。
- 有明确 bug finding：描述、截图、疑似 accessibility node 或状态路径。
- bug 可通过 UI 操作或 `@Snapshotable` 状态恢复复现。
- 项目允许 agent 编辑 Swift 源码和测试 fixture。

### 工作流

1. 读取 `/ios-qa` finding。
2. 将设备带入 bug 状态，方式可为 `/tap`、`/swipe`、`/type` 或 `POST /state/<key>`。
3. 捕获 pre snapshot：`test/fixtures/ios-fix/<bug-slug>-pre.json`。
4. 捕获 pre screenshot：`test/fixtures/ios-fix/<bug-slug>-pre.png`。
5. 记录一句 bug 描述和期望行为。
6. 读 Swift 源码，从 screen 追到 view model、data flow、state mutation，定位 root cause。
7. 最小化编辑 Swift 源码。
8. `xcodebuild ... build install`，重新部署，daemon 重连并 rotate token。
9. 用 pre snapshot restore，再截图验证。
10. 若修复成功，捕获 `<bug-slug>-post.png`。
11. 新增 `test/fixtures/ios-fix/<bug-slug>.test.ts`，用真实设备 gate `GSTACK_HAS_IOS_DEVICE=1`。

### 能验证什么

- bug 是否能由真实设备状态复现。
- 修复后同一 snapshot 恢复路径是否不再出现 bug。
- UI 层截图差异和可交互行为是否改善。
- Swift 编译和设备部署是否仍成功。

### 不能验证什么

- 不能验证未能 snapshot 的隐式状态。
- 不能保证所有相似 bug 都被覆盖，只覆盖当前 finding 和新增 regression fixture。
- 不能在没有设备时完成真实验证。
- 对需要服务端、推送、系统权限弹窗等外部条件的 bug，snapshot 可能不足以复现。

### 编辑行为

- 会编辑 Swift 源码，要求 diff minimal。
- 会写入 `test/fixtures/ios-fix/` 下的 JSON、PNG 和 `.test.ts`。
- 如果 build 失败，skill 要求 revert Swift edits 后先调查编译错误。
- 最多 3 次修复尝试；仍失败则停止并报告假设。

### 生成物

- `<bug-slug>-pre.json`
- `<bug-slug>-pre.png`
- `<bug-slug>-post.png`
- `<bug-slug>.test.ts`
- Swift 源码 diff
- 可能产生 daemon/security/session 相关运行日志

### 安全与风险

- `POST /state/restore` 需要高权限 capability，tailnet 场景应只给可信身份。
- fixture 只包含 `@Snapshotable` 字段，设计上避免 PII，但如果开发者误把敏感字段标记为 `@Snapshotable`，fixture 可能落盘敏感数据。
- 自动编辑源码前必须先有 reproducing snapshot，否则违反 skill 的 Iron Law。
- 真实设备自动操作可能改变本地 app 数据，建议用测试账号或可恢复状态。

### 示例调用

```text
/ios-fix fix this iOS bug from the latest /ios-qa report
/gstack-ios-fix patch the iPhone app
```

### 非 iOS 项目何时忽略

如果没有 `/ios-qa` finding、没有 iOS Swift 源码、没有真实设备，或 bug 属于 Web/后端/Android，应忽略 `/ios-fix`。

## `/ios-design-review`

### 用途

在真实 iPhone 上做视觉设计审计。它复用 `/ios-qa` 的 daemon 和 StateServer，逐屏截图并按 iOS 设计维度评分，输出 markdown 报告。

### 前置条件

- `/ios-qa` bridge/daemon 可用；如果 daemon 不在运行，按 `/ios-qa` Phase 0-2 启动。
- App 可在真实 iPhone 上打开到待审屏幕。
- 最好有 screen list；没有时通过 accessibility tree 自动发现主要屏幕。
- 若 tailnet 调用，token 至少要 `observe` capability。
- 若项目有 `DESIGN.md`，skill 会将其与 Apple HIG 和设计最佳实践一起参考。

### 工作流

1. 连接或启动 `gstack-ios-qa-daemon`。
2. `POST /session/acquire`，以 observe/read-only 意图运行。
3. 对每个主要 screen：
   - `GET /screenshot`
   - `GET /elements`
   - 按 10 个维度评分
   - 记录发现
4. 对任何低于 7 分的问题，用 AskUserQuestion 让用户决定是否处理。
5. 输出 markdown 报告到 `~/.gstack/projects/<slug>/ios-design-review-<date>.md`，内嵌截图。

评分维度：

- Typography hierarchy
- Spacing rhythm
- Color hierarchy
- Touch targets
- Loading / empty / error states
- Accessibility
- Animation discipline
- iOS idiom alignment
- Information density
- AI-slop check

### 能验证什么

- 真实设备截图下的视觉层级、间距、颜色、暗色模式迹象。
- 触控目标是否达到 44x44pt。
- VoiceOver label 等 accessibility tree 可见问题。
- 动态类型、Reduce Motion、空态/加载/错误态的可见设计问题。
- 是否符合 iOS idiom，例如 `NavigationStack`、`List`、`Form`、system sheet 等。

### 不能验证什么

- 读屏器完整体验只能从 accessibility metadata 推断，不能完全代替人工 VoiceOver QA。
- 如果没有触发某些状态或隐藏屏幕，报告可能漏掉对应 screen。
- 读-only 默认不修 UI，也不证明设计修改后的结果。
- 不适用于 web visual audit；web 应用应使用 `/design-review`。

### 编辑行为

- 默认只读，不做 mutating calls。
- skill allowed-tools 不含 `Edit/Write`，但会输出报告到 `~/.gstack/projects/...`。
- 对低分项通过 AskUserQuestion 提供建议，不自动改源码。

### 生成物

- `~/.gstack/projects/<slug>/ios-design-review-<date>.md`
- 报告内联或引用的 screenshots
- 可能产生 daemon/session 日志

### 安全与风险

- Tailnet observe token 也能读取截图和 accessibility tree，可能包含用户数据；只授予可信 reviewer。
- 截图报告写入 `~/.gstack/projects`，若启用 artifacts sync/gbrain，可能被同步到私有 artifacts repo；需要注意隐私。
- 黑屏/空白截图不应直接判定 UI 失败，skill 要求向用户确认 app 是否处于预期状态。

### 示例调用

```text
/ios-design-review review the iOS design
/gstack-ios-design-review audit the iPhone app visuals
```

远程只读授权示例：

```bash
gstack-ios-qa-mint grant --remote 'tag:designer' --capability observe
```

### 非 iOS 项目何时忽略

如果没有 iOS app、没有真实设备截图需求，或目标是浏览器页面、Android、桌面应用，应忽略 `/ios-design-review`。

## `/ios-clean`

### 用途

从 iOS app 中移除 DebugBridge 相关 instrumentation。skill 明确说它是 convenience flow，不是安全机制；真正防止 shipping 的关键是 `Package.swift` Debug-only guard 和 Release 构建/符号检查。

### 前置条件

- 项目曾安装 DebugBridge 或手动复制过相关文件。
- 有可编辑的 iOS app 源码。
- 最好有 git 工作区，便于回滚。
- 若要清理设备临时 token，需要 iPhone 连接。
- 能运行 Release build 和 `nm`。

### 工作流

1. Inventory：
   - 搜索 `import DebugBridge`
   - 搜索 `#if DEBUG ... DebugBridgeManager` blocks
   - 搜索 `// Auto-generated state accessor` 或 `StateAccessor.swift`
   - 解析 `Package.swift` 中 DebugBridge dependency
   - 展示待删除文件和行数，AskUserQuestion 选择 proceed/dry-run/abort
2. Remove：
   - 删除 import 和 `#if DEBUG` wiring
   - 从 `Package.swift` 删除 `.package(...DebugBridge...)` 和 target dependency
   - 删除生成的 `StateAccessor.swift`
   - best-effort 删除设备 `NSTemporaryDirectory()/gstack-ios-qa.token`
3. Verify：
   - `! grep -r "DebugBridge" <app-source-dir>`
   - `! grep -r "@Snapshotable" <app-source-dir>`
   - `swift build -c release`
   - `nm -j` 确认 built binary 没有 DebugBridge symbols

### 能验证什么

- 源码中是否还残留 `DebugBridge` / `@Snapshotable` 字符串。
- Release build 是否不再需要 DebugBridge。
- 二进制符号表是否没有 DebugBridge symbols。

### 不能验证什么

- 不能证明所有测试/QA 工具链都已从项目管理文档或 CI 配置中移除。
- grep 可能遗漏改名或间接包装的桥接逻辑。
- best-effort 设备 token 删除依赖设备在线。
- 不能替代 App Store/TestFlight 包的最终安全审计。

### 编辑行为

- 每项删除前都要求 AskUserQuestion 确认。
- 使用 Edit 删除源文件中的 import 和 Debug block。
- 删除生成的 accessor 文件。
- 不碰业务逻辑、view model、view code。
- 不碰 `#if DEBUG` 外的代码。
- 不 force push、不 amend、不删除 SPM cache。

### 生成物

- 主要是删除/清理 diff。
- Release build 产物用于验证。
- 可能的验证命令输出摘要。

### 安全与风险

- 这是发布前清理工具，但 skill 自身承认不是 safety-critical path。
- 真正要依赖 `.when(configuration: .debug)`、`swift build -c release` 和 `nm` 检查。
- 删除 `@Snapshotable` wrapper 可能影响后续 `/ios-qa` 或 `/ios-fix` 的状态恢复能力。
- 如果用户手动改过 DebugBridge 文件，清理可能不完整，失败时必须停下报告。

### 示例调用

```text
/ios-clean remove DebugBridge
/gstack-ios-clean strip the gstack iOS instrumentation
```

典型验证命令：

```bash
swift build -c release
nm -j <built-binary> | grep DebugBridge
```

### 非 iOS 项目何时忽略

如果项目从未安装 DebugBridge，或不是 iOS/SwiftPM/Xcode 项目，应忽略 `/ios-clean`。Web/后端项目不需要这个清理。

## `/ios-sync`

### 用途

在已安装 `/ios-qa` 的 app 中重新生成 DebugBridge 和 state accessor，适用于升级 gstack、添加新的 `@Observable` / `@Snapshotable` 字段，或同步上游模板修复。

### 前置条件

- App 已经安装过 `/ios-qa` DebugBridge。
- 存在 app source dir 和 `DebugBridgeGenerated` 或等价安装目录。
- 能访问 `$GSTACK_HOME/ios-qa/templates/`，或者开发 gstack 自身时访问 worktree 的 `ios-qa/templates/`。
- SwiftPM generator 可运行。
- 能运行 `swift build`、`xcodebuild` 并重新连接真实设备。

### 工作流

1. 检测版本：
   - 读 `<app>/DebugBridgeGenerated/.gstack-version`
   - 读上游 `$GSTACK_HOME/ios-qa/.gstack-version`
   - 若版本相同且没有新的 `@Observable`，直接退出
2. 重新生成 accessors：
   - 文档提到 `gstack-ios-qa-regen`
   - 当前 checkout 未发现该 bin，实际可用路径是 SwiftPM `gen-accessors`
3. 更新模板 Swift 文件：
   - 比较 `<app>/DebugBridgeGenerated/<Name>.swift`
   - 比较 `$GSTACK_HOME/ios-qa/templates/<Name>.swift.template`
   - 有 `// GSTACK-EDIT-LINE` marker 时将用户编辑 forward
   - 否则非平凡 diff 前 AskUserQuestion，之后整体替换
4. 验证：
   - `swift build`
   - `xcodebuild -scheme <SchemeName>`
   - 重新 launch app，daemon 连接并 rotate token
   - `GET /state/snapshot` 返回新的 accessor schema hash

### 能验证什么

- 生成器是否能覆盖新增 `@Snapshotable` 字段。
- DebugBridge 模板是否能在当前项目编译。
- daemon/token rotation 是否仍可用。
- state snapshot schema hash 是否更新。

### 不能验证什么

- 如果新增属性未标 `@Snapshotable`，schema 不变是预期，不代表 generator 失败。
- 不会自动判断业务状态设计是否合理。
- 不能验证 Release 安全清理；那是 `/ios-clean` 和 Release invariant 的职责。
- 当前文档提到的 `gstack-ios-qa-regen` 命令在 checkout 中缺失，自动化入口可能不完整。

### 编辑行为

- 会写入/替换 generated accessor。
- 会更新 templated Swift files。
- 会在非平凡替换前询问。
- 有 marker 时保留并 forward 用户编辑。
- 失败时建议 `git restore` 回滚并向用户展示 compile error。

### 生成物

- 更新后的 `DebugBridgeGenerated/*`
- 新 accessor schema hash
- 可能更新 `.gstack-version`
- 重新生成的 `StateAccessor.swift`

### 安全与风险

- 同步模板可能覆盖用户手动修改；只有带 `// GSTACK-EDIT-LINE` marker 的编辑会被 forward。
- 重新生成可能改变 snapshot schema，旧 fixture restore 时可能出现 `409 schema_mismatch`。
- `--input` 递归扫描，若包含 test fixtures，可能误纳入源；文档建议用 `--exclude`。
- 仍必须依赖 Debug-only guard，避免同步后的 DebugBridge 进入 Release。

### 示例调用

```text
/ios-sync regenerate iOS accessors
/gstack-ios-sync update the gstack iOS instrumentation
```

底层生成器示例：

```bash
swift run --package-path "$GSTACK_HOME/ios-qa/scripts/gen-accessors-tool" \
  gen-accessors --input "$APP_SOURCE_DIR" --output "$APP_SOURCE_DIR/DebugBridgeGenerated"
```

### 非 iOS 项目何时忽略

如果项目没有安装 `/ios-qa`、没有 SwiftUI `@Observable`/`@Snapshotable` 状态、不是 iOS app，或当前问题与移动设备无关，应忽略 `/ios-sync`。

## 远程/Tailscale 模式安全模型

`ios-qa/docs/tailscale-acl-example.md` 和 daemon 代码共同定义了远程访问模型：

- iPhone `StateServer` 不直接开放 tailnet。
- Mac daemon 是唯一 tailnet ingress。
- Tailnet listener 只在 `--tailnet` 且 `/var/run/tailscale.sock` probe 成功时启动。
- WhoIs 通过 tailscaled LocalAPI canonicalize identity。
- allowlist 是 `~/.gstack/ios-qa-allowlist.json`。
- endpoint allowlist 在 `types.ts`：
  - `observe`: `/healthz`、`/screenshot`、`/elements`、`GET /state/*`
  - `interact`: observe + session acquire/release/heartbeat、`/tap`、`/swipe`、`/type`
  - `mutate`: interact + `POST /state/*`
  - `restore`: mutate + `POST /state/restore`
- `/auth/mint` 每 identity 10 次/60 秒限流。
- token 默认 1 小时，最大 24 小时。
- mutating tailnet 请求写 `ios-qa-audit.jsonl`。
- 拒绝请求写 `attempts.jsonl`。

建议：

- 设计审计只给 `observe`。
- 普通远程 QA 给 `interact`。
- CI 或自动恢复测试才给 `mutate`。
- `restore` 等同完整状态恢复能力，应只给高度可信身份。

## 与发布安全相关的结论

这些 skill 的设计强调 Debug-only：

- `Package.swift.template` 要求 consuming target dependency 使用 `.when(configuration: .debug)`。
- `DebugOverlay.swift.template`、`StateServer.swift.template`、`Bridges.swift.template` 等都被 `#if DEBUG` 包围。
- Release safety 不能只靠 `/ios-clean`，还要跑 release build 和 symbol 检查。
- `/ios-clean` 是整理 diff 的工具，不是唯一安全边界。

发布前最小检查：

```bash
swift build -c release
grep -r "DebugBridge" <app-source-dir>
grep -r "@Snapshotable" <app-source-dir>
nm -j <built-binary> | grep DebugBridge
```

## 非 iOS 项目的总判断

非 iOS 项目通常应忽略这一组技能。适用条件非常具体：macOS + Xcode + 真实 iPhone + SwiftUI/iOS app + DebugBridge instrumentation。以下情况不应调用：

- Web 应用：使用 `/qa`、`/qa-only`、`/design-review`。
- 后端/API：使用测试、`/investigate`、`/review`。
- Android/React Native 非 iOS 原生路径：这组技能不能直接驱动。
- 没有真实 iPhone 或无法 USB 连接的环境。
- 只需要静态代码审查，不需要真实设备交互。

## 源文件清单

- `.agents/skills/gstack/ios-qa/SKILL.md`
- `.agents/skills/gstack/ios-fix/SKILL.md`
- `.agents/skills/gstack/ios-design-review/SKILL.md`
- `.agents/skills/gstack/ios-clean/SKILL.md`
- `.agents/skills/gstack/ios-sync/SKILL.md`
- `.agents/skills/gstack/docs/howto-ios-testing-with-gstack.md`
- `.agents/skills/gstack/ios-qa/docs/tailscale-acl-example.md`
- `.agents/skills/gstack/bin/gstack-ios-qa-daemon`
- `.agents/skills/gstack/bin/gstack-ios-qa-mint`
- `.agents/skills/gstack/ios-qa/daemon/src/index.ts`
- `.agents/skills/gstack/ios-qa/daemon/src/types.ts`
- `.agents/skills/gstack/ios-qa/daemon/src/allowlist.ts`
- `.agents/skills/gstack/ios-qa/daemon/src/cli-mint.ts`
- `.agents/skills/gstack/ios-qa/daemon/src/session-tokens.ts`
- `.agents/skills/gstack/ios-qa/daemon/src/proxy.ts`
- `.agents/skills/gstack/ios-qa/daemon/src/audit.ts`
- `.agents/skills/gstack/ios-qa/daemon/src/devicectl.ts`
- `.agents/skills/gstack/ios-qa/scripts/gen-accessors.ts`
- `.agents/skills/gstack/ios-qa/scripts/gen-accessors-tool/Sources/GenAccessors/main.swift`
- `.agents/skills/gstack/ios-qa/templates/Package.swift.template`
- `.agents/skills/gstack/ios-qa/templates/StateServer.swift.template`
- `.agents/skills/gstack/ios-qa/templates/DebugOverlay.swift.template`
- `.agents/skills/gstack/ios-qa/templates/Bridges.swift.template`
- `.agents/skills/gstack/ios-qa/templates/DebugBridgeTouch.m.template`
- `.agents/skills/gstack/ios-qa/templates/StateAccessor.swift.template`
