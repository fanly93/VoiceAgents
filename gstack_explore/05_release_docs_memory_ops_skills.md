# gstack 发布、文档、记忆与运维类技能分析

本文分析本地 gstack checkout 中以下技能：`ship`、`land-and-deploy`、`canary`、`setup-deploy`、`landing-report`、`document-release`、`document-generate`、`context-save`、`context-restore`、`learn`、`retro`、`gstack-upgrade`、`setup-gbrain`、`sync-gbrain`、`benchmark-models`、`make-pdf`。

范围限定为各技能的 `SKILL.md` 以及直接相关的脚本/文档，例如 `bin/gstack-next-version`、`bin/gstack-pr-title-rewrite.sh`、`bin/gstack-gbrain-sync.ts`、`bin/gstack-memory-ingest.ts`、`bin/gstack-brain-context-load.ts`、`docs/gbrain-sync.md`、`setup-gbrain/memory.md` 和项目本地使用说明。

## 本仓库使用前提

本仓库的 gstack 是项目级安装，位于 `.agents/skills/gstack`。不要调用根 `$gstack`；在 Codex 中应优先使用生成后的 `$gstack-*` 技能入口。本仓库必须保持为 git repo，因为生成技能依赖 `git rev-parse --show-toplevel` 定位项目级 runtime。

手动运行 gstack 命令时，应使用项目级环境，避免读写用户级目录：

```bash
cd /Users/tanglin/VibeCoding/VoiceAgents
env HOME="$PWD/.gstack-home" \
  GSTACK_HOME="$PWD/.gstack" \
  GSTACK_STATE_DIR="$PWD/.gstack" \
  PATH="$PWD/.bun/bin:$PATH" \
  <gstack-command>
```

本地状态目录建议理解为三层：

- 项目工作树内：代码、`CLAUDE.md`、`VERSION`、`CHANGELOG.md`、`.gstack/deploy-reports`、`.gstack/canary-reports`、`.context/retros`。
- gstack 项目状态：`${GSTACK_STATE_ROOT:-~/.gstack}/projects/$SLUG/...`，用于 checkpoints、learnings、review/ship/deploy 记录。
- 用户/机器级状态：`~/.gbrain`、`~/.claude.json`、`~/.gstack/.gbrain-sync-state.json`、`~/.gstack/analytics`、`~/.gstack/retros` 等。

在本仓库中使用时，把 `~/.gstack` 理解成项目级 `GSTACK_HOME=$PWD/.gstack`，除非技能文案明确讨论全局机器状态。

## 共同机制

这些生成技能大多包含相同 preamble：

- 检查 gstack 更新，必要时转入 `/gstack-upgrade` inline flow。
- 创建 `~/.gstack/sessions/$PPID`，记录活跃 session。
- 读取 `gstack-config`：telemetry、proactive、question_tuning、checkpoint_mode、artifacts_sync_mode 等。
- 通过 `gstack-slug` 定位项目 slug，并加载 `${GSTACK_HOME}/projects/$SLUG/learnings.jsonl`。
- 写入 `~/.gstack/analytics/skill-usage.jsonl` 和 `gstack-timeline-log`。
- 如果启用了 artifacts sync，调用 `gstack-brain-sync --discover-new` 和 `--once`。
- 如果配置了 gbrain，会通过 `gstack-brain-context-load` 注入可检索上下文；它有 500ms 级别的超时保护，失败时继续执行。

共同风险：

- 很多技能的文案仍以 `~/.claude/skills/gstack` 为默认路径。本仓库手动执行时要改用 `.agents/skills/gstack` 或项目级 env。
- 多个技能会修改 `CLAUDE.md`。本任务只分析，不运行这些技能；未来实际使用时要留意 `CLAUDE.md` 是否已有用户手写内容。
- 多数交互依赖 `AskUserQuestion`。Codex 当前工具环境不一定有对应 callable variant，完整交互可能需要宿主 UI 支持。

## 推荐发布顺序

特性开发完成后，本仓库较稳妥的顺序是：

1. `$gstack-review` 或 `$gstack-qa`：先做代码/体验验证。
2. `$gstack-landing-report`：查看版本队列，避免多 workspace 抢同一 `VERSION`。
3. `$gstack-ship`：跑测试、review、版本、CHANGELOG、PR 创建。
4. `$gstack-document-release`：通常由 `/ship` 的 Step 18 子代理自动触发；失败时手动补跑。
5. `$gstack-land-and-deploy`：PR 绿灯后合并、等待部署、生产验证。
6. `$gstack-canary <url>`：需要更长时间生产观察时使用。
7. `$gstack-retro` 或 `$gstack-learn`：事后沉淀工程节奏和项目学习。
8. `$gstack-context-save`：上下文切换前保存进度；新会话用 `$gstack-context-restore` 接续。

## ship

**用途**：完整 shipping workflow。它将一个 feature branch 从“代码已经改完”推进到“已验证、已版本化、已推送、已创建 PR/MR”。它是发布链的中心技能。

**前置条件**

- 当前分支不是 base branch。
- git remote 能定位 GitHub/GitLab，最好已登录 `gh` 或 `glab`。
- 项目有可运行测试；没有测试框架时技能会尝试 bootstrap。
- 需要 `VERSION` 使用四段版本号 `X.Y.Z.W`，`CHANGELOG.md` 可写。
- 推荐先完成计划、review、QA，但 `/ship` 自身会补做很多检查。

**何时使用**

- 功能实现完成，需要创建 PR。
- 需要自动生成版本、CHANGELOG、TODO 完成记录和 PR body。
- 多个 Conductor/worktree 并行开发时，需要 workspace-aware version 分配。

**工作流**

1. 检测平台和 base branch。
2. pre-flight：确认分支、状态、review readiness。
3. 合并 base branch 后跑测试。
4. 必要时 bootstrap test framework、生成首批真实测试、更新 `TESTING.md`/`CLAUDE.md`。
5. 运行测试、处理失败归因：分支引入 vs 既有失败。
6. 条件运行 eval suites。
7. 做 test coverage audit，并根据风险生成覆盖测试。
8. 做 plan completion audit 和可选 `/qa-only` 计划验证。
9. 加载 prior learnings，做 scope drift detection。
10. 做 pre-landing review、设计 review、review army、adversarial review。
11. 处理已有 PR 上的 Greptile 评论。
12. 捕获新的 learnings。
13. 用 `bin/gstack-next-version` 做版本 bump，处理 queue collision 和 already-bumped drift。
14. 生成或统一 `CHANGELOG.md` entry。
15. 保守更新 `TODOS.md`。
16. 拆分 bisectable commits；continuous checkpoint 模式下会 squash WIP commits。
17. verification gate 后 `git push`。
18. 派发 `/document-release` 子代理，在 PR 创建前同步文档。
19. 创建或更新 PR/MR，标题强制 `v<NEW_VERSION> ...`。
20. 持久化 ship metrics。

**生成产物**

- 代码 commit、版本/CHANGELOG/TODOS commit。
- 更新 `VERSION`、`CHANGELOG.md`，可能更新 `package.json`。
- 可能生成 `TESTING.md`、测试文件、测试计划。
- PR/MR，包含 Summary、Test Coverage、Review、Scope Drift、Plan Completion、Verification、TODOS、Documentation 等 section。
- `${GSTACK_HOME}/projects/$SLUG/$BRANCH-reviews.jsonl` 中的 ship metrics。
- 可能写入 learnings、analytics、timeline。

**Git/GitHub/部署假设**

- 支持 GitHub 和 GitLab；优先 `gh`/`glab`，否则退回 git-native 部分能力。
- 禁止 force push，只使用普通 `git push`。
- PR/MR 标题必须以版本开头；`bin/gstack-pr-title-rewrite.sh` 是单一规则来源。
- `bin/gstack-next-version` 读取 open PR claimed versions 和 sibling worktrees，选择下一个可用版本槽位。

**状态存储**

- 版本状态在 repo 内：`VERSION`、`CHANGELOG.md`。
- review/ship 指标在 `${GSTACK_HOME}/projects/$SLUG/*-reviews.jsonl`。
- learnings 在 `${GSTACK_HOME}/projects/$SLUG/learnings.jsonl`。
- analytics/timeline 在 `~/.gstack/analytics` 和 timeline log。

**风险点**

- 范围极大，会运行测试、改文档、改版本、提交、推送、创建 PR。
- 自动 test bootstrap 会引入新测试基础设施，适合首次建立测试，但会扩大 diff。
- `CHANGELOG.md` 由 `/ship` 生成，后续 `/document-release` 只允许 polish，不能 clobber。
- 多 workspace 下版本漂移需要严肃处理；若 `/land-and-deploy` 发现 drift，应回到 `/ship` 重跑。
- Codex 环境没有完整 `AskUserQuestion` 时，涉及 minor/major bump、review findings 等 gate 可能无法完整交互。

**示例调用**

```text
$gstack-ship
```

本仓库实用建议：先跑 `$gstack-landing-report`，再跑 `$gstack-ship`。如果只是在探索 gstack checkout，不要运行它；它会修改大量发布文件。

## land-and-deploy

**用途**：接续 `/ship` 创建的 PR，执行合并、等待部署、生产验证和必要时回滚。

**前置条件**

- 当前分支有 open PR，通常由 `/ship` 创建。
- `gh auth status` 成功；该技能主要按 GitHub CLI 设计。
- CI 已配置，或至少 PR checks 可查询。
- 最好已通过 `/setup-deploy` 在 `CLAUDE.md` 写入 Deploy Configuration。
- 如需视觉/浏览器验证，需要 `$B` browse daemon 可用。

**何时使用**

- PR 通过 review 和 CI，准备落地生产。
- 需要 merge queue、deploy workflow、staging、canary 这些步骤有人盯着。
- 需要在 merge 前最后确认 review/test/docs/PR body 是否仍可信。

**工作流**

1. Pre-flight：找 PR、确认状态、检查 `gh` auth。
2. 首次运行 dry-run：检测 deploy config、平台、workflow、staging、命令可用性；用户确认后写入 `${GSTACK_HOME}/projects/$SLUG/land-deploy-confirmed` 指纹。
3. CI 和 merge conflict 检查，必要时等待 CI。
4. VERSION drift detection：调用 `gstack-next-version`，如果 PR 版本落后于 next slot，停止并要求重跑 `/ship`。
5. Pre-merge readiness gate：review staleness、可选 quick review、测试、E2E/LLM eval、PR body、document-release/CHANGELOG/VERSION。
6. Merge：优先 `gh pr merge --auto --delete-branch`，否则 `--squash`；失败后必须查询 PR authoritative state，不能盲目重试 merge。
7. 检测 merge queue、部署 workflow、部署策略。
8. 可选 staging-first。
9. 等待部署：GitHub Actions、Fly/Render/Heroku CLI、Vercel/Netlify 自动部署、custom hook。
10. 根据 diff scope 做 canary 验证。
11. 失败时可 `git revert <merge-sha>` 并推送/创建 revert PR。
12. 写 deploy report 和 review dashboard JSONL。

**生成产物**

- 合并 PR，删除分支。
- `.gstack/deploy-reports/{date}-pr{number}-deploy.md`。
- `.gstack/deploy-reports/post-deploy.png`。
- `${GSTACK_HOME}/projects/$SLUG/land-deploy-confirmed`。
- `${GSTACK_HOME}/projects/$SLUG` 下的 land-and-deploy JSONL 记录。
- 必要时创建 revert commit 或 revert PR。

**Git/GitHub/部署假设**

- 核心路径假设 GitHub + `gh`。
- 支持 GitHub merge queue，poll PR state。
- 部署平台通过 `CLAUDE.md`、`fly.toml`、`render.yaml`、`vercel.json`、`netlify.toml`、`Procfile`、workflow 名称推断。
- docs-only change 会跳过部署验证。

**状态存储**

- 部署确认指纹在 `${GSTACK_HOME}/projects/$SLUG/land-deploy-confirmed`。
- deploy report 在 repo 的 `.gstack/deploy-reports`。
- 生产验证截图也在 `.gstack/deploy-reports`。

**风险点**

- 合并是不可逆操作；技能的 Step 3.5 是关键人工 gate。
- 若 deploy config 错误，会合并后无法验证生产。
- `gh pr merge` 非零退出后不能重试；必须查询 PR state。
- revert 会修改 base branch，需要权限且可能冲突。
- 浏览器 `$B` 在 Codex 沙箱中可能需要非沙箱/localhost 权限。

**示例调用**

```text
$gstack-land-and-deploy
$gstack-land-and-deploy #123
$gstack-land-and-deploy #123 https://example.com
```

本仓库实用建议：第一次使用前先 `$gstack-setup-deploy`。如果当前项目不是 Web app，可在 dry-run 中明确“无部署需要”，避免后续重复询问。

## canary

**用途**：生产部署后的短期可靠性监控。用 browse daemon 反复打开页面、截图、检查 console errors 和性能，与 baseline 比较。

**前置条件**

- 可访问生产 URL。
- `$B` browse daemon 可用。
- 推荐部署前先用 `--baseline` 捕获基线。
- `.gstack/canary-reports` 可写。

**何时使用**

- `/land-and-deploy` 后需要 5-30 分钟持续观察。
- 部署前想记录 baseline。
- 想快速做单次生产 health check。

**工作流**

1. 创建 `.gstack/canary-reports/baselines` 和 `screenshots`。
2. `--baseline` 模式：对页面截图、console、perf、text，写 `baseline.json` 后停止。
3. 未指定页面时自动发现内部导航，用户选择监控页面。
4. 无 baseline 时先做 pre-deploy snapshot。
5. 按 60 秒循环监控指定 duration。
6. 对比 baseline：page load failure、新 console errors、2x load time、404。
7. 高危/关键问题连续出现 2 次以上才 alert。
8. 生成 markdown/json report。
9. 健康时询问是否更新 baseline。

**生成产物**

- `.gstack/canary-reports/baseline.json`。
- `.gstack/canary-reports/baselines/*.png`。
- `.gstack/canary-reports/screenshots/*.png`。
- `.gstack/canary-reports/{date}-canary.md` 和 `.json`。
- `${GSTACK_HOME}/projects/$SLUG` 下 canary JSONL 记录。

**Git/GitHub/部署假设**

- 不合并、不部署、不改代码；只观察。
- 会用 git branch/slug 做记录，但不依赖 PR。

**状态存储**

- baseline/report/screenshot 在 repo 内 `.gstack/canary-reports`。
- summary 也会写入 gstack project state。

**风险点**

- 无 baseline 时只是 health check，回归判断弱。
- 新 console error 基于差异判断；baseline 本身有错误时不会报旧错。
- browse daemon 访问生产 URL 可能受 VPN、auth、CORS、CDN 或网络限制影响。
- 监控循环较长，交互期间不要误以为卡住。

**示例调用**

```text
$gstack-canary https://example.com --baseline
$gstack-canary https://example.com
$gstack-canary https://example.com --duration 5m --pages /,/dashboard
$gstack-canary https://example.com --quick
```

本仓库实用建议：如果 VoiceAgents 暂无线上 URL，先不要跑 canary；可在部署配置明确项目类型，避免 land-and-deploy 误判。

## setup-deploy

**用途**：配置 `/land-and-deploy` 所需部署信息，写入 `CLAUDE.md` 的 `## Deploy Configuration`。

**前置条件**

- 在项目根目录运行。
- 可读取平台配置文件或用户能提供部署方式、生产 URL、健康检查方式。
- `CLAUDE.md` 可写，或允许创建。

**何时使用**

- 第一次使用 `/land-and-deploy` 前。
- 部署平台、URL、health check、workflow 发生变化。
- `/land-and-deploy` dry-run 发现配置不可信。

**工作流**

1. 检查已有 `## Deploy Configuration`，可选择重配、编辑字段、确认无误。
2. 自动检测平台：Fly、Render、Vercel、Netlify、Heroku、Railway、GitHub Actions deploy workflow、CLI/library 项目类型。
3. 平台特定引导：
   - Fly：读取 `fly.toml` app，检查 `fly status`，推断 `https://{app}.fly.dev`。
   - Render：读取 `render.yaml`，确认 service URL，说明 merge 后 auto-deploy。
   - Vercel/Netlify：检测配置和 CLI/production URL。
   - GitHub Actions only：读取 workflow 并询问 production URL。
   - Custom：询问部署触发、生产 URL、health check、pre/post hooks。
4. 写入或替换 `CLAUDE.md` 中部署配置。
5. 尝试 curl health check 或运行 deploy status command。
6. 输出配置摘要。

**生成产物**

- `CLAUDE.md` 中的：
  - Platform
  - Production URL
  - Deploy workflow
  - Deploy status command
  - Merge method
  - Project type
  - Post-deploy health check
  - Custom deploy hooks

**Git/GitHub/部署假设**

- 部署平台可通过常见配置文件或 GitHub Actions workflow 推断。
- Render/Vercel/Netlify 常见路径是 merge 到 main 后自动部署。
- GitHub Actions workflow 只被读取，不会自动创建。

**状态存储**

- 长期配置在 `CLAUDE.md`。
- preamble analytics/timeline 同其他技能。

**风险点**

- 写 `CLAUDE.md` 可能与项目手写说明冲突；应保留现有内容，只替换标记 section。
- 健康检查失败不阻塞配置，但会导致后续 deploy 验证不可靠。
- 有些生产 URL 只能用户确认，不能完全靠推断。

**示例调用**

```text
$gstack-setup-deploy
```

本仓库实用建议：若项目暂时没有生产部署，仍可记录 `Project type: CLI / library / no deploy`，让 `/land-and-deploy` 后续跳过无意义验证。

## landing-report

**用途**：只读版本队列仪表盘。显示 open PR claimed versions、sibling worktrees、当前 `/ship` 各 bump level 会占用的版本号。

**前置条件**

- git repo，有 `VERSION` 最佳。
- 有 origin/base branch 更好。
- `gh`/`glab` 在线时可检测 open PR；离线时会降级。
- `bun` 可运行 `bin/gstack-next-version`。

**何时使用**

- 多个 workspace/agent 并行开发，准备 `/ship` 前。
- 想知道下一个 version slot。
- 怀疑 open PR 之间版本冲突。

**工作流**

1. 检测 base branch。
2. 读取本地 `VERSION` 和 `origin/$BASE:VERSION`。
3. 对 `micro`、`patch`、`minor`、`major` 分别调用 `bin/gstack-next-version`。
4. 渲染 dashboard：
   - Repo、Base、Host、Status
   - Open PRs claiming versions
   - sibling Conductor worktrees
   - 各 bump level next version
5. 根据 collision、active sibling、clean queue 给一个建议。

**生成产物**

- 正常情况下无持久化产物。
- 运行时可能写 `/tmp/landing-*.json`。
- preamble 仍可能写 analytics/timeline。

**Git/GitHub/部署假设**

- `bin/gstack-next-version` 是纯读工具，不写状态。
- 通过 GitHub/GitLab 查询 open PR 的 `VERSION`。
- sibling worktree 根据 workspace root、branch、VERSION、last commit 判断是否 active。

**状态存储**

- 无业务状态写入。

**风险点**

- 离线或 auth 不可用时无法做 queue-awareness，只能本地 fallback。
- open PR 的版本如果不是同 repo branch 或 fork，脚本会尽量过滤，但仍依赖 host API。
- 版本报告不是 lock；真正防撞仍发生在 `/ship` 和 `/land-and-deploy` drift gate。

**示例调用**

```text
$gstack-landing-report
```

本仓库实用建议：其他 agent 也在写 `gstack_explore/` 时，landing-report 对发布队列不直接相关；真正 feature PR 前再用。

## document-release

**用途**：post-ship 文档同步。通常在 `/ship` Step 18 由子代理执行，也可手动运行。

**前置条件**

- 在 feature branch 上运行，不能在 base branch。
- 能确定 base branch。
- 可读写 docs、`README.md`、`ARCHITECTURE.md`、`CONTRIBUTING.md`、`CLAUDE.md`、`CHANGELOG.md`、`TODOS.md`、`VERSION` 等。
- 有 `gh`/`glab` 时可更新 PR/MR body/title。

**何时使用**

- `/ship` 后 PR merge 前，确保文档与 diff 同步。
- `/ship` 的 document-release 子代理失败或返回 invalid JSON。
- coverage map 发现文档债。

**工作流**

1. diff 分析：stat、commits、changed files、docs discovery。
2. coverage map：以 Diataxis 视角审计 public surface 的 reference/how-to/tutorial/explanation 覆盖。
3. per-file audit：README、ARCHITECTURE、CONTRIBUTING、CLAUDE、其他 `.md`。
4. 自动应用清晰事实更新。
5. 对 risky/subjective docs change 询问用户。
6. CHANGELOG voice polish：只改措辞，不重写、不删除、不重排。
7. cross-doc consistency 和 discoverability。
8. TODOS cleanup：保守标记 completed，发现新增 deferred work。
9. VERSION bump question：永远不能静默 bump。
10. commit docs，push。
11. 更新 PR/MR `## Documentation` section 和 title version prefix。
12. 输出 documentation health 和 coverage summary。

**生成产物**

- docs 更新 commit，message 类似 `docs: update project documentation for vX.Y.Z.W`。
- 可能修改 README、ARCHITECTURE、CONTRIBUTING、CLAUDE、CHANGELOG、TODOS、VERSION。
- PR/MR body 中 `## Documentation` section。
- PR/MR title 与 `VERSION` 同步。

**Git/GitHub/部署假设**

- GitHub/GitLab 检测与 PR body 更新。
- 用 PID-specific `/tmp/gstack-pr-body-$$.md` 做 body 更新，降低 race 风险。
- stage 文件必须按名称，禁止 `git add -A`。

**状态存储**

- 文档改动在 git commit。
- PR body/title 在 host。
- preamble analytics/timeline。

**风险点**

- 最大风险是 clobber `CHANGELOG.md`；技能明确禁止 Write 覆盖，只允许 Edit 精确替换。
- coverage map 只提示债务，不自动生成完整文档；需要 `/document-generate` 补齐。
- VERSION bump 必须问用户；当前 Codex 环境若无 AUQ 会被阻塞。
- 修改 `CLAUDE.md` 时要保留本仓库关于项目级 gstack 的中文说明。

**示例调用**

```text
$gstack-document-release
```

本仓库实用建议：如果只是改 `gstack_explore/*.md` 报告，不需要跑 document-release；这类探索报告通常不应触发版本/CHANGELOG。

## document-generate

**用途**：从零生成缺失文档，按 Diataxis 拆分 reference、how-to、tutorial、explanation。

**前置条件**

- 用户指定 feature/module/project scope，或 `/document-release` 提供 coverage gaps。
- 能读代码、测试、已有 docs。
- 能写 `docs/` 或现有文档文件。

**何时使用**

- public surface 有零文档或 reference-only 文档债。
- 新模块需要完整读者路径。
- 想为某个内部架构补 explanation。

**工作流**

1. Scope & intent：确认文档目标和输出位置，默认建议 inline + standalone。
2. Codebase archaeology：读 README/ARCHITECTURE/CONTRIBUTING/AGENTS/CLAUDE、package/config、入口文件、实现、测试、相关依赖。
3. 产出 concept map。
4. Diataxis partitioning：决定每个 entity 要哪些 quadrant。
5. 先写 reference，再写 explanation、how-to、tutorial。
6. cross-document linking 与 entry-point discoverability。
7. quality self-review：accuracy、completeness、voice。
8. 按文件名 stage，commit，push。
9. 若 PR 存在，更新 `## Documentation Generated` section。

**生成产物**

- `docs/*.md` 或现有 docs 更新。
- README/CLAUDE/AGENTS/docs index/sidebar 的链接更新。
- commit：`docs: generate [scope] documentation (Diataxis)`。
- PR body `## Documentation Generated` 表格。

**Git/GitHub/部署假设**

- 需要 git branch 和 push。
- PR body 更新依赖 `gh`/`glab` 可用。
- 不直接处理 deploy。

**状态存储**

- 文档进入 repo。
- preamble analytics/timeline。

**风险点**

- 研究不足会生成“半懂”文档；Step 1 明确要求读代码和测试。
- code examples 必须可运行，不能猜。
- 超过 5 个文档建议先问用户确认，避免一次性生成过多维护负担。

**示例调用**

```text
$gstack-document-generate "document the voice agent runtime"
$gstack-document-generate "fill documentation gaps from document-release"
```

本仓库实用建议：如果未来把 `gstack_explore/` 整理成正式 docs，可用它生成 `docs/gstack-skills/*.md`，但要先明确这些报告是内部探索文档还是用户文档。

## context-save

**用途**：保存当前工作上下文，供未来 `/context-restore` 接续。只读代码状态，只写 checkpoint。

**前置条件**

- 当前目录可解析 project slug。
- git 可用最佳，但即使状态为空也可写 summary。
- `${GSTACK_STATE_ROOT}/projects/$SLUG/checkpoints` 可写。

**何时使用**

- 中断前、切换 agent 前、长任务上下文快耗尽前。
- 多 workspace handoff。
- 想留下一份结构化“我做到哪里”的记录。

**工作流**

1. 解析命令：save 或 list。
2. Save：
   - gather branch、git status、diff stat、staged diff stat、recent log。
   - 根据 conversation 和 git state 总结目标、决策、剩余工作、notes。
   - 计算 session duration。
   - bash 侧 sanitize title，生成 append-only 文件名。
   - 写 markdown checkpoint。
3. List：
   - 默认列当前 branch contexts。
   - `--all` 列所有 branch contexts。

**生成产物**

- `${GSTACK_STATE_ROOT}/projects/$SLUG/checkpoints/YYYYMMDD-HHMMSS-title.md`。
- frontmatter：status、branch、timestamp、session_duration_s、files_modified。

**Git/GitHub/部署假设**

- 不提交、不 push、不改代码。
- 读取 git 状态用于上下文。

**状态存储**

- checkpoint 保存在 `checkpoints/`，不是 `contexts/`。
- 文件 append-only，不覆盖。

**风险点**

- summary 依赖当前对话；如果对话已压缩或不完整，可能遗漏隐性决策。
- 用户标题在 bash 侧 sanitize，不能在 LLM 层重建路径。
- list 默认 current branch，restore 默认 all branches，二者有意不同。

**示例调用**

```text
$gstack-context-save
$gstack-context-save "release skills report"
$gstack-context-save list
$gstack-context-save list --all
```

本仓库实用建议：多 agent 同时写 `gstack_explore/` 时，完成阶段性探索后可保存上下文，但不要把 checkpoint 文件写进 `gstack_explore/`。

## context-restore

**用途**：恢复 `/context-save` 保存的工作上下文，只读 checkpoint，不改代码。

**前置条件**

- 已有 checkpoint 文件。
- 能通过 `gstack-slug` 和 `gstack-paths` 定位 `${GSTACK_STATE_ROOT}/projects/$SLUG/checkpoints`。

**何时使用**

- 新会话中“接着上次做”。
- 从另一个 branch/workspace 读取最近 handoff。
- 想查看某个 title/编号对应的 saved context。

**工作流**

1. 查找最近 20 个 checkpoint，按文件名时间戳 `sort -r`。
2. 默认加载全分支最新 checkpoint。
3. 用户提供 title fragment 或 number 时匹配具体文件。
4. 展示 title、branch、timestamp、duration、status、summary、remaining work、notes。
5. 当前 branch 与 saved branch 不同时提示用户。
6. 询问是否继续剩余工作、展示完整文件或结束。

**生成产物**

- 无业务产物；只输出恢复摘要。

**Git/GitHub/部署假设**

- 不依赖 PR。
- 会读取当前 branch 做提示。

**状态存储**

- 读取 `checkpoints/*.md`。

**风险点**

- 默认跨分支恢复，可能提示你继续另一个 branch 的工作；这是设计目的，不是 bug。
- “most recent” 以文件名前缀为准，不以 filesystem mtime 为准。
- Codex 无 AUQ 时 Step 3 的后续选择可能只能由对话手动完成。

**示例调用**

```text
$gstack-context-restore
$gstack-context-restore "release skills"
```

本仓库实用建议：如果恢复到别人/其他 agent 的 checkpoint，先核对目标文件路径，避免误写非 assigned file。

## learn

**用途**：管理项目 learnings。显示、搜索、修剪、导出、统计或手动添加学习条目。

**前置条件**

- `${GSTACK_STATE_ROOT}/projects/$SLUG/learnings.jsonl` 可能存在。
- `gstack-learnings-search` 和 `gstack-learnings-log` 可用。

**何时使用**

- 想看 gstack 过去对项目学到了什么。
- review/ship/investigate 后沉淀可复用模式。
- 怀疑 learnings 过期、矛盾、指向已删除文件。
- 想导出到 `CLAUDE.md` 或单独文档。

**工作流**

- 默认：显示最近 20 条，按 type 分组。
- `search <query>`：按 query 搜索。
- `prune`：
  - 检查 referenced files 是否还存在。
  - 检查相同 key 的矛盾 insight。
  - 逐条询问 remove/keep/update。
- `export`：输出 markdown section，按 Patterns/Pitfalls/Preferences/Architecture。
- `stats`：统计 total、dedup 后 unique、by type、by source、avg confidence。
- `add`：交互收集 type、key、insight、confidence、files 后 append。

**生成产物**

- `learnings.jsonl` 追加或 prune 后重写。
- 可选导出 markdown。
- 可选写入 `CLAUDE.md` 或独立文件。

**Git/GitHub/部署假设**

- 不涉及 PR/deploy。
- `files` 字段用 repo 相对路径辅助 staleness 检测。

**状态存储**

- `${GSTACK_STATE_ROOT}/projects/$SLUG/learnings.jsonl`。
- 同时有 analytics/timeline preamble 写入。

**风险点**

- prune 会删除或改写 learnings 文件，需用户确认。
- update 采用 append 新条目，“latest wins”，旧条目不一定消失。
- cross-project learnings 可能带来语境污染，retro 中会单独询问是否启用。

**示例调用**

```text
$gstack-learn
$gstack-learn search "deploy"
$gstack-learn stats
$gstack-learn export
$gstack-learn add
```

本仓库实用建议：可以记录“项目级 gstack 必须用 `.agents/skills/gstack` + 项目级 env”的 operational learning，但要避免把一次性探索结论误当长期架构事实。

## retro

**用途**：工程复盘。按时间窗口统计 git、测试、PR、session、热点、learnings、skill usage；支持 repo-scoped、compare、global。

**前置条件**

- repo 模式需要 origin/default branch；无 remote 时可降级但会披露。
- 全局模式需要 `gstack-global-discover`。
- 需要本地 git history、analytics、learnings、可选 TODO/Greptile history。

**何时使用**

- 每周复盘 shipping velocity、test health、热点和习惯。
- 比较两个时间窗口。
- 跨项目看 AI coding sessions 和 context switching。

**工作流**

Repo-scoped：

1. 解析 window，day/week 用 local midnight 对齐。
2. stale-base guard：确保 `origin/<default>` 在窗口内有新提交，避免日期错导致虚构叙述。
3. 并行采集 git log、numstat、timestamp、hotspots、PR numbers、authors、TODO、test count、analytics。
4. 计算 metrics：features shipped、commits、weighted commits、logical SLOC、test ratio、version range、sessions、Greptile signal、backlog health、skill usage。
5. 分析 hour distribution、45 分钟 gap sessions、commit type、hotspots、PR size、focus score、ship of the week、team members。
6. 捕获 genuine learnings。
7. 14d+ 时做 week-over-week。
8. 计算 team/personal streak。
9. 加载 `.context/retros/*.json` 做趋势对比。
10. 保存 `.context/retros/YYYY-MM-DD-N.json`。
11. 输出 narrative。

Global：

1. 调用 `gstack-global-discover --since <window> --format json`。
2. 对每个 repo 跑 git log。
3. 计算 global streak、context switching、per-tool patterns。
4. 输出 shareable personal card 和 deep-dive。
5. 保存 `~/.gstack/retros/global-YYYY-MM-DD-N.json`。

**生成产物**

- Repo scoped：`.context/retros/YYYY-MM-DD-N.json`。
- Global：`~/.gstack/retros/global-YYYY-MM-DD-N.json`。
- 主要 narrative 直接输出到对话，不写 markdown 文件。

**Git/GitHub/部署假设**

- 用 `origin/<default>`，不是本地 main。
- merge commits 视为 PR boundaries。
- commit author 用 `git config user.name` 区分“你”和 teammate。

**状态存储**

- `.context/retros`。
- `~/.gstack/retros`。
- 可读 `~/.gstack/analytics/skill-usage.jsonl`、`eureka.jsonl`、`${GSTACK_HOME}/projects/$SLUG/*-reviews.jsonl`。

**风险点**

- 日期锚点错误会严重误导；技能专门有 stale guard。
- 无 commits 时应明确说零数据，不要编故事。
- 不读取 `CLAUDE.md`，复盘自包含。
- narrative 输出很长，保存的只有 JSON snapshot。

**示例调用**

```text
$gstack-retro
$gstack-retro 14d
$gstack-retro compare 14d
$gstack-retro global 7d
```

本仓库实用建议：探索报告完成后，可用 retro 看本轮协作是否产生很多 docs-only commits；但本任务不需要运行。

## gstack-upgrade

**用途**：升级 gstack 本身，支持 inline upgrade 和 standalone usage。

**前置条件**

- 能找到 install dir：`$HOME/.claude/skills/gstack`、`$HOME/.gstack/repos/gstack`、`.claude/skills/gstack`、`.agents/skills/gstack` 等。
- git install 需要 `git fetch`、`git reset --hard origin/main`、`./setup`。
- vendored install 需要网络 clone。
- 本仓库使用 `.agents/skills/gstack`，应特别小心不要破坏项目级 runtime。

**何时使用**

- preamble 显示 `UPGRADE_AVAILABLE <old> <new>`。
- 用户明确要求升级 gstack。
- local vendored copy stale，需要同步。

**工作流**

Inline：

1. 检查 `GSTACK_AUTO_UPGRADE=1` 或 `gstack-config auto_upgrade`。
2. 非 auto 时询问：现在升级、以后自动、暂不、永不提示。
3. 暂不时写 `~/.gstack/update-snoozed`，按 24h/48h/1week backoff。
4. 检测 install type。
5. 保存 old version。
6. git install：`git stash`、`git fetch origin`、`git reset --hard origin/main`、`./setup`。
7. vendored install：clone 到 tmp，备份旧目录，替换，`./setup`，清理。
8. 处理 local vendored copy 和 team mode。
9. 跑 `gstack-upgrade/migrations/v*.sh`。
10. 写 `~/.gstack/just-upgraded-from`，清 update cache。
11. 摘要 CHANGELOG 中 user-facing changes。

Standalone：

- 强制 update check。
- 如果无新版本，检查 local vendored copy 是否 stale，并按 team mode 删除/同步。

**生成产物**

- 更新 gstack install dir。
- 可能修改 `.gitignore`、删除或同步 `.claude/skills/gstack` vendored copy。
- `~/.gstack/just-upgraded-from`。
- `~/.gstack/update-snoozed` 或 config `auto_upgrade/update_check`。

**Git/GitHub/部署假设**

- 官方 upstream 是 `origin/main` 或 `https://github.com/garrytan/gstack.git`。
- 本仓库 `.agents/skills/gstack/.git` 会被识别为 local-git。

**状态存储**

- `~/.gstack/config.yaml` 相关设置。
- `~/.gstack/last-update-check`、`update-snoozed`、`just-upgraded-from`。
- migrations 可改 gstack state，例如 artifacts rename。

**风险点**

- 对 git install 会执行 `git reset --hard origin/main`，这是破坏性操作；本仓库若有本地修改绝不能随意运行。
- vendored path 使用 `rm -rf`、`mv`、`cp -Rf`。
- 本项目 AGENTS 指定使用项目级 gstack，不用用户级 gstack；升级前要明确目标目录。
- 当前任务禁止编辑 `.agents/skills/gstack`，所以不能运行升级。

**示例调用**

```text
$gstack-gstack-upgrade
```

本仓库实用建议：除非用户明确要求，不要升级 `.agents/skills/gstack`。若必须升级，先确认 `git status --short .agents/skills/gstack` 和其他 agent 是否正在读写。

## setup-gbrain

**用途**：把 gbrain 配好，让 coding agent 可用持久知识库、MCP、代码索引、artifacts sync 和 transcript/memory ingest。

**前置条件**

- 面向本地 Mac 和 Claude Code MCP；Codex/其他 host 可使用 CLI，但 MCP 注册需手动适配。
- 需要 `gstack-gbrain-detect`、可选 `gbrain` CLI、`claude` CLI。
- Supabase 路径需要 Supabase Session Pooler URL 或 PAT。
- PGLite 路径可本地初始化。
- Remote MCP 路径需要 HTTPS MCP URL 和 bearer token。

**何时使用**

- 第一次配置 gbrain。
- gbrain doctor 失败、engine broken、token rotation、MCP URL 变化。
- 想切换 PGLite/Supabase/remote MCP。
- 想设置 per-repo trust policy 或 artifacts/transcripts sync。

**工作流**

1. 检测当前状态：CLI、version、config、engine、doctor、MCP mode、artifacts sync、local status。
2. broken local engine remediation：Retry、Switch to PGLite、Switch brain mode、Quit。
3. 选择路径：
   - Path 1：已有 Supabase URL。
   - Path 2a：用 PAT 自动 provision Supabase project。
   - Path 2b：手动创建 Supabase。
   - Path 3：PGLite local。
   - Path 4：Remote gbrain MCP over HTTP + bearer。
   - Switch：PGLite/Supabase 迁移。
4. 安装 gbrain CLI（Path 4 可跳过）。
5. 初始化 brain，所有 secret 通过 env var，不放 argv。
6. doctor 或 remote MCP verify。
7. 注册 Claude Code MCP：
   - local stdio：`claude mcp add --scope user gbrain -- <gbrain-bin> serve`
   - remote HTTP：`claude mcp add --scope user --transport http gbrain <URL> --header "Authorization: Bearer <TOKEN>"`
8. 设置 per-remote policy：read-write/read-only/deny/skip。
9. artifacts sync：创建或连接 `gstack-artifacts-$USER` 私有 repo，写 `~/.gstack-artifacts-remote.txt`。
10. local 模式 wire federated source；remote 模式打印给 brain admin 的 `gbrain sources add` 命令。
11. transcript & memory ingest gate：probe 后小规模自动，大规模询问。
12. 写 `CLAUDE.md` 的 `## GBrain Configuration`，smoke test 通过后写 `## GBrain Search Guidance`。
13. smoke test 和 GREEN/YELLOW/RED verdict。

**生成产物**

- `~/.gbrain/config.json`，mode 0600，由 gbrain 写入。
- `~/.claude.json` 中 MCP registration；remote token 存在这里，不进 `CLAUDE.md`。
- `CLAUDE.md` 的 GBrain Configuration/Search Guidance blocks。
- `~/.gstack-artifacts-remote.txt`。
- `~/.gstack/.git` artifacts repo、allowlist、merge drivers。
- `~/.gstack/.transcript-ingest-state.json`、`.gbrain-sync-state.json`。
- 可能的 `~/.gstack/transcripts/run-.../` staged transcripts。

**Git/GitHub/部署假设**

- artifacts repo 可通过 `gh`/`glab` 创建私有 repo，或用户提供 URL。
- per-repo policy 以 normalized git remote 为 key。
- Path 4 remote brain 的 source registration 由 brain admin 执行，不自动代跑。

**状态存储**

- gbrain engine state：`~/.gbrain`。
- gstack artifacts/memory state：`~/.gstack`。
- per-project instructions：`CLAUDE.md`。
- Claude MCP credentials：`~/.claude.json`。

**风险点**

- Supabase PAT 权限很大，必须用后撤销。
- DB URL、bearer token 不能进入 logs、argv、telemetry、`CLAUDE.md`。
- Remote MCP `claude mcp add --header` 有短暂 argv 暴露窗口。
- transcript ingestion 处理完整对话和 tool I/O，敏感度高；secret scan 默认在 ingest 阶段可选，真正跨机器边界由 `gstack-brain-sync` 扫描。
- `.setup-gbrain.lock.d` 用于并发保护；不要并发跑多个 setup。

**示例调用**

```text
$gstack-setup-gbrain
$gstack-setup-gbrain --repo
$gstack-setup-gbrain --switch
$gstack-setup-gbrain --cleanup-orphans
```

本仓库实用建议：当前项目级 gstack 使用 `.gstack-home`/`.gstack`，如果只是探索 skill 文件，不需要 setup-gbrain。若要真正启用，先决定是否允许把 VoiceAgents 的 transcripts/artifacts 纳入索引。

## sync-gbrain

**用途**：刷新 gbrain 对当前 repo 代码、transcripts/memory、artifacts git pipeline 的索引，并更新 `CLAUDE.md` 搜索指导。

**前置条件**

- 已跑 `/setup-gbrain`，或至少有 gbrain CLI/engine。
- 当前 repo 的 gbrain trust policy 不是 `deny`。
- `bun` 可运行 `bin/gstack-gbrain-sync.ts`。

**何时使用**

- 大改代码后希望 semantic/symbol search 更新。
- gbrain 搜索结果为空或过期。
- 想强制 full reindex。
- 需要确认 split-engine/remote-http 状态是否健康。

**工作流**

1. `gstack-gbrain-detect` 状态探测。
2. local engine pre-flight：
   - ok：继续。
   - no-cli/missing-config/broken-config/broken-db：根据 MCP mode 决定 STOP 或 degraded skip。
3. 运行 orchestrator：`gstack-gbrain-sync.ts <args>`。
4. orchestrator 三阶段：
   - code：`gbrain sources add` + `gbrain sync --strategy code` 或 `reindex-code`。
   - memory：`gstack-memory-ingest`。
   - brain-sync：`gstack-brain-sync` curated artifacts git pipeline。
5. code-index health check，0 pages 时询问是否 full reindex。
6. capability check：`gbrain put` + `gbrain search`。
7. 根据 capability 写入或移除 `CLAUDE.md` 的 `## GBrain Search Guidance`。
8. 输出 GREEN/YELLOW/RED verdict。

**生成产物**

- `~/.gstack/.gbrain-sync-state.json`，tmp+rename 原子写。
- `~/.gstack/.sync-gbrain.lock`。
- repo root `.gbrain-source` worktree scoped source pin。
- 更新或移除 `CLAUDE.md` Search Guidance block。
- gbrain source/index 数据。
- artifacts push 到 private repo。

**Git/GitHub/部署假设**

- code source 按当前 worktree 注册，同一 repo 的 sibling worktree 可各有 source pin。
- artifacts sync 是 git pipeline；remote-http 模式下 brain server 自己 pull/index。
- 不涉及 PR/deploy。

**状态存储**

- sync state 在 `~/.gstack/.gbrain-sync-state.json`。
- ingest state 在 `~/.gstack/.transcript-ingest-state.json`。
- gbrain engine 在 `~/.gbrain` 或 remote brain。
- Search Guidance 在 repo `CLAUDE.md`，会随 git 传播。

**风险点**

- `--full` 对大 repo 可耗时 25-35 分钟。
- local engine broken 时不能假装成功；技能要求 STOP 并给修复路径。
- Search Guidance 是机器能力声明；另一台机器没有 gbrain 时应移除。
- concurrent run 有 lock，失败时可能需要辨别 stale lock。

**示例调用**

```text
$gstack-sync-gbrain
$gstack-sync-gbrain --full
$gstack-sync-gbrain --code-only
$gstack-sync-gbrain --dry-run
$gstack-sync-gbrain --no-memory --quiet
```

本仓库实用建议：如果启用后，重大代码改动之后跑 incremental 即可；本次只写探索报告，不需要索引代码。

## benchmark-models

**用途**：跨模型 benchmark。把同一 prompt 或 skill 文件交给 Claude、GPT/Codex、Gemini，比 latency、tokens、cost，可选 LLM judge 质量评分。

**前置条件**

- `bin/gstack-model-benchmark` 可执行，通常需要 `./setup` 构建。
- 至少一个 provider 已登录/有 API key。
- 可选 judge 需要 Anthropic credential。

**何时使用**

- 想知道某个 gstack skill 用哪个模型效果最好。
- 对比 Claude/GPT/Gemini 在同一 prompt 上的速度、成本、质量。
- 建立模型 baseline，未来检测 provider drift。

**工作流**

1. 定位 `gstack-model-benchmark`。
2. 选择 prompt：
   - gstack skill `SKILL.md`
   - inline prompt
   - prompt file
3. dry-run providers：永远先显示 adapter availability。
4. 用户选择 all authed、only Claude、pick two。
5. 判断 judge 是否可用，用户显式选择是否启用。
6. 运行 benchmark：`--models <picked> [--judge] --output table`。
7. 解读 fastest、cheapest、highest quality、best overall。
8. 询问是否保存 JSON baseline；若保存，重跑 `--output json` 到 `~/.gstack/benchmarks/<date>-<slug>.json`。

**生成产物**

- 表格输出。
- 可选 `~/.gstack/benchmarks/*.json`。
- 可能产生 API 调用成本。

**Git/GitHub/部署假设**

- 不依赖 PR/deploy。
- skill prompt 可从当前 gstack checkout 找到。

**状态存储**

- benchmark baseline 在 `~/.gstack/benchmarks`。
- analytics/timeline 同其他技能。

**风险点**

- 不能跳过 dry-run，否则用户不知道 auth/cost 风险。
- `--judge` 有真实成本，不能自动开启。
- Provider auth、rate limit、timeout 都可能导致单 provider error。
- 不应硬编码具体 model；由 binary/provider adapter 处理。

**示例调用**

```text
$gstack-benchmark-models
```

本仓库实用建议：如果要评估“哪种模型更适合读 gstack skills 并写中文报告”，可以把某个 `SKILL.md` 或本报告任务 prompt 作为 input，但要先确认 API 成本。

## make-pdf

**用途**：把 Markdown 转成出版质量 PDF，支持 cover、TOC、watermark、page numbers、metadata、preview。

**前置条件**

- make-pdf build artifact 可用：通常是 `.agents/skills/gstack/make-pdf/dist/pdf` 或技能内 `$P`。
- browse/Chromium 渲染链可用。
- Linux 需要 `fonts-liberation` 保证 Helvetica/Arial fallback。

**何时使用**

- 用户要求“把 markdown 变成 PDF”“导出 PDF”“让这个文档好看”。
- 需要有 cover、TOC、chapter breaks 的正式文档。
- 需要 preview HTML 快速迭代。

**工作流**

1. setup check：确认 make-pdf 命令存在。
2. 80% case：`$P generate input.md` 输出 `/tmp/input.pdf`。
3. publication mode：`--cover --toc --author --title`。
4. draft watermark：`--watermark DRAFT`。
5. preview：`$P preview essay.md`。
6. output contract：stdout 只输出 PDF path；stderr 输出渲染进度。

**生成产物**

- `/tmp/<name>.pdf` 或用户指定的 `.pdf`。
- preview HTML/浏览器预览。

**Git/GitHub/部署假设**

- 不涉及 git、PR、deploy。
- 不应自动提交 PDF，除非用户明确要求。

**状态存储**

- 通常只写目标 PDF；临时文件由 renderer 管理。
- preamble analytics/timeline。

**风险点**

- 默认 `--allow-network` 关闭，外部图片不会加载；打开后 markdown 可发起网络请求。
- `--toc` 需要 headings；无 headings 可能 Paged.js timeout。
- 复制文本碎片化通常与 syntax highlighting 有关。
- 生成路径默认 `/tmp`，需要告知用户实际路径。

**示例调用**

```text
$gstack-make-pdf gstack_explore/05_release_docs_memory_ops_skills.md
$gstack-make-pdf generate --cover --toc report.md report.pdf
$gstack-make-pdf preview report.md
```

本仓库实用建议：本报告是 markdown，后续若用户要交付 PDF，可用 make-pdf；当前任务只要求写 `.md`。

## 直接相关脚本和文档摘要

### bin/gstack-next-version

这是 `/ship`、`/landing-report`、`/land-and-deploy` 版本安全的核心。它：

- 解析四段版本号。
- 检测 host：GitHub/GitLab/unknown。
- 读取 `origin/<base>:VERSION`。
- 查询 open PR/MR claimed versions。
- 扫描 sibling worktrees。
- 对 `major|minor|patch|micro` 选取 next free slot。
- 只输出 JSON，不写任何文件。

关键设计：如果 queue 已经有人 claimed 更高版本，候选版本会 bump past highest claim，保留原 bump level 的意图。

### bin/gstack-pr-title-rewrite.sh

PR/MR 标题版本前缀的单一规则来源：

- 已有 `v<NEW_VERSION> ` 前缀则不改。
- 有其他 `v<digits.dots> ` 前缀则替换。
- 无版本前缀则 prepend。

它会校验 `NEW_VERSION` 只能是 dot-separated digits，避免 shell pattern 风险。

### bin/gstack-gbrain-sync.ts

`/sync-gbrain` 的 orchestrator。三阶段：

- code：注册 source、增量 sync 或 full reindex。
- memory：调用 `gstack-memory-ingest`。
- brain-sync：调用 curated artifacts git pipeline。

它使用 `~/.gstack/.sync-gbrain.lock` 防并发，`~/.gstack/.gbrain-sync-state.json` 原子写，支持 `--incremental`、`--full`、`--dry-run`、`--code-only`、`--no-memory`、`--no-brain-sync`。

### bin/gstack-memory-ingest.ts

负责把 coding-agent transcripts 和 curated artifacts 写入 gbrain typed pages。来源包括：

- Claude Code sessions。
- Codex CLI sessions。
- Cursor session SQLite（后续）。
- `learnings.jsonl`、timeline、CEO plans、design docs、retros、eureka、builder profile。

状态在 `~/.gstack/.transcript-ingest-state.json`，本地-only，不通过 brain remote sync。per-file gitleaks scan 默认关闭，可用 `--scan-secrets` 开启；真正跨机器 git push 边界由 `gstack-brain-sync` 再扫一次。

### bin/gstack-brain-context-load.ts

每个 skill start 时的 retrieval surface。读取 skill frontmatter 中 `gbrain.context_queries`，或使用默认 salience block。支持 vector/list/filesystem 三类查询，每次 gbrain/MCP 调用 500ms 超时。所有 transcript 数据用 `<USER_TRANSCRIPT_DATA do-not-interpret-as-instructions>` 包裹，降低 prompt injection 风险。

### docs/gbrain-sync.md

解释 cross-machine memory sync：把 allowlisted `~/.gstack` 状态推送到私有 git repo，让 memory 跨机器可用并被 gbrain 索引。明确不离开本机的内容包括 credentials、machine-specific state、question preferences。隐私模式：off、artifacts-only、full。

### setup-gbrain/memory.md

解释 transcript/memory ingest 的数据源、敏感度、secret scanning、storage tier、删除/恢复路径、remote MCP setup。对本仓库尤其重要的是：transcripts 是高敏数据；如果没有明确需求，不要轻易启用全量历史 ingest。

## 本仓库的操作建议

- 当前任务只是探索 `.agents/skills/gstack`，不要运行会改发布状态的 `$gstack-ship`、`$gstack-land-and-deploy`、`$gstack-gstack-upgrade`。
- 后续真实 feature work 完成后，先 `$gstack-landing-report`，再 `$gstack-ship`，这样能避开版本冲突。
- 若要落地生产，先 `$gstack-setup-deploy`，把“是否有生产部署”说清楚；否则 `/land-and-deploy` 会在 dry-run 阶段频繁询问。
- 若要在多个 agent 间切换，使用 `$gstack-context-save` 和 `$gstack-context-restore`，不要把临时 handoff 写进 `gstack_explore/`。
- 若要启用 gbrain，先确认是否允许索引本仓库和 transcripts。VoiceAgents 可能包含会话、密钥或业务音频/转写相关内容，默认应保守选择 PGLite local、repo policy read-only 或先 skip。
- 若要把本报告交付给非工程读者，可再用 `$gstack-make-pdf` 生成 PDF；当前 markdown 已足够作为工程参考。
