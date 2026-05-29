# gstack 规划 / 产品 / Spec 类 Skills 分析

本报告分析 `.agents/skills/gstack` 中的规划、产品、设计系统、规格化与提问调优类 skill。范围限定为用户指定的 `SKILL.md` 文件及直接相关脚本/文档引用。示例调用均按本项目约定使用 Codex 兼容的项目级 skill 名称，例如 `$gstack-office-hours`，不使用根 `$gstack`。

## 共性观察

- 这些 skill 大多由同一套 gstack preamble 生成，包含更新检查、telemetry、项目 slug、learnigns、AskUserQuestion 格式、review dashboard、plan file report 等共享逻辑。分析单个 skill 时应把这些共享段落和 skill 主体区分开。
- 多数交互式 skill 强依赖 `AskUserQuestion`。在没有可用 AskUserQuestion 工具的宿主中，文档要求直接阻塞并报告不可用；在 Codex 中需要用项目实际可用的提问机制适配。
- 生成后的文档中仍大量引用 `~/.claude/skills/gstack/...`，但本项目要求使用项目级 gstack。实际手动运行时应使用项目级环境变量，避免写入用户级目录：

```bash
env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" <gstack-command>
```

- 多个 review skill 会写入 `~/.gstack` 或通过 `gstack-paths` 解析的状态目录，包括 review log、analytics、task JSONL、design artifacts、profile 等。在本项目约定下，这些应落到项目级 `.gstack`/`.gstack-home`。
- 规划链路大致是：`office-hours` 先澄清“值不值得做”和设计方向；`spec` 把已确定的工作写成可执行 issue；`plan-ceo-review` 做战略/范围 review；`plan-eng-review` 做架构/测试/失败模式 review；`plan-design-review` 做 UI/UX plan review；`plan-devex-review` 做开发者体验 plan review；`autoplan` 串行运行这些 review；`plan-tune` 调整提问偏好；`design-consultation` 生成或更新 `DESIGN.md`。

## 直接相关脚本与文档

这些脚本/文档被主体流程直接引用，理解 artifact 和风险时很关键：

- `.agents/skills/gstack/bin/gstack-slug`：计算项目 slug，用于 `~/.gstack/projects/$SLUG/...`。
- `.agents/skills/gstack/bin/gstack-paths`：解析状态目录，受 `GSTACK_HOME`、`GSTACK_STATE_DIR` 等影响。
- `.agents/skills/gstack/bin/gstack-config`：读写 telemetry、question tuning、cross-project learnings 等配置。
- `.agents/skills/gstack/bin/gstack-learnings-search` / `gstack-learnings-log`：跨会话学习检索和记录。
- `.agents/skills/gstack/bin/gstack-review-log` / `gstack-review-read`：review dashboard 和 `/ship` gating 的数据源。
- `.agents/skills/gstack/bin/gstack-developer-profile`：`office-hours` 和 `plan-tune` 的用户画像、资源去重、profile 读取/写入。
- `.agents/skills/gstack/bin/gstack-question-preference`：`plan-tune` 和 preamble 的 per-question preference 查询/写入。
- `.agents/skills/gstack/bin/gstack-codex-probe`：`autoplan` 的 Codex CLI auth/version preflight。
- `.agents/skills/gstack/design/dist/design`：`design-consultation` 与 `plan-design-review` 的 mockup 生成、比较板、质量检查。
- `.agents/skills/gstack/browse/dist/browse`：`design-consultation` 的视觉竞品调研与比较板 fallback。
- `.agents/skills/gstack/plan-devex-review/dx-hall-of-fame.md`：DX review 每个 pass 的标杆案例与 Claude Code skill DX checklist。
- `.agents/skills/gstack/docs/designs/PLAN_TUNING_V0.md`：`plan-tune` 的 canonical reference。

## 1. office-hours

路径：`.agents/skills/gstack/office-hours/SKILL.md`

### 何时使用

用于产品想法、创业方向、side project、hackathon、研究、开源或“我想做 X，但还没想清楚”的早期探索。它不是实现工具，文档明确规定只产出 design doc，不写代码、不 scaffold、不调用实现 skill。

### 期望用户输入

- 初始产品/功能/想法描述。
- 用户目标类型：创业、公司内部项目、hackathon/demo、开源/研究、学习、玩票项目等。
- 若是创业/内部项目，还期望产品阶段：pre-product、有用户、有付费客户。
- 后续通过一轮轮 AskUserQuestion 获取需求证据、现状替代方案、目标人群、最小 wedge、观察结果、未来适配等。

### 工作流阶段

1. **Phase 1 Context Gathering**：读 `CLAUDE.md`、`TODOS.md`、git log/diff，查相关代码区域，列出既有 design docs，询问用户目标并映射到 Startup mode 或 Builder mode。
2. **Prior Learnings**：读取项目或跨项目 learnings，可询问是否启用 cross-project learnings。
3. **Phase 2A Startup Mode**：YC 风格强诊断，围绕六个 forcing questions：真实需求、当前替代方案、具体目标用户、最窄付费 wedge、观察和惊讶、三年后适配。
4. **Phase 2B Builder Mode**：适合学习、玩票、开源、hackathon，问题更偏“最酷版本”“会展示给谁”“最快可分享路径”。
5. **Phase 2.5 Related Design Discovery**：根据问题关键词找既有 design doc，询问是继承还是重做。
6. **Phase 2.75 Landscape Awareness**：在隐私门禁后搜索外部 landscape，用三层分析推导 conventional wisdom 与可能的 eureka。
7. **Phase 3 Premise Challenge**：把前面内容提炼成必须成立的 premises，并要求用户确认。
8. **Phase 3.5 Cross-Model Second Opinion**：可选调用 Codex 或 Claude subagent 给冷启动第二意见。
9. **Phase 4 Alternatives Generation**：强制生成至少 A/B 两个方案，有时加入 lateral/creative C，并让用户明确选择。
10. **Visual Design Exploration / Visual Sketch**：对 UI 想法可接入 design 或 Codex 视觉探索。
11. **Phase 4.5 Founder Signal Synthesis**：记录本次会话观察到的 founder/builder signals，并写入 developer profile。
12. **Phase 5 Design Doc**：写 startup 或 builder 模板的 design doc。
13. **Spec Review Loop**：对 design doc 做 adversarial review，最多多轮修正。
14. **Phase 6 Handoff**：根据历史 session tier 做关系型 closing、资源推荐、下一 skill 建议。
15. **Capture Learnings**：记录有复用价值的 insight。

### 输出与 artifact

- Design doc：通常位于 `~/.gstack/projects/$SLUG/*-design-*.md`，含 `Supersedes:` 链路、premises、approaches、recommended approach、success criteria、assignment 等。
- Developer profile：`~/.gstack/developer-profile.json`，记录 session、signals、resources shown、design_doc、assignment。
- Builder journey：多次 session 后可能写 `~/.gstack/builder-journey.md`。
- Analytics：`~/.gstack/analytics/skill-usage.jsonl`、`spec-review.jsonl` 等。
- Learnings：通过 `gstack-learnings-log` 写入项目 learnings。

### 是否交互式

高度交互式。文档反复要求问题一次只问一个，很多阶段都有 STOP 点。它不能被一次性 summarize 成 doc；用户必须确认目标、premises、方案和 design doc approval。

### 与其他 skills 的链路

- 作为 `plan-ceo-review`、`plan-eng-review`、`plan-devex-review` 的前置增强输入：这些 review 在找不到 design doc 时会建议先跑 `/office-hours`。
- Phase 6 推荐后续：`/plan-ceo-review`、`/plan-eng-review`、`/plan-design-review`。
- 产出的 design doc 会被下游 review 自动发现和读取。

### 风险与限制

- 不适合已经明确要实现的窄 bugfix；会消耗大量交互。
- Startup mode 语气强势，可能让不需要商业验证的用户感到过度诊断；它用目标类型切换 Builder mode 缓解。
- 外部搜索需要隐私门禁；若跳过搜索，只能用内建知识。
- 产物在状态目录，不一定进 repo；团队协作时需要显式推广到 repo 文档。
- 对 `AskUserQuestion`、Codex、Agent、browser/design 工具可用性敏感。

### Codex 项目级示例

```text
$gstack-office-hours 我想做一个语音 agent 的 prompt 调试工作台，帮我先判断这个方向是否值得做，并产出 design doc。
```

## 2. plan-ceo-review

路径：`.agents/skills/gstack/plan-ceo-review/SKILL.md`

### 何时使用

用于战略、范围、产品方向、scope expansion/reduction、重大用户可见功能、计划是否正确的 CEO/founder-mode review。它不是代码 review，也不实现代码；目标是把 plan 变得更正确、更有野心或更聚焦。

### 期望用户输入

- 一个已有 plan、design doc、issue、PR/MR scope 或 branch diff。
- 用户可指定 posture，例如 go big、hold scope、reduce scope、show me options。
- 如果没有 design doc，skill 会建议先跑 `office-hours`。

### 工作流阶段

1. **Pre-review system audit**：读近期 git、diff、stash、TODO/FIXME、最近改动文件、`CLAUDE.md`、`TODOS.md`、架构文档；查 design doc 和 CEO handoff note。
2. **0A Premise Challenge**：判断是否在解决正确问题、是否是 proxy problem、不做会怎样。
3. **0B Existing Code Leverage**：把每个子问题映射到既有代码，避免重复造轮子。
4. **0C Dream State Mapping**：画 CURRENT STATE -> THIS PLAN -> 12-MONTH IDEAL。
5. **0C-bis Implementation Alternatives**：强制给 2-3 个实现路径，至少包含 minimal viable 和 ideal architecture。
6. **0D Mode-Specific Analysis**：根据模式运行扩展、选择性扩展、hold scope 或 reduction。
7. **0D-POST Persist CEO Plan**：在 expansion/selective expansion 时写 CEO plan，并跑 spec review loop。
8. **0E Temporal Interrogation**：从实现第 1 小时到 6 小时后推演将卡住的决策。
9. **0F Mode Selection**：确认四种模式之一：SCOPE EXPANSION、SELECTIVE EXPANSION、HOLD SCOPE、SCOPE REDUCTION。
10. **11 个 Review Sections**：架构、Error & Rescue、Security、Data/Interaction edge cases、Code quality、Tests、Performance、Observability、Deployment/Rollout、Long-term trajectory、Design/UX。
11. **Outside Voice**：可选 Codex 或 Claude subagent 独立挑战 plan。
12. **Required Outputs / Review Log / Dashboard / Plan File Report**：落盘 review 结果并更新 plan。

### 输出与 artifact

- Plan file 更新：`NOT in scope`、`What already exists`、`Dream state delta`、Error & Rescue Registry、Failure Modes Registry、mandatory diagrams、Implementation Tasks、`GSTACK REVIEW REPORT`。
- CEO plan：`~/.gstack/projects/$SLUG/ceo-plans/{date}-{feature}.md`，仅 expansion/selective expansion。
- Task JSONL：`~/.gstack/projects/$SLUG/tasks-ceo-review-*.jsonl`，供 `autoplan` 聚合。
- Review log：`gstack-review-log` 写 `plan-ceo-review`，字段含 status、critical gaps、mode、scope proposed/accepted/deferred、commit。
- Analytics：spec review metrics、telemetry。

### 是否交互式

高度交互式。每个 finding 都要求独立 AskUserQuestion，scope 和 mode 都是显式用户选择。Outside voice 的建议也不能自动应用。

### 与其他 skills 的链路

- 缺 design doc 时会建议 inline 跑 `office-hours`。
- 完成后根据 dashboard 推荐 `plan-eng-review`，UI scope 时推荐 `plan-design-review`。
- Expansion/selective expansion 产出的 CEO plan 可推广到 `docs/designs/{FEATURE}.md`。
- `autoplan` Phase 1 会加载并自动执行该 skill 的主体 review 方法。

### 风险与限制

- 很重，适合较大产品/架构计划；对小 bugfix 可能过度。
- Review sections 不允许跳过，容易产生长交互和大量 plan 写入。
- 文档要求许多 diagram 和 registry，若宿主没有 plan file 或 AskUserQuestion，会降低可用性。
- 生成后的 skill 路径引用 `~/.claude`，项目级使用时需要环境适配。
- 对外部 Codex/Agent 的 outside voice 是信息性增强，不应作为自动变更依据。

### Codex 项目级示例

```text
$gstack-plan-ceo-review 请用 SELECTIVE EXPANSION review 当前 voice-agent live-write plan，重点看是否解决了正确问题，以及哪些 30 分钟内的扩展值得 cherry-pick。
```

## 3. plan-eng-review

路径：`.agents/skills/gstack/plan-eng-review/SKILL.md`

### 何时使用

用于实现前的工程 plan review，覆盖架构、代码质量、测试、性能、失败模式、分发、TODO 交叉引用等。它是默认 shipping gate 类型的 plan-stage review，比 CEO review 更聚焦“能不能安全实现和运行”。

### 期望用户输入

- 已有 plan、issue、设计文档或 diff scope。
- 若 plan 无 design doc，skill 会建议先跑 `office-hours`，但用户可跳过标准 review。
- 用户需要对 scope reduction、具体架构问题、测试缺口等逐项决策。

### 工作流阶段

1. **Design Doc Check / Prerequisite Offer**：查 `~/.gstack/projects/$SLUG/*-design-*.md`，缺失则建议 `office-hours`。
2. **Step 0 Scope Challenge**：找既有代码可复用点，最小改动集，复杂度检查，搜索 built-in/best practice/pitfalls，TODO 交叉引用，完整性检查，分发检查。
3. **Review Sections**：Architecture、Code Quality、Test、Performance，至少四大块，不能因 plan 类型跳过。
4. **Confidence Calibration / Pre-emit verification gate**：finding 需要引用具体代码行，低信心 finding 降级。
5. **Outside Voice**：可选 Codex 或 Claude subagent 独立 plan challenge。
6. **Required Outputs**：NOT in scope、What already exists、TODOS updates、Failure modes、Parallelization plan、Implementation Tasks。
7. **Review Log / Dashboard / Plan File Report**：写 `plan-eng-review` review log，并更新 plan report。
8. **Next Steps**：UI scope 时建议 `plan-design-review`，重大产品变更时可提 `plan-ceo-review`。

### 输出与 artifact

- Plan file：scope challenge、architecture diagram、test diagram、failure mode registry、NOT in scope、existing reuse、Implementation Tasks、GSTACK REVIEW REPORT。
- Task JSONL：`~/.gstack/projects/$SLUG/tasks-eng-review-*.jsonl`。
- Review log：`plan-eng-review`，字段含 unresolved、critical_gaps、issues_found、mode、commit。
- 可能写 TODOs，逐项询问后才写。

### 是否交互式

交互式。复杂度触发、每个架构/质量/测试/性能 issue 都要求单独 AskUserQuestion，不能把 finding 一次性写进 plan 替代对话。

### 与其他 skills 的链路

- 可 inline 跑 `office-hours` 作为前置。
- Review 后建议 `plan-design-review` 或 `plan-ceo-review`。
- `autoplan` Phase 3 加载该 skill 并把 AskUserQuestion 变成自动决策。
- `/ship` dashboard 会读取它的 review log，Eng Review 是默认 shipping gate。

### 风险与限制

- 对“代码行引用”的要求适合已存在代码，但对纯 greenfield plan 可能需要明确说明没有证据。
- 搜索 built-in/best practice 依赖 WebSearch；不可用时只能说明使用内建知识。
- 过强的交互要求在无 AskUserQuestion 环境会阻塞。
- 它强调完整性和边界，可能扩大实现计划；用户需要明确区分 P1/P2/P3。

### Codex 项目级示例

```text
$gstack-plan-eng-review review specs/voice-agent-runtime.md，重点看架构、失败模式、测试矩阵和分发流程，先不要实现。
```

## 4. plan-design-review

路径：`.agents/skills/gstack/plan-design-review/SKILL.md`

### 何时使用

用于 UI/UX 相关计划的设计完整性 review。它 review 的对象是 plan，不是 live site；目标是让实现前的 plan 已经包含信息架构、状态、响应式、可访问性、AI slop 风险和设计系统对齐。

### 期望用户输入

- 一个含 UI scope 的 plan 或设计文档。
- 可提供 DESIGN.md、已有 UI 组件、mockup 偏好、跳过 mockup 的明确要求。
- 用户需要通过 comparison board 或 AskUserQuestion 反馈设计方向和 unresolved decisions。

### 工作流阶段

1. **Pre-review system audit**：读 plan、`CLAUDE.md`、`DESIGN.md`、`TODOS.md`、review logs，确认 UI scope。
2. **Design setup**：查 `design/dist/design` 和 `browse/dist/browse`，若可用则默认生成 mockups。
3. **Step 0 Design Scope Assessment**：给 plan 设计完整性初始评分、检查 DESIGN.md、列出既有 UI pattern、询问 focus areas。
4. **Step 0.5 Visual Mockups**：对 UI scope 默认用 `$D variants` 生成 mockups，`$D check` 质检，`$D compare --serve` 开 comparison board。
5. **7 个 Pass**：
   - Information Architecture
   - Interaction State Coverage
   - User Journey & Emotional Arc
   - AI Slop Risk
   - Design System Alignment
   - Responsive & Accessibility
   - Unresolved Design Decisions
6. **Post-Pass Update Mockups**：若 review 改动显著，可询问是否重新生成 mockups。
7. **Required Outputs**：NOT in scope、What already exists、TODOS、Implementation Tasks、Completion Summary、Approved Mockups。
8. **Review Log / Dashboard / Plan File Report / Next Steps**：写 design review metadata，建议后续 review 或 implementation。

### 输出与 artifact

- Design artifacts：`~/.gstack/projects/$SLUG/designs/<screen>-YYYYMMDD/`，包含 variants、comparison board、feedback、approved.json。
- Plan file：Approved Mockups 表、状态覆盖表、journey storyboard、NOT in scope、What already exists、Implementation Tasks、GSTACK REVIEW REPORT。
- Task JSONL：`tasks-design-review-*.jsonl`。
- Review log：`plan-design-review`，字段含 initial_score、overall_score、unresolved、decisions_made、commit。

### 是否交互式

高度交互式，但视觉选择通过 comparison board 完成。文档特别强调不要用 AskUserQuestion 直接问“选 A/B/C 图”，AskUserQuestion 只用于告知 board URL 并等待反馈。

### 与其他 skills 的链路

- DESIGN.md 缺失时建议 `design-consultation`。
- `plan-ceo-review` 在 UI scope 下会建议它做深度设计 review。
- `design-consultation` 可先建立设计系统，再由该 skill 校准计划。
- `autoplan` Phase 2 在检测到 UI scope 时加载它。
- 实现后建议跑 `design-review` 做 live rendered QA。

### 风险与限制

- 依赖 design binary 和可能的本地 HTTP server；在 Codex sandbox 下 serving localhost 可能需要非沙箱执行。
- Mockups 是用户状态数据，不进 repo；实现者需要能访问 `~/.gstack` artifact 路径。
- 若无 UI scope 应退出，不适合后端/API-only。
- AI slop blacklist 很强，会主动反对通用 SaaS 模板、紫色渐变、3-column feature grid 等。

### Codex 项目级示例

```text
$gstack-plan-design-review review 当前 dashboard UI plan。请默认生成 mockups，并检查 empty/error/loading states、mobile 和 a11y。
```

## 5. plan-devex-review

路径：`.agents/skills/gstack/plan-devex-review/SKILL.md`

直接相关文档：`.agents/skills/gstack/plan-devex-review/dx-hall-of-fame.md`

### 何时使用

用于 API、CLI、SDK、library、framework、platform、docs、Claude Code skill、MCP、AI agent tool 等 developer-facing surface 的 plan review。它不是给普通终端用户 UI 做 UX review，而是评估开发者从发现到 hello world、集成、debug、升级的完整体验。

### 期望用户输入

- 一个开发者面向产品/功能/工具的 plan。
- README/docs/package/CLI help/error message 作为证据来源。
- 用户需要确认 primary developer persona、TTHW 目标、magical moment 载体和 review 深度模式。

### 工作流阶段

1. **Pre-review system audit**：读 plan、`CLAUDE.md`、README、docs、package、CHANGELOG，扫描 getting started、CLI help、error patterns、examples。
2. **Applicability Gate**：自动判断 API/Service、CLI Tool、Library/SDK、Platform、Documentation、Claude Code Skill。无 developer-facing surface 时退出。
3. **Step 0 DX Investigation**：
   - 0A Developer Persona Interrogation
   - 0B Empathy Narrative
   - 0C Competitive DX Benchmarking
   - 0D Magical Moment Design
   - 0E Mode Selection：DX EXPANSION / DX POLISH / DX TRIAGE
   - 0F Developer Journey Trace
   - 0G First-Time Developer Roleplay
4. **0-10 Rating Method**：每个维度说明“对这个产品来说 10 分是什么”。
5. **8 个 Pass**：
   - Getting Started Experience
   - API/CLI/SDK Design
   - Error Messages & Debugging
   - Documentation & Learning
   - Upgrade & Migration Path
   - Developer Environment & Tooling
   - Community & Ecosystem
   - DX Measurement & Feedback Loops
6. **Claude Code Skill DX Checklist**：仅当产品类型包含 Claude Code skill 时运行。
7. **Outside Voice**：可选 Codex 或 Claude subagent 独立 plan challenge。
8. **Required Outputs / Implementation Tasks / Scorecard / Checklist**。
9. **Review Log / Plan File Report / Next Steps**。

### 输出与 artifact

- Plan file DX sections：Developer Persona Card、Empathy Narrative、Competitive Benchmark、Magical Moment Specification、Journey Map、Confusion Report、DX Scorecard、DX Implementation Checklist、NOT in scope、What already exists。
- Task JSONL：`~/.gstack/projects/$SLUG/tasks-devex-review-*.jsonl`。
- Review log：`plan-devex-review`，字段含 product_type、tthw_current、tthw_target、mode、persona、competitive_tier、initial/overall score、commit。
- Outside voice log：`codex-plan-review` 或相关 review log。

### 是否交互式

高度交互式。persona、empathy narrative、competitive target、magical moment、review mode 和每个 friction point 都要求用户决策。每个 issue 一次 AskUserQuestion。

### 与其他 skills 的链路

- 缺 design doc 时可建议 `office-hours`。
- `autoplan` Phase 3.5 在检测到 DX scope 时加载它。
- 实现后可用 `devex-review` 测量真实 DX 与 plan 的差距。
- 对 Claude Code skill/MCP 的 review 会加载 `dx-hall-of-fame.md` 中的专门 checklist。

### 风险与限制

- WebSearch 不可用时，竞品 benchmark 会退化到内建参考，例如 Stripe/Vercel/Firebase/Docker。
- 真实 TTHW 往往只能估算，除非实现后用 `devex-review` 实测。
- 对 docs 和 README 证据依赖强；文档缺失时 review 会倾向产出较多 docs 任务。
- 对用户 persona 的确认是核心 gate，跳过会降低后续评分可信度。

### Codex 项目级示例

```text
$gstack-plan-devex-review review 这个 MCP server onboarding plan，目标是让新开发者 5 分钟内完成 hello world，并检查错误消息和 docs。
```

## 6. autoplan

路径：`.agents/skills/gstack/autoplan/SKILL.md`

### 何时使用

用于“一键全 review”场景：用户要求 auto review、autoplan、run all reviews、review this plan automatically。它读取 CEO、design、eng、DX review skill 文件并按完整深度串行执行，用 6 条 decision principles 自动回答中间问题，最后只把 taste decisions 和 user challenges 交给用户确认。

### 期望用户输入

- 一个 plan 文件或当前计划上下文。
- 用户接受自动决策模式，并准备在最后 gate 审核 taste decisions / user challenges。
- 若有 UI 或 DX scope，会自动检测并包含对应 phase。

### 工作流阶段

1. **Phase 0 Intake + Restore Point**：备份 plan 原文到 `~/.gstack/projects/$SLUG/*-autoplan-restore-*.md`，并在 plan 顶部插入 restore comment。
2. **Read context**：读 `CLAUDE.md`、`TODOS.md`、git log、diff、design docs；检测 UI scope 和 DX scope。
3. **Load skill files from disk**：按需读取 `plan-ceo-review`、`plan-design-review`、`plan-eng-review`、`plan-devex-review`，跳过已由 autoplan 处理的共享段落。
4. **Phase 0.5 Codex auth + version preflight**：用 `gstack-codex-probe` 检测 Codex CLI。
5. **Phase 1 CEO Review**：固定 SELECTIVE EXPANSION，premises 是少数不能自动决定的 gate；运行双 voice 并产出 consensus table。
6. **Phase 2 Design Review**：UI scope 时运行 7 维设计 review 和双 voice。
7. **Phase 3 Eng Review + Dual Voices**：运行工程 review 与双模型共识。
8. **Phase 3.5 DX Review**：DX scope 时运行 developer experience review。
9. **Decision Audit Trail**：每个自动决策都追加到 plan。
10. **Pre-Gate Verification**：检查每个 phase 的 required outputs 是否真的存在。
11. **Phase 4 Final Approval Gate**：聚合 per-phase task JSONL，展示 plan summary、auto-decisions、taste choices、user challenges、scores、cross-phase themes、deferred TODOs、implementation tasks。
12. **Completion Review Logs**：用户批准后写各 review log 和 `autoplan-voices` log。

### 输出与 artifact

- Restore file：`~/.gstack/projects/$SLUG/{branch}-autoplan-restore-{timestamp}.md`。
- Plan file：Decision Audit Trail、各 phase 结果、最终 approval gate 内容。
- Per-phase tasks：来自 CEO/design/eng/DX skill 的 `tasks-*-review-*.jsonl`。
- Aggregated tasks：最终 gate 中聚合展示。
- Review logs：`plan-ceo-review`、`plan-eng-review`、可选 `plan-design-review`、`plan-devex-review`，带 `via:"autoplan"`。
- Voice logs：`autoplan-voices` 按 phase 记录 codex/subagent 共识。

### 是否交互式

半自动。绝大多数 AskUserQuestion 由 autoplan 按 6 原则自动决定；但两类不会自动决定：premises，以及两模型都建议改变用户原始方向的 User Challenge。最后有总 approval gate。

### 与其他 skills 的链路

- 直接加载并执行 `plan-ceo-review`、`plan-design-review`、`plan-eng-review`、`plan-devex-review` 的主体 review 方法。
- 跳过各 skill 的 preamble、review dashboard、plan file report、prerequisite offer、outside voice 等由 autoplan 自己处理的段落。
- 为 `/ship` 写入等价的 review logs，使 dashboard 识别已通过 review。

### 风险与限制

- 文档明确要求顺序执行 CEO -> Design -> Eng -> DX，不能并行，否则后续 phase 无法吸收前面决策。
- 自动决策可能掩盖用户偏好，因此需要 Decision Audit Trail 和 final gate。
- 如果 per-phase required outputs 没有真正写入 plan，pre-gate 只能重试有限次，可能带 warning 继续。
- Codex prompts 必须加 filesystem boundary，避免 Codex 误读 skill definitions。
- 对 plan file 可写性依赖很高；不适合无明确 plan 文件的松散聊天。

### Codex 项目级示例

```text
$gstack-autoplan 对当前 plan 做完整自动 review：CEO、Design、Eng、DX 都按需跑，最后只把 taste decisions 和 user challenges 交给我。
```

## 7. spec

路径：`.agents/skills/gstack/spec/SKILL.md`

### 何时使用

用于把已经值得做、方向基本确定的工作写成 backlog-ready spec/issue，并可选 spawn agent 执行。它不是 brainstorming 工具；如果用户还在探索是否要做，文档要求先路由到 `office-hours`。

### 期望用户输入

- 初始需求、bug、feature、refactor、audit/cleanup 方向。
- 可选 flags：`--dedupe`/`--no-dedupe`、`--no-gate`、`--audit`、`--execute`、`--no-execute`/`--file-only`、`--plan-file <path>`、`--sync-archive`。
- 用户需要回答 why/scope/technical questions，并确认 draft spec。

### 工作流阶段

1. **Flag parsing**：回显 dedupe、gate、audit、execute、plan-file、sync-archive 等解析结果。
2. **Phase 1 Understand the Why**：确认 who、current behavior、desired behavior、why now、done criteria。
3. **Dedupe check**：默认用 `gh issue list --search` 查近似 open issue；失败时非阻塞继续。
4. **Phase 2 Scope and Boundaries**：锁定 out of scope、触达系统、顺序约束、最小版本、失败模式和 rollback。
5. **Phase 3 Technical Interrogation**：硬要求先读代码证据，再问技术问题；必须引用文件/符号或说明 greenfield。
6. **Phase 4 Draft Review**：展示完整 draft issue，直到用户确认。
7. **Phase 4.5 Quality Gate**：默认用 Codex 评分 spec 可执行性；派发前先扫描 secret pattern，命中则 fail closed，不归档、不派发。
8. **Phase 5 File the Spec**：用 GitHub issue 或降级输出可粘贴 body；总是本地归档 spec。
9. **Optional Spawn Agent**：`--execute` path 下处理 dirty worktree、stash policy、SHA pin、唯一 worktree/branch、最终确认，然后 `claude -p`。
10. **TTHW telemetry / Handoff**：记录从 Phase 1 到首次 citation、到 file/spawn 的时间。

### 输出与 artifact

- GitHub issue：若 `gh` 可用且认证成功。
- Local spec archive：`$GSTACK_STATE_ROOT/projects/$SLUG/specs/{timestamp}-{pid}-{title}.md`，含 frontmatter：issue number/url、branch、plan mode、executed、worktree path、ttfc/tthw 等。
- Optional worktree：`../worktrees/{slug}-{pid}` 或配置的 `WORKTREE_PARENT`。
- Stash：dirty gate 选择 stash 时保留 `spec-execute-auto-$$`。
- 可能的 plan file：`--plan-file` 或 plan-mode 下把 spec 写入指定 plan 文件。

### 是否交互式

交互式。Phase 1/2/3 是问答式；duplicate issue、quality gate 低分、dirty worktree、最终 spawn 都需要用户决策。开放式问题用聊天，已知选项用 AskUserQuestion。

### 与其他 skills 的链路

- 前置：探索期应先 `office-hours`。
- 后置：如果 spec 暴露架构或设计风险，建议 `plan-eng-review` 或 `autoplan`。
- 实现 handoff：issue/归档 spec 本身就是给 implementer 或 spawned agent 的输入。
- `/ship` 可能利用 issue number 自动 close。

### 风险与限制

- `gh`、Codex、Claude CLI、git worktree 都是可选或环境依赖；每个失败都有降级路径，但自动执行能力会下降。
- Secret redaction gate 很关键；若用户需求包含密钥，quality gate 会阻塞。
- Spawn agent 在 dirty worktree 场景有 TOCTOU 和 stash 复杂度；文档要求重查状态并保守处理。
- 归档默认本地，`--sync-archive` 才进入 sync，避免把敏感 spec 推到共享 artifact。

### Codex 项目级示例

```text
$gstack-spec --no-execute 为“修复语音 agent 断线后的重连状态恢复”写一个可执行 issue，先读现有 server/session 代码再问技术问题。
```

## 8. design-consultation

路径：`.agents/skills/gstack/design-consultation/SKILL.md`

### 何时使用

用于创建或更新设计系统、品牌指南、`DESIGN.md`，或在产品方向明确后为 UI/网站/工具建立完整视觉系统。它是设计顾问式对话，不是简单选项表单。

### 期望用户输入

- 产品是什么、给谁用、属于什么空间/行业、项目类型。
- 是否需要竞品/视觉研究。
- “第一次看到产品后希望别人记住什么”的一句话。
- 对提案中的 aesthetic、color、typography、layout、spacing、motion、risks 的反馈。

### 工作流阶段

1. **Phase 0 Pre-checks**：查现有 `DESIGN.md`/`design-system.md`，读 README/package/source 结构，读取 office-hours output。
2. **Browse setup**：可选构建/使用 `browse` 做视觉研究。
3. **Design setup**：可选使用 `design` binary 生成 AI mockups；设计 artifact 必须写到 `~/.gstack/projects/$SLUG/designs/`。
4. **Prior Learnings**：读取 learnings。
5. **Phase 1 Product Context**：用一个大问题确认产品上下文、项目类型、是否调研，并问 memorable thing。
6. **Taste Profile**：读取 `~/.gstack/projects/$SLUG/taste-profile.json`，基于历史 approved/rejected 调整提案。
7. **Phase 2 Research**：若用户同意，WebSearch 找竞品，browse top sites，做三层 synthesis。
8. **Design Outside Voices**：可选 Codex design voice 和 Claude subagent 并行给方向。
9. **Phase 3 Complete Proposal**：一次性提出 coherent package：aesthetic、decoration、layout、color、typography、spacing、motion、safe choices、risks。
10. **Phase 4 Drill-downs**：用户要求调整某一维时深入。
11. **Phase 5 Design System Preview**：
    - Path A：DESIGN_READY 时生成 AI mockups、comparison board、feedback loop、approved.json，并可 `$D extract` tokens。
    - Path B：fallback 生成自包含 HTML preview。
12. **Phase 6 Write DESIGN.md & Confirm**：plan mode 下写 Proposed DESIGN.md 到 plan；非 plan mode 下写 repo 根 `DESIGN.md` 并更新 `CLAUDE.md`。

### 输出与 artifact

- `DESIGN.md`：非 plan mode 下写 repo 根，含 product context、aesthetic、typography、color、spacing、layout、motion、decisions log。
- `CLAUDE.md` 追加 Design System 指引：视觉/UI 决策必须读 `DESIGN.md`。
- Plan mode 下：写 `## Proposed DESIGN.md` 与 `## Approved Design Direction` 到 plan file，不直接写 repo 文件。
- Design artifacts：`~/.gstack/projects/$SLUG/designs/design-system-YYYYMMDD/`，包含 variants、board、feedback、approved.json。
- Taste profile 可能被读取/更新，design outside voices 写 `design-outside-voices` review log。

### 是否交互式

交互式。它用 AskUserQuestion 收集上下文、展示完整提案、等待 comparison board feedback、确认最终写入。文档强调用户可以随时自然语言讨论，不需要 rigid subcommand。

### 与其他 skills 的链路

- 若产品方向不清，建议先 `office-hours`。
- `plan-design-review` 在没有 DESIGN.md 时会建议跑它。
- 完成后建议 `design-html` 将设计系统转成工作 HTML。
- `design-review`/`qa` 可后续检查实现是否遵守 DESIGN.md。

### 风险与限制

- 会写 repo 根 `DESIGN.md` 和修改 `CLAUDE.md`，但仅在非 plan mode 且用户确认后。
- 竞品研究依赖 WebSearch/browse；不可用时退化到内建知识。
- Design binary 可用时会开本地 comparison board，受 sandbox/localhost 限制。
- 对字体和 AI slop 有强 opinion，例如禁止 Inter/Roboto/Arial/system 作为 primary，可能与现有品牌冲突，需要用户最终决定。

### Codex 项目级示例

```text
$gstack-design-consultation 给 VoiceAgents 建一个 DESIGN.md。产品是给开发者调试语音 agent 的工作台，我想要专业、可扫描、不是通用 SaaS 模板。
```

## 9. plan-tune

路径：`.agents/skills/gstack/plan-tune/SKILL.md`

直接相关文档：`.agents/skills/gstack/docs/designs/PLAN_TUNING_V0.md`

### 何时使用

用于调优 gstack skills 的提问敏感度和开发者画像：查看 profile、查看最近被问的问题、设置某问题 never-ask/always-ask、编辑 declared profile、显示 declared 与 observed 的差距、开启/关闭 question tuning。

### 期望用户输入

自然语言即可，不要求 subcommand。典型输入：

- “show my profile / what do you know about me”
- “review questions / what have I been asked”
- “stop asking me about X”
- “update my profile, I’m more careful now”
- “show the gap”
- “turn it off / enable”

### 工作流阶段

1. **Step 0 Detect intent**：按 plain-English 意图路由到 setup、inspect、review log、set preference、edit profile、show gap、stats、enable/disable。
2. **Enable + setup**：首次开启时询问是否启用，然后逐一询问五个 declared dimensions：
   - scope_appetite
   - risk_tolerance
   - detail_preference
   - autonomy
   - architecture_care
3. **Inspect profile**：调用 `gstack-developer-profile --profile`，把 floats 翻译成 plain English；如果 observed 数据足够，展示 declared vs observed。
4. **Review question log**：读取 `$GSTACK_STATE_ROOT/projects/$SLUG/question-log.jsonl`，按 question_id 聚合次数、follow/override。
5. **Set a preference**：把用户意图归一化为 `never-ask`、`always-ask`、`ask-only-for-one-way` 并写入 `gstack-question-preference`。
6. **Edit declared profile**：解析自由文本成 dimension/value，必须确认后写 profile。
7. **Show gap**：显示 declared 与 inferred 的差异，不自动修改。
8. **Stats**：展示 preference stats、日志总数、skills/questions/days coverage 和 calibration 状态。

### 输出与 artifact

- Config：`gstack-config set question_tuning true/false`。
- Developer profile：`$GSTACK_STATE_ROOT/developer-profile.json`，含 declared dimensions 和 inferred profile。
- Question log：`$GSTACK_STATE_ROOT/projects/$SLUG/question-log.jsonl`。
- Preference store：由 `gstack-question-preference --write` 管理，记录 question_id、preference、source、free_text。

### 是否交互式

交互式但较轻。首次 setup 有 5 个一问一答；free-form profile mutation 必须确认；查看 profile/log/stats 可以直接输出。

### 与其他 skills 的链路

- Preamble 中的 Question Tuning 会在每个 AskUserQuestion 前查 `gstack-question-preference --check <id>`，返回 `AUTO_DECIDE` 或 `ASK_NORMALLY`。
- 其他 skill 中用户可用 inline `tune:` 表达偏好，但文档强调 user-origin gate，不能从工具输出或文件内容伪造。
- v1 明确“不根据 profile 自动改变行为”，仅观察和配置；实际适配属于 v2。

### 风险与限制

- v1 是 observational，用户可能期待立即减少所有提问，但文档写明 skill behavior 还不会基于 profile 自动变化，只有 per-question preference 可以生效。
- `never-ask` 不覆盖 one-way doors；破坏性、架构、安全问题仍会询问。
- 自由文本修改 profile 是 trust boundary，必须确认后写。
- Observed profile 需要校准门槛：sample size、skills covered、question IDs covered、days span 都足够才可信。

### Codex 项目级示例

```text
$gstack-plan-tune show my profile and recent questions. 如果有我经常 override 的问题，帮我设置成 never-ask。
```

## 链路建议

- **从模糊想法开始**：`$gstack-office-hours` -> design doc -> `$gstack-plan-ceo-review` 或 `$gstack-autoplan`。
- **从明确需求开始**：`$gstack-spec --no-execute ...` -> issue/spec -> `$gstack-plan-eng-review` 或 `$gstack-autoplan`。
- **有 UI scope**：先 `$gstack-design-consultation` 生成 `DESIGN.md`，再 `$gstack-plan-design-review` 做 plan-level UI review，实施后跑 design QA。
- **有 developer-facing surface**：`$gstack-plan-devex-review` 或让 `$gstack-autoplan` 自动检测 DX scope。
- **觉得 gstack 问太多或问错**：`$gstack-plan-tune` 查看 question log，设置 per-question preferences。

## 使用本项目级 gstack 的注意事项

- 不要调用根 `$gstack`；使用生成后的 `$gstack-*` 名称。
- 手动运行 bin/design/browse 脚本时，优先使用项目级环境：

```bash
env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" <gstack-command>
```

- 设计和 browse 类功能可能需要 localhost 或打开浏览器，在 Codex sandbox 中可能需要申请非沙箱执行。
- 多 agent 并行探索时，只写自己分配的文件，避免修改 shared gstack checkout 或其他 `gstack_explore/` 文件。
