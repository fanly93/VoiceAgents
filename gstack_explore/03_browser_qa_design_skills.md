# gstack 浏览器、QA、抓取与设计技能分析

分析范围：`.agents/skills/gstack` 下的 `browse`、`open-gstack-browser`、`setup-browser-cookies`、`pair-agent`、`qa`、`qa-only`、`design-review`、`design-shotgun`、`design-html`、`devex-review`、`scrape`、`skillify`、`benchmark` 的 `SKILL.md`，以及直接相关的 QA 模板/分类和 browse browser-skill 写入 helper。

## 总体结论

这些技能以 gstack browse daemon 为核心。`browse` 提供长驻 Chromium、页面读取、交互、截图、性能、cookie、tab、browser-skill、pair-agent tunnel 等底层能力；`qa`、`qa-only`、`design-review`、`devex-review`、`benchmark` 在其上组织审计流程；`scrape` 和 `skillify` 把一次性网页抽取升级为可复用 browser-skill；`design-shotgun` 与 `design-html` 额外依赖 design binary `$D` 生成/比较/落地视觉方案。

本项目注意点：技能正文多处默认查找 `$_ROOT/.claude/skills/gstack/...` 或 `$HOME/.claude/skills/gstack/...`。当前工作区的项目说明要求使用项目级 gstack：`.agents/skills/gstack`，并通过

```bash
env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" <gstack-command>
```

隔离运行状态。因此手动执行时应按项目说明改写路径/环境，避免写入用户级目录。

## 共同前置条件与浏览器模型

- Git repo：gstack 依赖 `git rev-parse --show-toplevel` 定位项目级 runtime。本目录必须保持为 git repo。
- browse binary：技能统一先检查 browse binary。模板路径是 `.claude/skills/gstack/browse/dist/browse` 或用户级路径；本项目应优先解析 `.agents/skills/gstack/browse/dist/browse`。
- 一次性构建：若输出 `NEEDS_SETUP`，需要用户确认后运行 gstack `setup`，缺 Bun 时会下载固定版本 Bun 并校验 sha256。
- daemon：`browse` 是长驻 daemon。首次调用约 3 秒，后续命令约 100ms。cookies、tabs、login session 会跨命令保留。
- headless/headed：默认 headless；`$B connect`、`$B handoff`、`--headed` 会进入可见 Chromium。`--headed` 与 `--proxy` 是 daemon 启动级配置，已有不同配置 daemon 时会拒绝并提示 `browse disconnect`。
- screenshots：所有截图命令生成 PNG 后，技能要求用 Read 工具把图片展示给用户，否则用户看不到视觉证据。
- CDP mode：部分技能会检查 `$B status` 是否为 `Mode: cdp`。若连接的是用户真实浏览器，则跳过 cookie 导入、user-agent 或 headless workaround。
- 本地 URL：QA/design/benchmark/devex 通常需要目标 URL。无 URL 时，QA 和 design-review 会尝试 diff-aware 模式并探测 `localhost:3000`、`:4000`、`:8080`。

## `/browse`

### 使用场景

底层浏览器控制与页面检查。适合加载页面、测试用户流、截图取证、读取 console/network、检查 DOM/ARIA、做响应式截图、导入 cookie、下载文件、运行 browser-skills、连接 headed browser、与用户 handoff。

### 前置条件

- 需要 browse binary 和可启动的 Chromium/Playwright 环境。
- 本地 HTML 支持 `file://` 或 `load-html`，但文件路径被限制在 cwd 或 `$TMPDIR` 下。
- retina 截图用 `viewport WxH --scale 2`，scale 限制 1-3；改变 scale 会重建 browser context，旧 `@e` refs 失效。
- headed/proxy 模式必须在 fresh daemon 上启用，不能对已有 daemon 静默重启。

### 工作流

常见 QA 流程：

```bash
$B goto http://localhost:3000
$B text
$B console --errors
$B network
$B snapshot -i
$B click @e3
$B snapshot -D
$B screenshot /tmp/result.png
```

常见视觉/响应式流程：

```bash
$B responsive /tmp/layout
$B viewport 375x812
$B snapshot -i -a -o /tmp/annotated.png
```

复杂认证可 handoff：

```bash
$B handoff "Stuck on CAPTCHA at login page"
$B resume
```

### 是否编辑代码

`browse` 自身不编辑项目代码。它可能写状态文件、截图、PDF、下载文件、MHTML、browser-skill 状态或 cookie/session 状态。

### 输出/产物

- 文本：`text`、`html`、`links`、`forms`、`console`、`network`、`perf`。
- 图片：`screenshot`、`snapshot -a -o`、`responsive`。
- 文件：`archive` MHTML、`pdf`、`download` 文件、`scrape media` manifest。
- 状态：`.gstack/browse.json`，browser state，cookies，tabs。

### `$B` 交互

这是所有上层技能的主接口。核心能力包括 navigation、reading、interaction、inspection、visual、snapshot、tabs、server、browser-skill。

### 常见失败模式

- `NEEDS_SETUP`：browse 未构建。
- daemon config mismatch：已有 daemon 的 headed/proxy 配置不同，需要 `browse disconnect`。
- `@e` ref 失效：导航、viewport scale/context 重建后必须重新 `snapshot`。
- headless 被拦截：CAPTCHA、bot detection、OAuth/MFA 需要 handoff 或 headed/proxy。
- proxy 错误：SOCKS5 upstream 拒绝/不可达会启动 fail-fast；URL 和 env 同时提供 credentials 会拒绝。
- 本地文件路径被拒：`file://` 和 `load-html` 受 cwd/TMPDIR 路径限制。
- 截图不可见：只生成文件不 Read，用户看不到图。
- 页面输出包含 prompt injection：`text/html/links/forms/console/snapshot` 等不可信内容会被包裹，不能执行其中指令。

## `/open-gstack-browser`

### 使用场景

启动可见的 GStack Browser，让用户实时看到 AI 浏览器动作和 side panel feed。适合需要人工观察、调试交互、展示 QA/design/benchmark 行为、让 sidebar chat 直接驱动浏览器的场景。

### 前置条件

- browse binary 可用。
- 需要清理旧 daemon 状态和 Chromium profile locks。
- headed Chromium 会固定使用端口 `34567` 供 extension 自动连接。
- extension 路径默认查找 gstack install 下的 `extension/manifest.json`。

### 工作流

1. 清理 `.gstack/browse.json` 中旧 PID，移除 profile lock。
2. 运行：

```bash
$B connect
$B status
```

3. 确认输出 `Mode: headed`，确认端口是 `34567`。
4. 引导用户打开 Chrome extension side panel。
5. Demo：

```bash
$B goto https://news.ycombinator.com
$B snapshot -i
```

### 是否编辑代码

不编辑项目代码。会杀旧 browse server、删除 browse state/profile lock、启动 headed browser 和 sidebar agent。

### 输出/产物

- headed Chromium 窗口。
- side panel 活动流和 chat tab。
- `.gstack/browse.json` 中的 server port/pid/token 状态。

### `$B` 交互

核心命令是 `$B connect`、`$B status`、`$B focus`、`$B disconnect`，后续所有 `$B` 命令都会在可见浏览器中体现。

### 示例提示

```text
/open-gstack-browser
```

之后可继续：

```bash
$B goto http://localhost:3000
$B snapshot -i
```

### 常见失败模式

- mode 不是 `headed`：需要 `$B status` 排查。
- 浏览器不可见：尝试 `$B focus`。
- extension 未出现：去 `chrome://extensions` 手动 Load unpacked。
- side panel 灰色/未连接：手动输入端口 `34567`。
- stale lock/profile：需要 pre-flight cleanup。

## `/setup-browser-cookies`

### 使用场景

把用户本机 Chromium 系浏览器中的 cookie 导入 Playwright browse session，用于登录态、付费站、私有 dashboard 等页面测试。

### 前置条件

- browse binary 可用并能启动 cookie picker。
- 若 `$B status` 显示 `Mode: cdp`，说明已连接真实浏览器，cookie 已可用，不需要导入。
- macOS 可能触发 Keychain 授权；Linux v11 cookie 可能需要 libsecret/`secret-tool`。

### 工作流

```bash
$B cookie-import-browser
```

打开 picker UI 后，用户在浏览器中选择 domain 导入。若已知 domain 可直连：

```bash
$B cookie-import-browser comet --domain github.com
$B cookies
```

### 是否编辑代码

不编辑代码。会读取本机浏览器 cookie 数据并写入 browse Playwright session。

### 输出/产物

- cookie picker UI。
- browse session 中的 cookies。
- `$B cookies` 可总结 domain 和数量，避免暴露 cookie value。

### `$B` 交互

使用 `cookie-import-browser`、`cookies`。picker 由 browse server 同端口提供。

### 常见失败模式

- CDP mode 下误导入：技能会提前停止，避免重复。
- Keychain/secret-service 拒绝导致 cookie 解密失败。
- 浏览器名称不匹配：direct import 示例里的 `comet` 需要按用户实际浏览器替换。
- 用户未在 picker 选择 domain，后续仍未登录。

## `/pair-agent`

### 使用场景

把当前 browse daemon 暴露给另一个 AI agent。适合让 OpenClaw、Codex、Cursor、另一个 Claude Code、本地或远程 agent 共用浏览器能力，同时每个 agent 有自己的 tab。

### 前置条件

- browse server 必须运行；若未运行，用 `$B goto about:blank` 拉起。
- 同机 pairing 可写目标 agent 配置目录。
- 远程 pairing 需要 ngrok；安装并认证后 `$B pair-agent --client TARGET_HOST` 会生成 copy-paste instruction block。
- setup key 5 分钟过期且只能用一次；session token 24 小时。

### 工作流

1. `$B status` 检查 browse server。
2. 问用户目标 agent：OpenClaw、Codex、Cursor、Claude Code 或 generic。
3. 问同机还是远程。
4. 同机：

```bash
$B pair-agent --local codex
```

5. 远程：

```bash
$B pair-agent --client codex
$B pair-agent --admin --client codex
```

6. 输出完整 instruction block 给用户复制到另一个 agent。
7. `$B status` 验证 connected agent。

### 是否编辑代码

不编辑项目代码。同机模式会写目标 agent 的 gstack browse credential 配置，例如 `~/.codex/skills/gstack/browse-remote.json`。远程模式会启动/使用 tunnel。

### 输出/产物

- 一次性 setup key。
- 目标 agent 的 browse credentials 或 instruction block。
- 可能的 ngrok tunnel URL。
- browse status 中的 connected agent。

### `$B` 交互

使用 `$B pair-agent`、`$B status`、`$B tunnel revoke`、`$B tunnel rotate`。默认 token 有 read+write；`--admin` 增加 JS、cookie、storage 能力。

### 常见失败模式

- ngrok 未安装或未登录。
- setup key 过期或已使用。
- `Tab not owned by your agent`：远程 agent 操作了不属于自己的 tab，应先 `newtab`。
- `Domain not allowed`：token 域限制不匹配。
- `Rate limit exceeded`：远程 agent 超过 10 req/s。
- `Token expired`：24 小时 session 过期。
- remote reachability：ngrok tunnel 未运行或 server 不健康。

## `/qa`

### 使用场景

完整的浏览器 QA + 修复闭环。像真实用户一样测试页面、表单、导航、状态、console、响应式；发现 bug 后按严重程度修源代码、提交 atomic commit、重新验证并写报告。

### 前置条件

- 需要目标 URL 或可进入 diff-aware 模式。
- 需要 clean working tree。若 dirty，必须询问用户 commit/stash/abort。
- 需要 browse binary。
- 可能需要认证信息、cookie 文件、用户 2FA/CAPTCHA handoff。
- 会检测测试框架；没有测试框架时会引导 bootstrap，安装测试依赖、生成测试、CI 和 TESTING.md。

### 工作流

模式：

- diff-aware：无 URL 且在 feature branch 时自动分析 `git diff main...HEAD`，映射受影响页面/路由，探测本地端口。
- full：有 URL 默认全站系统探索。
- quick：主页 + top 5 navigation 的 smoke test。
- regression：基于 previous `baseline.json` 比较新旧问题和健康分。

主要阶段：

1. 初始化输出目录 `.gstack/qa-reports/screenshots`。
2. 认证：登录表单、cookie import、2FA/CAPTCHA handoff。
3. Orient：`goto`、`snapshot -i -a`、`links`、`console --errors`。
4. Explore：逐页截图、console、交互、表单、状态、响应式。
5. Document：每个 issue 立即写入报告，交互 bug 要 before/action/result/snapshot diff。
6. Wrap：计算 health score，写 baseline。
7. Triage：按 tier 决定修 critical/high/medium/low。
8. Fix loop：定位源码、最小修复、每个 fix 一个 commit、重新浏览器验证、必要时生成回归测试。
9. Final QA：复测受影响页面。
10. Report：写本地和项目级 outcome。
11. 更新 `TODOS.md`。

### 是否编辑代码

会编辑代码。还可能修改测试、创建测试框架配置、CI、TESTING.md、CLAUDE.md、TODOs，并执行 `git commit`。规则是一个 fix 一个 commit，回归则 `git revert HEAD`。

### 输出/产物

```text
.gstack/qa-reports/
├── qa-report-{domain}-{YYYY-MM-DD}.md
├── screenshots/
└── baseline.json
```

还会写 `~/.gstack/projects/{slug}/{user}-{branch}-test-outcome-{datetime}.md`。

QA 模板包含 metadata、health score、top 3 fixes、console health、severity summary、issues、fixes applied、regression tests、ship readiness、regression comparison。

### `$B` 交互

大量使用 `$B goto`、`snapshot -i -a`、`links`、`console --errors`、`click`、`fill`、`snapshot -D`、`viewport`、`screenshot`、`js fetch('/api/...')`。

### 示例提示

```text
/qa http://localhost:3000 --quick
/qa http://localhost:3000 Focus on the billing page
/qa --regression .gstack/qa-reports/baseline.json
/qa
```

### 常见失败模式

- dirty working tree 阻塞，必须先 commit/stash/abort。
- 无 URL 且无法从 diff 映射页面，需要用户给 URL。
- 本地 dev server 未运行，常见端口探测失败。
- auth/CAPTCHA/2FA 阻塞。
- 无测试框架且 bootstrap 安装失败，可能回滚 bootstrap 变更并继续无测试 QA。
- issue 未复现：规则要求重试一次，不能把 fluke 写成 bug。
- fix 后健康分下降或回归：需要警告或 revert。
- fix 数过多/风险过高：WTF-likelihood >20% 时停止询问。

## `/qa-only`

### 使用场景

只做浏览器 QA 报告，不改代码。适合上线前审计、验收、第三方页面检查、只想要问题清单和截图证据的场景。

### 前置条件

与 `/qa` 类似：目标 URL 或 diff-aware、本地 dev server、认证/cookies、browse binary。无需 clean tree，因为禁止修复。

### 工作流

与 `/qa` 的 Phase 1-6 基本相同：初始化、认证、orient、explore、document、wrap。没有 triage fix loop、commit、回归测试生成。若无测试框架，报告摘要里提示可运行 `/qa` bootstrap。

### 是否编辑代码

不编辑代码。规则明确：不读源码、不改文件、不建议修复实现，只报告用户可见问题。

### 输出/产物

同样写：

```text
.gstack/qa-reports/
├── qa-report-{domain}-{YYYY-MM-DD}.md
├── screenshots/
└── baseline.json
```

并写项目级 test outcome artifact。

### `$B` 交互

同 `/qa`，但只浏览器测试和截图，不进入源码定位。

### 示例提示

```text
/qa-only http://localhost:3000 --quick
/qa-only http://localhost:3000 Focus on onboarding
/qa-only --regression .gstack/qa-reports/baseline.json
```

### 常见失败模式

- 用户实际想修复，需改用 `/qa`。
- 无 URL/无运行 app。
- 认证阻塞。
- 截图未展示。
- 诱惑读源码：技能禁止，必须从用户视角测试。

## `/design-review`

### 使用场景

设计审计 + 前端修复闭环。关注视觉层级、排版、颜色、间距、响应式、交互状态、内容质量、AI slop，而不只是“能不能用”。适合 UI/UX 改动、上线前视觉把关、消除模板感/AI 味。

### 前置条件

- 目标 URL 或 diff-aware。
- clean working tree，因后续每个 design fix 都要 atomic commit。
- browse binary。
- 可选 design binary `$D`：用于生成 target mockup 和视觉比较。
- 可选 `DESIGN.md`/`design-system.md`：若存在，所有判断按项目设计系统校准。
- 会检测测试框架；JS 行为类设计修复可能生成回归测试。

### 工作流

模式：

- full：5-8 页，完整 checklist、响应式截图、交互流程。
- quick：主页 + 2 个关键页。
- deep：10-15 页和每个核心交互。
- diff-aware：按 branch diff 映射受影响页面。
- regression：读 `design-baseline.json` 对比。

基线阶段：

1. First Impression：截图并用第一人称写第一印象、眼动顺序、page area test。
2. Design System Extraction：用 `$B js` 抽字体、颜色、heading scale、touch target、性能。
3. Page-by-page Audit：`snapshot -i -a`、`responsive`、console、perf、trunk test 和 10 类 checklist。
4. Interaction Flow Review：走 2-3 个关键流程，用 `snapshot -D` 观察反馈与感觉。
5. Cross-page Consistency：导航、footer、组件、语气、间距一致性。
6. Compile Report：写 design score、AI slop score、baseline。
7. Outside voices：Codex + Claude subagent 源码设计审计，非阻塞。
8. Triage/Fix loop：按 high/medium/polish 修复，CSS-first。
9. Final audit 和报告。

### 是否编辑代码

会编辑代码。优先 CSS/styling，必要时改 component。每个 finding 一个 `style(design): FINDING-NNN ...` commit。只有 JS 行为类修复才生成回归测试。可在用户接受时写 `DESIGN.md`。

### 输出/产物

```text
~/.gstack/projects/$SLUG/designs/design-audit-{YYYYMMDD}/
├── design-audit-{domain}.md
├── screenshots/
└── design-baseline.json
```

同时写项目级 summary artifact。报告包含 design score、AI slop score、category grades、findings、fix status、commit SHA、before/after screenshots。

### `$B`/`$D` 交互

- `$B screenshot`、`snapshot -i -a`、`responsive`、`console --errors`、`perf`、`js` 抽设计系统。
- `$D generate` 可为复杂视觉 finding 生成 target mockup。
- `$D verify` 可比较 target mockup 与修复后截图。

### 示例提示

```text
/design-review http://localhost:3000 --quick
/design-review http://localhost:3000 Focus on the settings page
/design-review --deep
```

### 常见失败模式

- dirty working tree 阻塞。
- 无 `DESIGN.md` 导致校准只能基于通用原则。
- `$D` 不可用：跳过 target mockup，不阻塞审计。
- 过度改结构：规则要求 CSS-first、最小修复。
- 视觉修复引入功能回归：需 revert。
- 设计修复风险 >20% 或超过硬上限 30 fixes 时停止询问。
- AI slop 规则误用于后台 app：必须先分类 MARKETING/APP/HYBRID。

## `/design-shotgun`

### 使用场景

视觉探索/头脑风暴。生成多个不同设计方向，打开对比板，让用户评分、评论、remix、approve。适合还没定视觉方向、想从多个风格中挑选的阶段。

### 前置条件

- design binary `$D` 最好可用；不可用则 fallback 到 HTML wireframe。
- browse binary 可选；不可用时用系统 `open file://...` 查看 comparison board。
- 所有设计产物必须保存到 `~/.gstack/projects/$SLUG/designs/`，不能保存到项目目录、`.context`、`docs/designs` 或 `/tmp` 作为最终位置。
- 可读取 `DESIGN.md`、已有 office-hours 输出、历史 `approved.json`、`taste-profile.json`。

### 工作流

1. 检测历史设计 session，允许 revisit 或新探索。
2. 收集上下文：用户、job-to-be-done、现有组件/页面、用户流、edge cases。
3. 读取 taste memory：`taste-profile.json` 和最近 `approved.json`。
4. 生成 N 个文字 concept，要求字体、配色、布局方向显著不同。
5. 让用户确认 concept 后并行生成 PNG variants。
6. 若从现有页面 evolve，先 `$B screenshot current.png`，再 `$D evolve`。
7. 生成 comparison board：

```bash
$D compare --images "$_IMAGES" --output "$_DESIGN_DIR/design-board.html" --serve
```

8. 用户在 board 中提交 `feedback.json` 或 `feedback-pending.json`。
9. 根据 regenerate/remix/more_like 继续迭代。
10. 确认反馈后写 `approved.json`，更新 taste profile。

### 是否编辑代码

不编辑项目代码。它写用户级 gstack design artifacts 和 taste profile。后续若选择 `/design-html` 或“copy to project”才进入落地。

### 输出/产物

```text
~/.gstack/projects/$SLUG/designs/<screen-name>-YYYYMMDD/
├── variant-A.png
├── variant-B.png
├── variant-C.png
├── design-board.html
├── feedback.json
├── feedback-pending.json
└── approved.json
```

### `$B`/`$D` 交互

- `$D generate`、`variants`、`evolve`、`check`、`compare`、`iterate`。
- `$B screenshot` 用于现有页面 evolve 起点。
- comparison board 通过 HTTP server 收集反馈，AskUserQuestion 只是等待机制。

### 示例提示

```text
/design-shotgun for the onboarding dashboard, 4 variants
/design-shotgun I don't like how http://localhost:3000/pricing looks
```

### 常见失败模式

- `$D generate --output ~/.gstack/...` 受 sandbox 影响失败：技能建议先输出到 `/tmp/variant-X.png` 再复制到最终目录。
- 变体趋同：字体/配色/布局太像，必须重新生成弱变体。
- board server 启动失败：fallback 为 inline 展示图片并用 AskUserQuestion 收集偏好。
- 用户没有点击 Submit：检查不到 feedback file，需要用用户文字反馈。
- zero variants succeeded：fallback sequential generation。
- taste profile 与当前需求冲突：需要提示是更新 taste 还是本次例外。

## `/design-html`

### 使用场景

把 approved mockup、CEO plan 或用户自由描述落成 Pretext-native HTML/CSS 或框架组件。重点是文字布局真实可重排：resize 后高度重算、卡片自适应、聊天气泡 shrinkwrap、编辑文本后 relayout。

### 前置条件

- 可选 `$D`：有 approved PNG 时可用 `$D prompt --image` 抽结构化实现 spec。
- browse binary 用于三视口截图验证。
- 需要上下文来源：`approved.json`、CEO plan、variant PNG、`DESIGN.md` 或用户描述。
- vanilla HTML 需要 vendored `design-html/vendor/pretext.js`；缺失时 fallback 到 CDN。
- 若输出框架组件，需检测 React/Svelte/Vue 并安装 `@chenglou/pretext`。

### 工作流

1. 输入检测：查最新 CEO plan、approved.json、variant PNG、finalized.html、DESIGN.md。
2. 路由：
   - approved-mockup：以 approved PNG 为视觉源。
   - evolve：已有 finalized.html 时在旧 HTML 上迭代。
   - plan-driven：用 CEO/design plan prose。
   - freeform：用户直接描述。
3. 设计分析：抽颜色、字体、布局、组件、spacing，`DESIGN.md` token 优先。
4. Pretext tier 分类：simple/card-grid/chat/editorial/complex editorial。
5. 框架检测：询问 vanilla HTML 还是框架组件。
6. 生成 `finalized.html` 或组件。
7. 启动本地 preview server：

```bash
python3 -m http.server 0 --bind 127.0.0.1
```

8. 用 browse 做 mobile/tablet/desktop 截图验证。
9. 进入最多 10 轮 refinement loop，用户说 done 后退出。
10. 写 `finalized.json`，可询问是否生成 `DESIGN.md`，再询问下一步是否 copy 到项目。

### 是否编辑代码

默认不直接改项目代码，产物在 `~/.gstack/projects/$SLUG/designs/...`。但两个动作可能改项目：用户选择框架输出时安装依赖；用户接受时创建 `DESIGN.md`；最终 AskUserQuestion 选择“Copy to project”后才会复制进代码库。

### 输出/产物

```text
~/.gstack/projects/$SLUG/designs/<screen-name>-YYYYMMDD/
├── finalized.html
├── finalized.json
└── possibly finalized.tsx/svelte/vue
```

`finalized.json` 记录 source mockup/plan、mode、html file、pretext tier、framework、iteration count、date、screen、branch。

### `$B`/`$D` 交互

- `$D prompt --image` 抽 implementation spec。
- `$B goto file://...` 和三视口 screenshot 验证。
- live preview 可通过普通 browser 打开 `http://localhost:<port>/finalized.html`。

### 示例提示

```text
/design-html
/design-html Just describe it: build a pricing page for a developer API
```

### 常见失败模式

- 没有 approved/plan/context：需要用户选择先跑 `/design-shotgun`、`/plan-ceo-review`、`/plan-design-review` 或直接描述。
- Pretext vendor 缺失：fallback CDN，导致 HTML 不再完全离线自包含。
- python3 不可用：fallback `open finalized.html`。
- 文本 overflow/布局重叠：必须修完再展示。
- refinement loop 超过 10 轮：询问继续还是结束。
- 用户手动 contenteditable 修改可能丢失：规则要求 surgical edit，不要整文件重写。

## `/devex-review`

### 使用场景

面向开发者产品的 live DX 审计。不是读计划，而是实际浏览文档、试 getting started、截图页面、运行 CLI help/错误命令，量化 Time to Hello World 和 DX 八维分数。

### 前置条件

- 需要 docs/product URL 或从 README/CLAUDE/package 中发现。
- browse 可测试 web surfaces：docs、playground、dashboard、signup、error pages。
- bash 可测试 CLI：`--help`、缺参、错误 flags、README/CHANGELOG/CI 文件。
- 对无法测试的维度必须标注 INFERRED，不能猜。

### 工作流

1. Target discovery：读 CLAUDE.md、README、package 获取 URL/命令。
2. Boomerang baseline：读取 prior `/plan-devex-review` score。
3. Getting Started Audit：浏览入口页，记录步骤、时间、摩擦、截图。
4. API/CLI/SDK Ergonomics：跑 CLI help，访问 playground。
5. Error Message Audit：触发 404、无效表单、未认证、CLI 缺参。
6. Documentation Audit：测试搜索、代码示例、语言切换、信息架构。
7. Upgrade Path：读 CHANGELOG、migration guides、deprecated grep。
8. Developer Environment：读 README setup、CI、types、test utilities。
9. Community & Ecosystem：浏览 community links、GitHub issues、contributing。
10. DX Measurement：反馈机制、issue templates、docs analytics。
11. 写 DX scorecard、plan vs reality、review log、readiness dashboard。

### 是否编辑代码

通常只报告，不改业务代码。它会写 review log；若在 plan mode 中找到 plan file，会把 `## GSTACK REVIEW REPORT` 更新到 plan 文件末尾。

### 输出/产物

- 会话中的 DX scorecard、TTHW、boomerang comparison、readiness dashboard。
- `gstack-review-log` JSONL entry。
- 可能更新 plan 文件中的 GSTACK REVIEW REPORT。

### `$B` 交互

用 browse 导航 docs/landing/playground/signup/error/community 页面并截图。CLI 和文件证据用 shell。

### 示例提示

```text
/devex-review https://docs.example.com
/devex-review review this repo's getting started flow
```

### 常见失败模式

- 没有 URL，需要问用户。
- 需要真实账号、邮箱验证或付费，browse 无法完整测试，只能标注 blocked/partial。
- CLI install/本地环境构建不能由 browse 测，需要 bash 或 INFERRED。
- 分数无证据：技能要求每个 score 都标明 TESTED/PARTIAL/INFERRED。
- prior plan score 与 live score 差距 >2，需要 boomerang alert。

## `/scrape`

### 使用场景

从网页读取结构化数据。它是 read-only 入口：优先匹配已有 browser-skill，未匹配则用 `$B` 原语原型化抓取，输出 JSON，并提示 `/skillify`。

### 前置条件

- browse daemon 必须可用。
- 用户 intent 需要包含目标页面/host 或能推断 URL。
- 不能用于提交、登录、下单、删除、创建等 mutating flow。
- Auth/cookie 不是它负责，需先 `/setup-browser-cookies`。

### 工作流

1. 解析用户 `/scrape` 后的一行 intent；缺失时只问一次。
2. 拒绝 mutating verbs，提示 `/automate` 尚未 shipped 或直接用 `$B click/fill/type`。
3. Match phase：

```bash
$B skill list
$B skill show <name>
$B skill run <name> [--arg key=value]
```

匹配条件：domain 符合、trigger/description 覆盖 intent、args 可满足。

4. Prototype phase：

```bash
$B goto <url>
$B text
$B html
$B links
```

迭代 selector，构造一个稳定 JSON document。

5. 成功后只追加一句：

```text
Say /skillify to make this a permanent skill (200ms on next call).
```

### 是否编辑代码

不编辑代码、不写项目文件。只读取页面并输出 JSON。

### 输出/产物

一份 stdout JSON，例如：

```json
{ "items": [], "count": 0 }
```

match path 返回 matched skill 的 JSON；prototype path 返回本次构造的 JSON。

### `$B` 交互

使用 `$B skill list/show/run` 和 `$B goto/text/html/links`。不使用写入型网页交互。

### 示例提示

```text
/scrape top stories on Hacker News
/scrape product names + prices on example.com/products
```

### 常见失败模式

- intent 含写操作：必须拒绝。
- 两个 skill 均可能匹配：优先 project > global > bundled；仍含糊则走 prototype。
- selector 尝试 3-4 次仍无合理 JSON：报告尝试内容和阻塞原因，不输出半成品，不提示 skillify。
- lazy-loaded/paywalled/JS-rendered 数据不可见：需要进一步操作或 cookie，可能需用户决策。
- 多页 crawl：明确不支持，一次调用只做 one-shot。

## `/skillify`

### 使用场景

把最近一次成功的 `/scrape` prototype 固化为永久 browser-skill，下次 `/scrape` 命中 trigger 时可在约 200ms 内运行 deterministic script。

### 前置条件

- 最近 10 个 agent turn 内必须有成功 `/scrape` prototype 结果，且用户没有否定它。
- matched skill 的 `/scrape` 不能 skillify，因为它已经是 codified。
- 需要 browse daemon、Bun runtime、canonical `browse-client.ts`。
- 需要用户确认 skill 名称和 tier，再在测试通过后确认是否 commit。

### 工作流

1. Provenance guard：找最近成功 `/scrape` intent + JSON。
2. 提议 skill name、3-5 triggers、host，并检查同名 shadow/collision。
3. 合成 `script.ts`：只用最终成功的 `$B` calls，parser 必须是 pure function。
4. 捕获 HTML fixture：

```bash
$B goto "<TARGET_URL>"
$B html > /tmp/skillify-fixture-$$.html
```

5. 写 `script.test.ts`，至少一个非空和字段形状断言。
6. 读取 canonical SDK：`browse/src/browse-client.ts`，复制到 `_lib/browse-client.ts`。
7. 用 `stageSkill` 原子 staging 到 `~/.gstack/.tmp/skillify-<spawnId>/<name>/`。
8. `$B skill test "<name>" --dir "<stagedDir>"` 或 `bun test script.test.ts`。
9. 测试通过后问用户 commit/look/discard。
10. `commitSkill` 原子 rename 到 global/project tier；拒绝 clobber。
11. `$B skill list | grep <name>` 和 `$B skill run <name>` 验证。

### 是否编辑代码

不编辑项目业务代码。会写 browser-skill artifact 到 global `~/.gstack/browser-skills/<name>/` 或 project `<repo>/.gstack/browser-skills/<name>/`。写入前 staging，失败/拒绝会 `discardStaged` 清理。

### 输出/产物

每个 skill 目录包含：

```text
SKILL.md
script.ts
script.test.ts
_lib/browse-client.ts
fixtures/<host>-<date>.html
```

`SKILL.md` frontmatter 包含 name、description、host、trusted false、source agent、version、args、triggers。

### `$B` 交互

使用 `$B skill list/show/test/run`、`$B goto`、`$B html`。生成的 script 通过 `_lib/browse-client.ts` 连接 daemon。

### 示例提示

```text
/scrape top stories on Hacker News
/skillify
```

### 常见失败模式

- 无近期成功 `/scrape`：必须拒绝，不能从聊天碎片合成。
- 用户几轮后切到别的话题：需确认是否 skillify 那次。
- skill name 不合法：必须 lowercase/digit/dash、字母开头、无连续 dash。
- tier collision：同 tier 已存在则 commit 拒绝；高 tier 会 shadow 低 tier。
- parser/test 失败：最多重试两次，失败则 discard staged，不留下半成品。
- SDK path 找不到或 Bun 不可用。
- fixture 过期：测试仍可能过但目标站 HTML 已变化，属于已知限制。
- post-commit run 与 prototype JSON 不匹配：必须告知用户，不能静默回滚。

## `/benchmark`

### 使用场景

性能回归检测。适合建立 baseline、比较 PR 性能变化、快速单页 timing、按 diff 测受影响页面、看历史趋势。

### 前置条件

- 需要目标 URL 或 `--diff` 能发现页面。
- browse daemon 可用，页面可加载。
- 若用 `--diff`，最好有 `gh` 能读取 PR base/default branch。
- baseline 模式需要写 `.gstack/benchmark-reports/baselines/baseline.json`。

### 工作流

1. 创建：

```bash
mkdir -p .gstack/benchmark-reports
mkdir -p .gstack/benchmark-reports/baselines
```

2. Page discovery：类似 canary，从导航或 `--pages` 得到页面；`--diff` 读 branch diff。
3. 每页：

```bash
$B goto <page-url>
$B perf
$B eval "JSON.stringify(performance.getEntriesByType('navigation')[0])"
```

4. 抽 TTFB、FCP、LCP、DOM Interactive、DOM Complete、Full Load。
5. 抽 resource、JS/CSS bundle、network summary。
6. `--baseline` 保存 baseline JSON。
7. 对比 baseline：按 timing、bundle、request thresholds 标记 OK/WARNING/REGRESSION。
8. 输出 slowest resources、performance budget、trend。
9. 写 markdown 和 JSON report。

### 是否编辑代码

只读，不改代码。只写 benchmark reports/baselines。

### 输出/产物

```text
.gstack/benchmark-reports/
├── baselines/baseline.json
├── {date}-benchmark.md
└── {date}-benchmark.json
```

报告包含 metric delta、regression count、slowest resources、performance budget、trend。

### `$B` 交互

核心是 `$B perf` 和 `$B eval performance.getEntriesByType(...)`。还用 `$B goto` 加载各页。

### 示例提示

```text
/benchmark http://localhost:3000 --baseline
/benchmark http://localhost:3000 --quick
/benchmark http://localhost:3000 --pages /,/dashboard,/api/health
/benchmark --diff
/benchmark --trend
```

### 常见失败模式

- 无 baseline 时不能判断回归，只能给绝对值并建议先 capture baseline。
- LCP/FCP PerformanceObserver 在简单 eval 时可能拿不到完整值，需要确保页面加载后采样。
- 网络波动影响 timing，因此 bundle size 是更稳定的 leading indicator。
- 第三方脚本慢：可标注上下文，但不应把无法修的第三方当首要 fix。
- `--diff` 依赖 branch/base/gh 信息，失败时需改用显式 URL/pages。

## 技能间关系

- `browse` 是底座；其他技能几乎都依赖 `$B`。
- `open-gstack-browser` 改变 browse 的可视化形态，让 `/qa`、`/design-review`、`/benchmark` 过程可被用户实时观察。
- `setup-browser-cookies` 给 QA/design/scrape/devex 解锁登录态。
- `pair-agent` 把 browse 能力分配给其他 agent，适合并行排查或远程协作。
- `qa-only` 是 `/qa` 的只读版；`qa` 是报告 + 修复 + 回归测试 + commit。
- `design-shotgun` 负责发散并形成 approved mockup；`design-html` 负责把 approved/plan/freeform 落成 HTML；`design-review` 负责上线界面的审计和修复。
- `scrape` 是一次性抽取入口；`skillify` 把成功 prototype 持久化为 browser-skill。
- `benchmark` 与 QA/design 同样用 browse，但只关注性能指标，不改代码。

## 实操建议

1. 在本项目手动执行任何 gstack 命令前，先用项目级 env，避免写入 `~/.gstack` 或 `~/.claude`。
2. 对浏览器测试类任务，优先明确 URL 和认证方式；没有 URL 时才依赖 diff-aware 自动映射。
3. 只想要报告用 `/qa-only`；允许自动修复和 commit 才用 `/qa`。
4. 只想评价视觉和生成修复用 `/design-review`；想先探索多个方向用 `/design-shotgun`；已有 mockup/plan 要生成 HTML 用 `/design-html`。
5. 抓取数据先 `/scrape`，成功且会重复使用再 `/skillify`。
6. 性能变化先 `/benchmark --baseline`，之后每个分支或 PR 再跑 `/benchmark` 比较。
