# gstack review / debug / security / quality / safety skills 分析

本报告基于项目本地 checkout：`.agents/skills/gstack`。本项目约定使用 Codex 生成后的项目级技能名，例如 `$gstack-review`，不要调用根 `$gstack`。下文示例统一使用 `$gstack-*` 命名；技能文件内部仍有自动生成的 `~/.claude/skills/gstack/...` 路径，这是上游模板遗留/兼容路径，实际在本项目中应优先理解为项目级 gstack runtime 的等价入口。

## 总览

| Skill | 核心用途 | 是否改代码 | 安全/约束重点 | 典型输出 |
|---|---|---:|---|---|
| `$gstack-review` | 合并前 PR/diff 审查 | 是，Fix-First | 必须读完整 diff；机械项自动修，风险项询问；不提交不推送 | Pre-Landing Review、Scope Check、specialist/adversarial findings、review log |
| `$gstack-investigate` | 复现、定位、修复 bug | 是，根因确认后 | Iron Law：无根因不修；3 个假设失败就停；可自动 freeze 编辑范围 | DEBUG REPORT |
| `$gstack-cso` | 安全态势审计 | 不改业务代码 | read-only；daily 8/10 置信门；comprehensive 2/10；反提示注入 | Security Posture Report、`.gstack/security-reports/*.json` |
| `$gstack-health` | 代码质量仪表盘 | 不修问题 | 只运行项目已有工具；跳过缺失工具不扣分 | CODE HEALTH DASHBOARD、health history |
| `$gstack-codex` | 调 Codex CLI 做第二意见 | 通常不直接改代码 | Codex 子进程 read-only；边界提示禁止读技能目录 | CODEX SAYS、gate/recommendation、session id |
| `$gstack-careful` | destructive Bash 命令警告 | 不改代码 | `rm -rf`、DROP、force-push 等返回 ask | hook warning |
| `$gstack-freeze` | 限制 Edit/Write 到目录 | 只写状态文件 | 越界 Edit/Write 直接 deny；Bash 不受限 | freeze boundary |
| `$gstack-guard` | careful + freeze | 只写状态文件 | Bash destructive ask + Edit/Write boundary deny | guard mode active |
| `$gstack-unfreeze` | 清除 freeze boundary | 只删状态文件 | 只解除编辑边界，不卸载 hook | boundary cleared |

## 关键区分：review vs investigate

`$gstack-review` 是“合并前质量门”。它从当前分支相对 base branch 的 diff 出发，问的是“这批变更能不能安全 landing、有没有范围漂移、有没有结构性问题”。它会检查 plan/intent、完整 diff、review checklist、specialist subagents、Claude/Codex adversarial review，并进入 Fix-First 流程：机械修复可自动应用，安全/竞态/用户可见行为等需要用户确认。它不负责从一个用户报告的生产现象里证明根因。

`$gstack-investigate` 是“debug/root cause 模式”。它从症状、错误、堆栈、复现步骤出发，硬性要求先定位根因再修复。它的 Iron Law 是 `NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST`。如果无法复现或假设未验证，就继续收集证据；3 个假设失败后必须停下来询问继续、升级人工、还是加日志等待。review 里出现“需要判断/无法证明”的问题可以转入 investigate；investigate 修完后再跑 review/health 才是正常收尾。

## `$gstack-review`

### 何时使用

用于 “review this PR”、“code review”、“check my diff”、“pre-landing review”，也适合在 `$gstack-ship` 前确认当前分支是否可合并。它审当前分支相对 base branch 的变更，而不是全仓库安全扫描或运行所有健康检查。

示例：

```text
$gstack-review
$gstack-review --security
$gstack-review --all-specialists
```

### 工作流/阶段

1. 检测 git 平台和 base branch：GitHub/GitLab CLI 优先，失败后用 `origin/HEAD`、`origin/main`、`origin/master`，最后 fallback 到 `main`。
2. 检查当前分支：如果在 base branch 或没有 diff，输出 `Nothing to review` 并停止。
3. Scope Drift Detection：读取 `TODOS.md`、PR 描述、commit messages，判断 stated intent、delivered diff、scope creep、missing requirements。
4. Plan completion audit：如果找到 plan file，抽取 actionable items，按 DIFF-VERIFIABLE / CROSS-REPO / EXTERNAL-STATE / CONTENT-SHAPE 分类，和 diff 或可达 sibling repo 证据交叉验证。
5. 读取 `review/checklist.md`，再获取完整 diff。critical pass 覆盖 SQL/data safety、竞态、LLM output trust boundary、shell injection、enum/value completeness。enum/value completeness 明确要求读 diff 之外的消费者。
6. Greptile 集成是 additive：有 PR 评论就 triage，没有就静默跳过。
7. specialist dispatch：50 行以上 diff 默认派发 Testing、Maintainability；按 scope 派发 Security、Performance、Data Migration、API Contract、Design；大 diff 或 critical finding 触发 Red Team。
8. Fix-First：对所有 finding 分类为 AUTO-FIX 或 ASK。机械项直接改；风险项批量询问用户。
9. 文档陈旧检查、TODO cross-reference、always-on adversarial review。Claude adversarial 总是运行；Codex available 时运行 Codex adversarial；200+ 行 diff 或用户明确 full/structured/P1 gate 时运行 Codex structured review。
10. 记录 review outcome 到 gstack review log，并可记录 learning。

### 收集的证据

它会收集 branch/base、`git diff` 和 `git diff --stat`、commit log、PR body、`TODOS.md`、plan file、review checklist、Greptile comments、specialist subagent JSON findings、Codex/Claude adversarial 输出、文档与代码变更的对应关系、过往 review log 和 learnings。

### 编辑行为

`$gstack-review` 不是纯 read-only。它的规则是 Fix-First：

- AUTO-FIX：死代码、unused variables、明显 N+1、stale comments、magic numbers、缺失轻量 LLM output validation、version/path mismatch、inline styles、O(n*m) view lookup 等可直接修。
- ASK：auth/XSS/injection、race condition、设计决策、大于约 20 行的修复、enum completeness、删除功能、用户可见行为变化。
- test_stub override：specialist 提供 test_stub 时转为 ASK，用户批准后写 fix + test。
- 不提交、不推送、不创建 PR，这些留给 `$gstack-ship`。

### 安全约束

必须读完整 diff；不能报告 diff 中已经修复的问题。任何“安全”“已覆盖”“handled elsewhere”声明都要引用具体代码或测试。confidence < 5 的内容不能进主 finding。Codex 调用带有 filesystem boundary，要求不要读 `~/.claude/`、`~/.agents/`、`.claude/skills/`、`agents/`，避免把技能提示当作项目代码。Codex adversarial 错误非阻塞，属于增强信号。

### 预期输出

输出通常包含：

- `Scope Check: CLEAN / DRIFT DETECTED / REQUIREMENTS MISSING`
- `PLAN COMPLETION AUDIT`
- `Pre-Landing Review: N issues (X critical, Y informational)`
- `SPECIALIST REVIEW`
- `ADVERSARIAL REVIEW`
- `ADVERSARIAL REVIEW SYNTHESIS`
- 自动修复摘要和需要用户输入的列表
- `gstack-review-log` 持久化记录

### 与正常开发组合

常规顺序：实现功能和测试后先跑项目测试，再跑 `$gstack-review`。如果 review 报出可复现 bug 或需要根因判断的 finding，转 `$gstack-investigate`。修完后跑 `$gstack-health` 看整体质量分，再重新 `$gstack-review`，最后由 ship 流程处理版本、changelog、commit/PR。

## `$gstack-investigate`

### 何时使用

用于 “debug this”、“fix this bug”、“why is this broken”、“root cause analysis”、“investigate this error”，也应在用户贴出 500、stack trace、unexpected behavior、“昨天还能用”时优先使用。不要直接猜修复。

示例：

```text
$gstack-investigate "登录后重定向循环"
$gstack-investigate "API 500: TypeError in billing route"
```

### 工作流/阶段

1. Phase 1 Root Cause Investigation：收集症状、错误、堆栈和复现步骤；读代码路径；查 affected files 最近 git log；尝试确定性复现；查 prior learnings。
2. 形成 `Root cause hypothesis: ...`，必须是具体、可测试的声明。
3. Scope Lock：根因假设形成后，尝试把编辑范围锁到最窄目录，写入 freeze state。若 bug 跨全仓或范围不清，说明原因并跳过。
4. Phase 2 Pattern Analysis：匹配 race、nil/null、state corruption、integration failure、configuration drift、stale cache 等模式；查 `TODOS.md` 和同区域历史修复。
5. Phase 3 Hypothesis Testing：先加临时日志/断言/调试输出验证假设。假设失败则回到 Phase 1；3 个假设失败必须 AskUserQuestion。
6. Phase 4 Implementation：根因确认后最小 diff 修根因，写 regression test，跑完整测试。修复超过 5 个文件必须询问 blast radius。
7. Phase 5 Verification & Report：重新复现原 bug 并确认已修，跑测试，输出 DEBUG REPORT，记录 investigation learning。

### 收集的证据

它关注症状、复现步骤、stack trace、错误日志、代码路径、引用搜索、affected files 的 `git log --oneline -20`、prior learnings、假设验证输出、回归测试、完整测试输出、原始 bug 场景的 fresh verification。

### 编辑行为

只有在 root cause 已确认后才允许修复。修复应尽量小，只改根因，不做邻近重构。它会尝试使用 freeze hook 限制 Edit/Write 到 affected module。调试用临时日志/断言可以作为验证手段，但最终报告需要说明证据；临时调试代码不应残留，除非它是有意添加的生产诊断。

### 安全约束

核心约束是 Iron Law：无根因不修。3+ failed fix attempts 或 3 个假设失败时停止并重新评估架构/升级。外部搜索必须先脱敏：去掉 hostname、IP、路径、SQL、客户标识和内部数据。无法验证的修复不能声称完成；不能说 “this should fix it”。触及 >5 文件必须询问用户。

### 预期输出

最终输出结构：

```text
DEBUG REPORT
Symptom:         ...
Root cause:      ...
Fix:             ...
Evidence:        ...
Regression test: ...
Related:         ...
Status:          DONE | DONE_WITH_CONCERNS | BLOCKED
```

状态语义：`DONE` 代表根因找到、修复应用、回归测试写好、测试通过；`DONE_WITH_CONCERNS` 代表修了但不能完全验证；`BLOCKED` 代表根因不清或已升级。

### 与正常开发组合

bug 修复建议顺序：`$gstack-investigate` 定位和修复，之后运行项目相关测试，再 `$gstack-health` 看质量回归，最后 `$gstack-review` 检查 diff 是否引入结构风险。若 investigate 自动设置 freeze，完成后用 `$gstack-unfreeze` 放开后续编辑范围。

## `$gstack-cso`

### 何时使用

用于 “security audit”、“threat model”、“pentest review”、“OWASP”、“security check”、“vulnerability scan”。这是安全态势审计，不是 PR review，也不是 bug fix。

示例：

```text
$gstack-cso
$gstack-cso --comprehensive
$gstack-cso --infra --diff
$gstack-cso --code
$gstack-cso --skills
$gstack-cso --supply-chain
$gstack-cso --owasp
$gstack-cso --scope auth
```

### 工作流/阶段

参数解析规则很严格：

- 无 flag：全量 daily audit，phase 0-14，8/10 confidence gate。
- `--comprehensive`：全量深扫，2/10 gate，低置信项标为 `TENTATIVE`。
- scope flags 互斥：`--infra`、`--code`、`--skills`、`--supply-chain`、`--owasp`、`--scope` 不能同时出现。多选必须报错，不能静默选择。
- `--diff` 可和任意 scope / comprehensive 组合，只看当前分支变更；git history 扫描限制到当前分支 commits。
- Phase 0、1、12、13、14 总是运行。

主要 phase：

0. 架构心智模型和 stack/framework detection。
1. Attack Surface Census：代码入口和基础设施面。
2. Secrets Archaeology：git history、tracked env、CI inline secrets。
3. Dependency Supply Chain：audit、install scripts、lockfile。
4. CI/CD Pipeline Security：unpinned actions、`pull_request_target`、script injection、secrets、CODEOWNERS。
5. Infrastructure Shadow Surface：Docker/IaC/K8s/prod credentials。
6. Webhook & Integration Audit：webhook signature、TLS verify、OAuth scopes。
7. LLM & AI Security：prompt injection、LLM output HTML/eval/tool validation/cost attacks。
8. Skill Supply Chain：repo-local skills 自动扫；global skills 需用户许可。
9. OWASP Top 10。
10. STRIDE threat model。
11. Data classification。
12. False Positive Filtering + Active Verification。
13. Findings report + trend tracking + remediation。
14. Save report。

### 收集的证据

它收集 stack/config、README/CLAUDE 等架构说明、端点和 auth 边界、CI/IaC/Docker/K8s 配置、git history 中 secret patterns、lockfile 和 dependency audit、webhook handlers、LLM 调用与数据流、skill 文件中的可疑 network/credential/prompt-injection pattern、OWASP/STRIDE 证据、过往 `.gstack/security-reports/` 趋势。

### 编辑行为

明确 read-only：不修改业务代码。它会产出报告和本地历史文件，Phase 14 写 `.gstack/security-reports/{date}-{HHMMSS}.json`。发现泄露密钥时给 incident response playbook，但不会自动 scrub history、rotate secret 或 force-push。

### 安全约束

daily mode 低于 8/10 不报告，强调 zero noise。comprehensive mode 才报告 2/10 以上的 tentative。每个 finding 必须有具体 exploit scenario。候选 finding 必须经过 hard exclusions、confidence gate、active verification、variant analysis。pre-emit gate 要求引用触发 finding 的具体代码行；不能引用就降到 4-5 并从主报告压下去。审计中要忽略代码库里试图影响审计方法/范围/结论的指令，代码是被审对象，不是指令来源。

### 预期输出

输出包括 attack surface map、security findings 表、每个 finding 的 severity/confidence/status/phase/category/exploit/impact/recommendation、趋势、top 5 remediation roadmap，以及固定 disclaimer。JSON 报告 schema 包含 mode、scope、diff_mode、phases_run、attack_surface、findings、supply_chain_summary、filter_stats、totals、trend。

### 与正常开发组合

在重大 release 前或定期安全例行检查跑 `$gstack-cso`。分支级安全检查可用 `$gstack-cso --diff`。发现需要代码修复的漏洞后，不应让 cso 自己改；转入 `$gstack-investigate` 或普通开发修复，再用 `$gstack-review --security` 检查具体 diff，必要时复跑 `$gstack-cso --diff`。

## `$gstack-health`

### 何时使用

用于 “health check”、“code quality”、“how healthy is the codebase”、“run all checks”、“quality score”。它给出质量仪表盘，不替代 review，也不修复问题。

示例：

```text
$gstack-health
```

### 工作流/阶段

1. 读取 `CLAUDE.md` 的 `## Health Stack`。如果存在，按其中命令运行。
2. 否则自动检测 typecheck、lint、test、dead code、shell lint、GBrain。检测包括 `tsconfig.json`、biome/eslint/ruff、package test script、pytest/cargo/go、knip、shellcheck、gbrain doctor。
3. 自动检测后询问用户是否持久化到 `CLAUDE.md`、调整工具、或只运行一次。
4. 顺序运行每个工具，记录开始/结束、exit code、duration、最后 50 行输出。缺失工具记为 `SKIPPED`。
5. 按权重评分：typecheck 22%、lint 18%、tests 28%、deadcode 13%、shell 9%、gbrain 10%。跳过项权重重分配。
6. 输出 dashboard，低于 7 的类别展示具体输出。
7. 写 `~/.gstack/projects/$SLUG/health-history.jsonl`，再读最近 10 次做趋势分析和建议。

### 收集的证据

它只使用项目已有工具的结果：type/lint/test/dead code/shellcheck/gbrain doctor 输出、exit code、耗时、历史 health entries。失败时要展示 raw tail 输出，方便用户直接定位。

### 编辑行为

硬门是 “Do NOT fix any issues”。唯一可能的编辑是用户选择持久化 health stack 时追加/更新 `CLAUDE.md` 的 `## Health Stack`。除此之外，只写本地 gstack health history。

### 安全约束

不能用自己的主观分析替代项目工具。工具不存在就是 skipped，不算失败。尊重 `CLAUDE.md` 已配置命令，不重新发明检查命令。运行顺序是 sequential，因为工具可能共享资源或锁文件。`gbrain doctor --json` 必须 5 秒 timeout，避免卡住整次 health。

### 预期输出

核心输出：

```text
CODE HEALTH DASHBOARD
Category | Tool | Score | Status | Duration | Details
COMPOSITE SCORE: N / 10
HEALTH TREND
REGRESSIONS DETECTED
RECOMMENDATIONS
```

### 与正常开发组合

适合在修复后、review 前、ship 前跑。`$gstack-health` 告诉你类型/测试/lint/死代码有没有退化；`$gstack-review` 告诉你 diff 的结构风险；`$gstack-cso` 告诉你安全态势风险。三者不是互相替代。

## `$gstack-codex`

### 何时使用

用于 “codex review”、“codex challenge”、“ask codex”、“second opinion”、“outside voice challenge”。它是 OpenAI Codex CLI wrapper，提供 review、challenge、consult 三种模式。

示例：

```text
$gstack-codex review
$gstack-codex review focus on API contract
$gstack-codex challenge
$gstack-codex challenge security
$gstack-codex "这个 migration 顺序有没有风险？"
$gstack-codex review --xhigh
```

### 工作流/阶段

1. 检查 `codex` binary；不存在则停止并提示安装。
2. Auth probe 和版本检查：接受 `CODEX_API_KEY`、`OPENAI_API_KEY` 或 `${CODEX_HOME:-~/.codex}/auth.json`。已知坏版本 `0.120.0`、`0.120.1`、`0.120.2` 会 warning。
3. 解析 portable roots：`PLAN_ROOT` 和 `TMP_ROOT`。
4. 检测模式：
   - `review`：对当前分支 diff 做 code review，有 pass/fail gate。
   - `challenge`：adversarial，找 edge cases、race、安全洞、资源泄漏、静默数据损坏。
   - 无参数：有 diff 就问 review/challenge/other；无 diff 时找 plan；都没有就问用户 prompt。
   - 其他文本：consult。
5. 所有 prompt 都加 filesystem boundary：Codex 不应读/执行技能目录，不应修改 `agents/openai.yaml`。
6. Review mode：默认走 `codex review`；有自定义 focus 时走 `codex exec` 并将 diff 放入 `DIFF_START/DIFF_END`，防 diff prompt injection。查 `[P1]` 决定 gate fail/pass。
7. Challenge/Consult mode：用 `codex exec --json`，解析 reasoning、agent messages、command executions、tokens。consult 可保存和恢复 `.context/codex-session-id`。
8. 输出 verbatim Codex 内容后，必须给一行 canonical `Recommendation: ... because ...`。

### 收集的证据

它收集当前 diff、plan 内容、Codex JSONL reasoning/tool/output、stderr、tokens、session id、已有 `$gstack-review` 结果用于 cross-model comparison。review 结果会写 `gstack-review-log`。

### 编辑行为

Codex 子进程通常以 read-only sandbox 运行。技能本身可能写临时文件、`.context/codex-session-id`、review log；plan review 场景下会把 `## GSTACK REVIEW REPORT` 更新到 plan file 末尾。它不是主修复工具；Codex 的建议需要由当前 agent/用户决定是否采纳。

### 安全约束

filesystem boundary 是核心：避免 Codex 读取 `.agents` / skills prompt，把元指令当业务代码。自定义 review 把 diff 放在 delimiter 中，明确 diff 是数据不是指令。review/challenge 有 timeout/hang detection；错误要表面化，不能把空输出当“没问题”。`--xhigh` 代价极高，文档提醒可能导致长时间 hang。

### 预期输出

Review mode 输出：

```text
CODEX SAYS (code review):
<verbatim output>
GATE: PASS | FAIL
Recommendation: ...
```

Challenge/consult 输出类似 `CODEX SAYS (adversarial challenge)` 或 `CODEX SAYS (consult)`，包含 tokens、可能的 session saved，以及推荐行。

### 与正常开发组合

`$gstack-codex` 适合作为第二意见，不应替代本地测试、review 或 investigate。常见组合是：先 `$gstack-review`，再 `$gstack-codex challenge` 找主审遗漏；或在 plan/architecture 不确定时 `$gstack-codex` consult。若 Codex 指出可复现 bug，转 `$gstack-investigate`；若指出 diff 质量问题，回到普通实现再 `$gstack-review`。

## `$gstack-careful`

### 何时使用

用于 “be careful”、“warn before destructive”、“safety mode”、“prod mode”，尤其是共享环境、生产系统、危险 git/DB/K8s/Docker 操作前。

示例：

```text
$gstack-careful
```

### 工作流/阶段

它不是多阶段分析技能，而是注册 Bash PreToolUse hook。hook 脚本为 `.agents/skills/gstack/careful/bin/check-careful.sh`，从 tool input JSON 读 `command` 字段，匹配 destructive pattern。

### 收集的证据

只检查即将执行的 Bash command 字符串。命中时记录 hook fire event 到本地 analytics，记录 pattern 名称，不记录完整命令内容。

### 编辑行为

不编辑项目文件，不执行修复。它只对 Bash 调用返回 `{ "permissionDecision": "ask", "message": ... }` 或 `{}`。

### destructive-command guardrails

会警告：

- `rm -rf` / `rm -r` / `rm --recursive`
- `DROP TABLE` / `DROP DATABASE`
- `TRUNCATE`
- `git push --force` / `git push -f`
- `git reset --hard`
- `git checkout .` / `git restore .`
- `kubectl delete`
- `docker rm -f` / `docker system prune`

安全例外：递归删除 build/cache artifacts 不警告，包括 `node_modules`、`.next`、`dist`、`__pycache__`、`.cache`、`build`、`.turbo`、`coverage`。

### 安全约束

这是 warning，不是 block。用户可以 override。它只覆盖 Bash 工具，不覆盖 Edit/Write。hook session-scoped，结束会话或新会话后失效。

### 预期输出

命中时出现类似：

```json
{"permissionDecision":"ask","message":"[careful] Destructive: git reset --hard discards all uncommitted changes."}
```

### 与正常开发组合

在调查生产、清理目录、改 git history、操作集群前先 `$gstack-careful`。如果同时还要限制文件编辑范围，直接用 `$gstack-guard`。

## `$gstack-freeze`

### 何时使用

用于 “freeze edits to directory”、“lock editing scope”、“only edit this folder”。适合 debug 时防止顺手改无关代码，也适合多人并行时限制 blast radius。

示例：

```text
$gstack-freeze
# 回答：src/auth/
```

### 工作流/阶段

1. AskUserQuestion 询问要限制的目录。
2. 将用户路径解析为绝对路径。
3. 确保 trailing slash，写入 freeze state file：`$GSTACK_STATE_ROOT/freeze-dir.txt`。
4. Edit/Write PreToolUse hook 调用 `.agents/skills/gstack/freeze/bin/check-freeze.sh`。
5. hook 从 tool input JSON 读 `file_path`，规范化绝对路径和 symlink/`..`，检查是否以 freeze dir 开头。

### 收集的证据

只读取用户选择的目录和每次 Edit/Write 的 `file_path`。越界时记录 hook fire event。

### 编辑行为

它只写 freeze state file。业务文件只有在位于 boundary 内时才允许通过正常 Edit/Write 修改。

### 安全约束

越界 Edit/Write 返回 `permissionDecision: "deny"`，这是阻断，不是询问。trailing slash 防止 `/src` 错配 `/src-old`。但它不是安全沙箱：Read、Bash、Glob、Grep 不受影响，Bash 里的 `sed -i` 等仍可能改 boundary 外文件。它防误操作，不防恶意绕过。

### 预期输出

设置后告知：

```text
Edits are now restricted to <path>/. Any Edit or Write outside this directory will be blocked.
```

越界时：

```json
{"permissionDecision":"deny","message":"[freeze] Blocked: ... is outside the freeze boundary (...)."}
```

### 与正常开发组合

debug 单模块时先 freeze，再 `$gstack-investigate` 或普通编辑。`$gstack-investigate` 本身在形成根因假设后也会尝试自动 scope lock。需要扩大范围时用 `$gstack-unfreeze` 或重新 `$gstack-freeze`。

## `$gstack-guard`

### 何时使用

用于 “full safety mode”、“guard mode”、“maximum safety”、“lock it down”。它等于 `$gstack-careful` + `$gstack-freeze`。

示例：

```text
$gstack-guard
# 回答：server/auth/
```

### 工作流/阶段

1. 注册 Bash PreToolUse hook，调用 careful 的 `check-careful.sh`。
2. 注册 Edit/Write PreToolUse hook，调用 freeze 的 `check-freeze.sh`。
3. 询问编辑边界目录，解析绝对路径，写入 freeze state。
4. 告知两层保护：destructive command warnings + edit boundary。

### 收集的证据

组合收集：即将执行的 Bash command、Edit/Write file_path、freeze dir、hook fire pattern。

### 编辑行为

不改业务代码，只写 freeze state。后续业务编辑必须在 boundary 内；destructive Bash 只警告不阻断。

### 安全约束

`guard` 依赖 sibling `/careful` 和 `/freeze` 脚本同时存在。destructive Bash 是 ask，可 override；Edit/Write 越界是 deny，不可直接 override，除非 unfreeze 或改 boundary。Bash 写文件仍可能绕过 freeze，所以高风险 Bash 命令仍需人工判断。

### 预期输出

```text
Guard mode active.
1. Destructive command warnings ...
2. Edit boundary ...
```

### 与正常开发组合

适合生产排障、共享 repo、多个 agent 并行时使用。先 `$gstack-guard` 锁到任务目录，再做 investigate/fix。完成单模块任务后 `$gstack-unfreeze`，必要时保留 careful 效果到会话结束。

## `$gstack-unfreeze`

### 何时使用

用于 “unfreeze edits”、“unlock all directories”、“remove freeze”，需要扩大编辑范围但不想结束会话时使用。

示例：

```text
$gstack-unfreeze
```

### 工作流/阶段

1. 解析 gstack paths，找到 `$GSTACK_STATE_ROOT/freeze-dir.txt`。
2. 如果存在，读取旧 boundary，删除 state file。
3. 如果不存在，报告没有设置 freeze boundary。

### 收集的证据

只读取 freeze state file 里的旧路径。

### 编辑行为

删除 freeze state file，不改业务代码。

### 安全约束

它只解除 freeze 边界。已注册的 freeze hook 仍在会话中，但因为没有 state file，会允许所有 Edit/Write。它不会关闭 `$gstack-careful` 的 destructive Bash warnings；若之前用的是 `$gstack-guard`，unfreeze 后 Bash destructive warnings 仍可能继续到会话结束。

### 预期输出

```text
Freeze boundary cleared (was: <path>). Edits are now allowed everywhere.
```

或：

```text
No freeze boundary was set.
```

### 与正常开发组合

在 `$gstack-investigate` 或 `$gstack-guard` 后需要跨目录收尾、运行更大范围编辑、或切换任务时使用。建议在解除后先说明新的编辑范围，避免多人/多 agent 场景里误改他人负责区域。

## destructive guardrails 的实际边界

`$gstack-careful` 和 `$gstack-guard` 对 destructive Bash 的处理是 `ask`，不是 `deny`。这保留了必要的生产操作能力，但依赖用户确认。`$gstack-freeze` 和 `$gstack-guard` 对 Edit/Write 越界是 `deny`，但 Bash 不受 freeze 约束。因此最安全的实践是：

1. 用 `$gstack-guard` 锁目录。
2. 避免通过 Bash 写文件；使用 Edit/Write 让 boundary 生效。
3. 对 destructive Bash warning，只有在确认目标、备份/回滚路径、工作树状态后才允许。
4. 涉及 `git reset --hard`、`git checkout .`、`git restore .` 时，先检查 `git status`，因为这些会丢失用户或其他 agent 的未提交修改。
5. 涉及 force-push、DB destructive SQL、K8s delete、Docker prune 时，优先停下来让用户明确批准。

## 推荐组合流程

常规 feature：

```text
实现代码和测试
$gstack-health
$gstack-review
修复 review findings
$gstack-review
```

bug / incident：

```text
$gstack-guard  # 锁到相关模块，危险 Bash 有警告
$gstack-investigate
运行项目测试
$gstack-health
$gstack-review
$gstack-unfreeze
```

安全检查：

```text
$gstack-cso --diff
修复具体漏洞时转 $gstack-investigate 或普通开发
$gstack-review --security
$gstack-cso --diff
```

需要第二意见：

```text
$gstack-review
$gstack-codex challenge
# Codex 指向可复现 bug -> $gstack-investigate
# Codex 指向 diff 风险 -> 修代码后重跑 $gstack-review
```

多人/多 agent 并行：

```text
$gstack-freeze  # 或 $gstack-guard
# 只编辑自己负责目录
$gstack-unfreeze  # 任务结束或切换范围
```
