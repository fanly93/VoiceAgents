# gstack 总体使用指南与探索汇总

生成时间：2026-05-28

本汇总基于 6 个 subagent 的并行探索结果，覆盖本地 checkout `.agents/skills/gstack` 以及项目级生成入口 `.agents/skills/gstack-*`。详细分报告见：

- `01_runtime_installation_usage.md`：安装、运行时、项目级环境。用户已说明安装部分此前探索过，本总览只保留必要约束。
- `02_planning_product_skills.md`：规划、产品、spec、设计系统类 skills。
- `03_browser_qa_design_skills.md`：浏览器、QA、抓取、设计实现类 skills。
- `04_review_debug_security_skills.md`：review、debug、安全、质量、安全护栏类 skills。
- `05_release_docs_memory_ops_skills.md`：发布、部署、文档、记忆、运维类 skills。
- `06_ios_mobile_skills.md`：iOS 真机与移动设备类 skills。

## 核心结论

gstack 不是单个工具，而是一套 AI 工程工作流。它把一个项目从“想法”推进到“计划、实现、审查、浏览器验证、发布、部署、沉淀”的多个阶段，每个阶段由一个专门 skill 承担。

本项目必须使用项目级 Codex 入口：

```text
$gstack-office-hours
$gstack-autoplan
$gstack-review
$gstack-qa
$gstack-browse
...
```

不要调用根 `$gstack`。根 `.agents/skills/gstack/SKILL.md` 是源码 checkout 和运行时目录的一部分，偏 Claude 路径；Codex 兼容入口是 `.agents/skills/gstack-*` 这些生成后的 skill。

后续让我用 gstack 帮你完成项目时，推荐默认流程是：

```text
想清楚方向：$gstack-office-hours 或 $gstack-spec
审计划：    $gstack-autoplan
实现：      Codex 正常改代码
查问题：    $gstack-review / $gstack-investigate / $gstack-health
测体验：    $gstack-qa 或 $gstack-qa-only
发布：      $gstack-ship
部署：      $gstack-land-and-deploy
沉淀：      $gstack-document-release / $gstack-learn / $gstack-context-save
```

## 项目级使用约束

本项目的 gstack 已在 `.agents/` 下，后续不需要重新探索安装。仍需牢记这些运行约束：

- 本目录必须保持为 git repo，gstack 依赖 `git rev-parse --show-toplevel` 定位项目级 runtime。
- 手动运行 gstack 命令时使用项目级 env，避免写入用户级目录。
- 技能正文里仍可能出现 `~/.claude/skills/gstack` 或 `~/.gstack`，在本项目中应理解为需要映射到项目级 `.agents/skills/gstack`、`.gstack`、`.gstack-home`。
- `$gstack-browse`、`$gstack-qa`、`$gstack-design-review` 等需要 localhost/browser daemon 时，在 Codex 沙箱中可能需要申请非沙箱执行。

手动命令模板：

```bash
env HOME="$PWD/.gstack-home" \
  GSTACK_HOME="$PWD/.gstack" \
  GSTACK_STATE_DIR="$PWD/.gstack" \
  PATH="$PWD/.bun/bin:$PATH" \
  <gstack-command>
```

## 按阶段选择 skill

### 1. 产品和计划阶段

适合还没开始写代码，或需求有不确定性时使用。

| Skill | 什么时候用 | 主要产物 | 是否交互 |
|---|---|---|---|
| `$gstack-office-hours` | 早期想法、产品方向、side project、需要判断“到底该不该做” | design doc、premises、方案选择、learnings | 强交互 |
| `$gstack-spec` | 方向已基本确定，需要写成可执行 issue/spec | GitHub issue 或本地 spec archive，可选 worktree 执行 | 强交互 |
| `$gstack-plan-ceo-review` | 需要 CEO/Founder 视角挑战范围、方向、野心和取舍 | CEO plan、scope mode、review log | 强交互 |
| `$gstack-plan-eng-review` | 实现前检查架构、数据流、测试、失败模式 | plan 更新、failure registry、test matrix | 强交互 |
| `$gstack-plan-design-review` | UI/UX plan 实现前的设计完整性检查 | mockups、design tasks、plan design report | 强交互 |
| `$gstack-plan-devex-review` | API、SDK、CLI、MCP、docs 等开发者体验 plan | DX scorecard、persona、TTHW、journey map | 强交互 |
| `$gstack-autoplan` | 已有 plan，希望自动跑 CEO + Design + Eng + DX review | 综合 review plan、decision audit trail、review logs | 半自动 |
| `$gstack-design-consultation` | 需要设计系统、品牌方向、`DESIGN.md` | `DESIGN.md`、design artifacts、taste profile | 强交互 |
| `$gstack-plan-tune` | 调整 gstack 提问敏感度和个人偏好 | question preference/profile | 交互 |

实用判断：

- 需求还模糊：先 `$gstack-office-hours`。
- 需求明确但还没成 ticket：用 `$gstack-spec`。
- 已有计划但想完整审一遍：用 `$gstack-autoplan`。
- 只担心架构和测试：用 `$gstack-plan-eng-review`。
- 只担心 UI 体验：用 `$gstack-plan-design-review`。
- 面向开发者的工具/API：用 `$gstack-plan-devex-review`。

### 2. 浏览器、QA、设计落地阶段

这组 skill 以 browse daemon 为核心，能打开真实 Chromium、点击、截图、检查 console/network/perf，并在上层组织 QA 或设计修复流程。

| Skill | 什么时候用 | 是否改代码 | 主要产物 |
|---|---|---:|---|
| `$gstack-browse` | 需要浏览器眼睛：打开页面、截图、点击、检查 DOM/console/network | 否 | screenshots、page state、browser session |
| `$gstack-open-gstack-browser` | 想看见可视浏览器和 sidebar 动作 | 否 | headed Chromium、side panel |
| `$gstack-setup-browser-cookies` | QA 登录态页面，需要从真实浏览器导入 cookie | 否 | browse session cookies |
| `$gstack-pair-agent` | 让另一个 agent 共用浏览器 | 否 | pairing token/instruction |
| `$gstack-qa` | 系统 QA 并修复 bug | 是 | QA report、screenshots、fix commits、regression tests |
| `$gstack-qa-only` | 只要 QA 报告，不允许改代码 | 否 | QA report、screenshots、baseline |
| `$gstack-design-review` | live site 视觉审计并修复 UI 问题 | 是 | design audit、before/after screenshots、style commits |
| `$gstack-design-shotgun` | 生成多个视觉方向并让用户挑选 | 否 | variants、comparison board、approved.json |
| `$gstack-design-html` | 把批准的 mockup 落成生产 HTML/CSS | 是 | HTML/CSS/组件实现 |
| `$gstack-devex-review` | 实测开发者 onboarding/docs/API/CLI 体验 | 多数不改，视流程而定 | DX audit、TTHW、screenshots |
| `$gstack-scrape` | 从网页抽取结构化数据 | 否 | JSON 数据 |
| `$gstack-skillify` | 把成功 scrape 流程固化为可复用 browser-skill | 是，写 browser-skill 文件 | script/test/fixture |
| `$gstack-benchmark` | 检查页面性能和回归 | 否 | performance baseline/report |

实用判断：

- 只是让我看看页面是否正常：`$gstack-browse`。
- 想要完整测试并修：`$gstack-qa`。
- 只想要验收报告：`$gstack-qa-only`。
- UI 看起来不高级、不一致、像模板：`$gstack-design-review`。
- 还没决定视觉方向：`$gstack-design-shotgun`，批准后再 `$gstack-design-html`。
- 需要登录态：先 `$gstack-setup-browser-cookies`。

### 3. Review、debug、安全和质量阶段

这组用于实现后把风险找出来，或在出 bug 时做根因调查。

| Skill | 什么时候用 | 是否改代码 | 重点 |
|---|---|---:|---|
| `$gstack-review` | 合并前检查当前分支 diff | 是，Fix-First | PR/diff 质量门、scope drift、结构风险 |
| `$gstack-investigate` | 用户报告 bug、错误、stack trace、异常行为 | 是，但必须先证明根因 | Iron Law：无根因不修 |
| `$gstack-cso` | 安全审计、威胁建模、OWASP/STRIDE | 否 | read-only，低噪声安全报告 |
| `$gstack-health` | 运行 typecheck/lint/test/dead code 等健康检查 | 否 | 代码质量仪表盘 |
| `$gstack-codex` | 让 Codex CLI 给第二意见 | 通常否 | review/challenge/consult |
| `$gstack-careful` | 操作生产或危险命令前启用警告 | 否 | destructive Bash ask |
| `$gstack-freeze` | 限制 Edit/Write 到某个目录 | 只写状态 | 越界编辑 deny |
| `$gstack-guard` | careful + freeze | 只写状态 | 生产/多人协作安全模式 |
| `$gstack-unfreeze` | 解除 freeze 编辑边界 | 只删状态 | 放开编辑范围 |

关键区别：

- `$gstack-review` 从 diff 出发，问“这批变更能不能 landing”。
- `$gstack-investigate` 从症状出发，问“根因是什么，如何证明并修复”。
- `$gstack-health` 运行项目已有工具，不替代 review。
- `$gstack-cso` 做安全态势审计，不自动修业务代码。

推荐组合：

```text
实现完成 -> 跑测试 -> $gstack-review -> 修复 findings -> $gstack-health -> $gstack-qa 或 $gstack-qa-only
出现 bug -> $gstack-investigate -> 回归测试 -> $gstack-review
安全相关 -> $gstack-cso --diff -> 修复 -> $gstack-review --security
高风险环境 -> $gstack-guard -> investigate/fix -> $gstack-unfreeze
```

### 4. 发布、部署、文档、记忆和运维阶段

这组把已完成的变更推进到 PR、部署、生产观察和长期记忆。

| Skill | 什么时候用 | 主要动作 | 风险等级 |
|---|---|---|---|
| `$gstack-ship` | 代码准备好，要版本化、提交、推送、开 PR | tests、review、VERSION、CHANGELOG、commit、push、PR | 高 |
| `$gstack-land-and-deploy` | PR 已通过，要合并和部署验证 | merge、wait CI/deploy、canary、可选 rollback | 高 |
| `$gstack-canary` | 部署后持续观察生产 | console/perf/screenshot monitoring | 中 |
| `$gstack-setup-deploy` | 首次配置部署平台和生产 URL | 写 deploy config 到项目说明 | 中 |
| `$gstack-landing-report` | 多 workspace 并行时查看版本队列 | read-only queue dashboard | 低 |
| `$gstack-document-release` | 发版后同步 README/docs/changelog | 更新文档 | 中 |
| `$gstack-document-generate` | 从代码生成缺失文档 | Diataxis docs | 中 |
| `$gstack-context-save` | 中断前保存上下文 | checkpoint/context artifact | 低 |
| `$gstack-context-restore` | 新会话恢复进度 | 读取 saved context | 低 |
| `$gstack-learn` | 管理项目 learnings | review/search/prune/export | 低 |
| `$gstack-retro` | 周期性工程复盘 | retro report、趋势 | 低 |
| `$gstack-gstack-upgrade` | 更新 gstack 自身 | 更新本地 gstack | 中 |
| `$gstack-setup-gbrain` | 初始化跨机器记忆系统 | gbrain config/MCP | 中 |
| `$gstack-sync-gbrain` | 重建 repo 索引和 search guidance | gbrain sync、CLAUDE.md guidance | 中 |
| `$gstack-benchmark-models` | 比较 Claude/GPT/Gemini 在某 skill 上表现 | model benchmark | 低到中 |
| `$gstack-make-pdf` | 把 markdown 转成 PDF | PDF artifact | 低 |

发布建议：

```text
$gstack-review
$gstack-qa-only 或 $gstack-qa
$gstack-landing-report
$gstack-ship
$gstack-document-release
$gstack-land-and-deploy
$gstack-canary <production-url>
$gstack-learn 或 $gstack-retro
```

注意：`$gstack-ship` 和 `$gstack-land-and-deploy` 会执行高影响动作，包括 commit、push、PR、merge、deploy、可能 rollback。只有在明确要发布时使用。

### 5. iOS / 真机移动设备阶段

这组只适用于 SwiftUI/iOS 真机调试，不适合普通 Web/后端项目。

| Skill | 什么时候用 | 主要能力 | 是否改代码 |
|---|---|---|---:|
| `$gstack-ios-qa` | 在真实 iPhone 上做 live QA | 安装 DebugBridge、截图、元素、状态、触控 | 是，接入 DebugBridge |
| `$gstack-ios-fix` | 根据 iOS QA 发现修复 bug | 真机复现、修复、回归快照 | 是 |
| `$gstack-ios-design-review` | 真机视觉/HIG 设计审计 | iPhone screenshot、10 维 Apple HIG rubric | 可能 |
| `$gstack-ios-clean` | Release 前移除 DebugBridge/#if DEBUG wiring | 清理调试桥 | 是 |
| `$gstack-ios-sync` | 更新 iOS DebugBridge 模板 | regenerate StateServer/templates/accessors | 是 |

非 iOS 项目直接忽略这组。只有满足 macOS、Xcode、真实 iPhone、SwiftUI、`@Observable`、DebugBridge 接入这些条件时才使用。

## 推荐的项目协作模式

### 模式 A：从模糊想法到可执行计划

```text
$gstack-office-hours
$gstack-spec --no-execute
$gstack-autoplan
```

适合新功能、新产品方向或你还没确定 scope 的任务。`office-hours` 用来澄清真实需求和方案；`spec` 固化为 issue；`autoplan` 自动跑 CEO/Design/Eng/DX review。

### 模式 B：已有明确需求，直接实现并验证

```text
$gstack-spec --no-execute
Codex 实现
$gstack-review
$gstack-health
$gstack-qa-only
```

适合普通功能开发。若 QA 报出要修的问题，再切 `$gstack-qa` 或让 Codex 手动修后重跑 review。

### 模式 C：线上/本地 bug 修复

```text
$gstack-investigate "<症状或错误>"
Codex 最小修复
项目测试
$gstack-review
$gstack-qa-only
```

关键是先证明根因，不要直接猜修。

### 模式 D：UI/产品体验优化

```text
$gstack-design-consultation
$gstack-plan-design-review
Codex 实现
$gstack-design-review
$gstack-qa-only
```

如果已经有页面但视觉方向不满意，可以从 `$gstack-design-shotgun` 开始，批准方向后再落地。

### 模式 E：发布到 PR 和生产

```text
$gstack-review
$gstack-qa-only
$gstack-landing-report
$gstack-ship
$gstack-land-and-deploy
$gstack-canary
$gstack-document-release
```

这套适合真正要合并发布时使用。只探索或本地实验时不要跑 `$gstack-ship`。

## Skill 覆盖清单

本地共发现 53 个 `SKILL.md`。项目实际应优先使用以下 Codex 生成入口：

```text
$gstack-autoplan
$gstack-benchmark
$gstack-benchmark-models
$gstack-browse
$gstack-canary
$gstack-careful
$gstack-claude
$gstack-context-restore
$gstack-context-save
$gstack-cso
$gstack-design-consultation
$gstack-design-html
$gstack-design-review
$gstack-design-shotgun
$gstack-devex-review
$gstack-document-generate
$gstack-document-release
$gstack-freeze
$gstack-guard
$gstack-health
$gstack-investigate
$gstack-ios-clean
$gstack-ios-design-review
$gstack-ios-fix
$gstack-ios-qa
$gstack-ios-sync
$gstack-land-and-deploy
$gstack-landing-report
$gstack-learn
$gstack-make-pdf
$gstack-office-hours
$gstack-open-gstack-browser
$gstack-pair-agent
$gstack-plan-ceo-review
$gstack-plan-design-review
$gstack-plan-devex-review
$gstack-plan-eng-review
$gstack-plan-tune
$gstack-qa
$gstack-qa-only
$gstack-retro
$gstack-review
$gstack-scrape
$gstack-setup-browser-cookies
$gstack-setup-deploy
$gstack-setup-gbrain
$gstack-ship
$gstack-skillify
$gstack-spec
$gstack-sync-gbrain
$gstack-unfreeze
$gstack-upgrade
```

源码 checkout 下还存在根 `gstack/SKILL.md` 和内部源码目录，后续不要把它作为项目入口调用。

## 后续让我执行项目任务时的默认策略

我会按任务类型主动选择最小够用的 gstack skill：

- 你说“帮我想清楚/规划/写方案”：优先 `$gstack-office-hours`、`$gstack-spec` 或 `$gstack-autoplan`。
- 你说“修 bug/报错/为什么坏了”：优先 `$gstack-investigate`。
- 你说“review/准备合并”：优先 `$gstack-review`。
- 你说“打开页面看看/测试网站”：优先 `$gstack-browse` 或 `$gstack-qa-only`。
- 你说“测试并修”：优先 `$gstack-qa`。
- 你说“UI 不好看/设计审查”：优先 `$gstack-design-review` 或 `$gstack-design-shotgun`。
- 你说“发 PR/ship”：优先 `$gstack-ship`，但会先确认高影响动作。
- 你说“部署/上线”：优先 `$gstack-land-and-deploy`，首次先 `$gstack-setup-deploy`。
- 你说“保存上下文/下次继续”：优先 `$gstack-context-save`，恢复用 `$gstack-context-restore`。

如果某个 gstack skill 的完整流程依赖当前 Codex 工具环境没有暴露的 `AskUserQuestion`、浏览器 daemon、localhost 权限、GitHub auth、Codex CLI、Claude CLI 或外部网络，我会先说明缺口，再用本项目可用工具做等价降级。
