# gstack 安装、运行时与项目级使用分析

日期：2026-05-28
工作区：`/Users/tanglin/VibeCoding/VoiceAgents`
gstack checkout：`.agents/skills/gstack`

## 结论摘要

本项目采用项目级 gstack：gstack 源码和运行时资产位于 `.agents/skills/gstack`，生成后的 Codex skills 以 `.agents/skills/gstack-*` 形式暴露给 Codex。不要使用用户级 `~/.codex/skills/gstack*`，也不要调用根 `$gstack` 作为主要入口。

项目级运行依赖两个定位机制：

1. Codex skill preamble 先执行 `git rev-parse --show-toplevel`，再检查 `<repo>/.agents/skills/gstack`，从而把 `GSTACK_ROOT` 指向项目内 runtime。
2. 浏览器 daemon 也用 git root 定位 `<repo>/.gstack/browse.json`、日志和项目级浏览器状态。

因此 `/Users/tanglin/VibeCoding/VoiceAgents` 必须保持为 git repo。当前验证结果：

```bash
git rev-parse --show-toplevel
```

输出：

```text
/Users/tanglin/VibeCoding/VoiceAgents
```

## 目录结构

当前项目内与 gstack 相关的主要目录：

```text
.
├── AGENTS.md
├── .agents/
│   └── skills/
│       ├── gstack/                         # 项目级 gstack 源码 checkout + runtime root
│       │   ├── README.md
│       │   ├── AGENTS.md
│       │   ├── ARCHITECTURE.md
│       │   ├── BROWSER.md
│       │   ├── package.json
│       │   ├── setup
│       │   ├── bin/
│       │   │   ├── gstack-config
│       │   │   ├── gstack-paths
│       │   │   └── ...
│       │   ├── browse/
│       │   │   ├── dist/browse             # 编译后的浏览器 CLI
│       │   │   └── src/
│       │   └── .agents/skills/
│       │       ├── gstack-browse/
│       │       ├── gstack-office-hours/
│       │       ├── gstack-qa/
│       │       ├── gstack-review/
│       │       └── ...
│       ├── gstack-browse -> .../gstack/.agents/skills/gstack-browse/
│       ├── gstack-office-hours -> .../gstack/.agents/skills/gstack-office-hours/
│       ├── gstack-qa -> .../gstack/.agents/skills/gstack-qa/
│       ├── gstack-review -> .../gstack/.agents/skills/gstack-review/
│       └── ...
├── .gstack/                                # 本项目的 gstack 状态根
├── .gstack-home/                           # 伪 HOME，隔离 ~/.gstack、Bun/Playwright 缓存
├── .bun/                                   # 项目级 Bun
└── problems/gstack-project-local-usage-2026-05-28.md
```

文件依据：

- `AGENTS.md`：明确要求项目使用 `.agents/skills/` 下的项目级 gstack，不使用用户级 `~/.codex/skills/gstack*`。
- `.agents/skills/gstack/README.md`：上游安装、技能、浏览器和 troubleshooting 总览。
- `.agents/skills/gstack/AGENTS.md`：gstack 自身的技能列表、构建命令和路径约定。
- `.agents/skills/gstack/ARCHITECTURE.md`：浏览器 daemon、状态文件、安全和日志模型。
- `.agents/skills/gstack/BROWSER.md`：`$B` 浏览器 CLI 的完整命令、环境变量和开发命令。
- `.agents/skills/gstack/setup`：Codex skill 生成、链接、runtime sidecar 和 Playwright 检查逻辑。
- `.agents/skills/gstack/bin/gstack-paths`、`.agents/skills/gstack/bin/gstack-config`：状态路径和配置解析。
- `problems/gstack-project-local-usage-2026-05-28.md`：本项目此前的验证记录。

## 项目级环境变量

手动运行 gstack 命令时应使用项目级环境，避免写入用户级 `~/.gstack` 或 `~/.codex`：

```bash
cd /Users/tanglin/VibeCoding/VoiceAgents

env \
  HOME="$PWD/.gstack-home" \
  GSTACK_HOME="$PWD/.gstack" \
  GSTACK_STATE_DIR="$PWD/.gstack" \
  PATH="$PWD/.bun/bin:$PATH" \
  <gstack-command>
```

各变量作用：

| 变量 | 项目建议值 | 作用 |
|---|---|---|
| `HOME` | `$PWD/.gstack-home` | 隔离所有硬编码到 `~` 的 gstack、Bun、Playwright、analytics/session 路径。 |
| `GSTACK_HOME` | `$PWD/.gstack` | gstack 主状态根；`gstack-config`、timeline、learnings、brain queue 等优先读取它。 |
| `GSTACK_STATE_DIR` | `$PWD/.gstack` | `gstack-config` 的 legacy alias；建议同时设置以兼容旧脚本。 |
| `PATH` | `$PWD/.bun/bin:$PATH` | 优先使用项目级 Bun，满足 `setup`、`bun run build`、`bun test` 和浏览器源码运行需求。 |

`gstack-paths` 的解析顺序见 `.agents/skills/gstack/bin/gstack-paths`：

- `GSTACK_STATE_ROOT`：`GSTACK_HOME` -> gstack plugin 的 `CLAUDE_PLUGIN_DATA` -> `$HOME/.gstack` -> `.gstack`
- `PLAN_ROOT`：`GSTACK_PLAN_DIR` -> `CLAUDE_PLANS_DIR` -> `$HOME/.claude/plans` -> `.claude/plans`
- `TMP_ROOT`：`TMPDIR` -> `TMP` -> `.gstack/tmp`

本项目用上述 env 实测：

```text
GSTACK_STATE_ROOT=/Users/tanglin/VibeCoding/VoiceAgents/.gstack
PLAN_ROOT=/Users/tanglin/VibeCoding/VoiceAgents/.gstack-home/.claude/plans
TMP_ROOT=/var/folders/4h/gzghpzjs6t77x9871tfmrsj40000gn/T/
```

## 为什么 git repo root 很重要

项目级 gstack 的核心定位逻辑依赖 `git rev-parse --show-toplevel`。

生成后的 Codex skill，例如 `.agents/skills/gstack-office-hours/SKILL.md` 和 `.agents/skills/gstack-browse/SKILL.md`，preamble 开头包含：

```bash
_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
GSTACK_ROOT="$HOME/.codex/skills/gstack"
[ -n "$_ROOT" ] && [ -d "$_ROOT/.agents/skills/gstack" ] && GSTACK_ROOT="$_ROOT/.agents/skills/gstack"
GSTACK_BIN="$GSTACK_ROOT/bin"
GSTACK_BROWSE="$GSTACK_ROOT/browse/dist"
```

也就是说：

- 如果当前目录是 git repo，并且 repo root 下存在 `.agents/skills/gstack`，skill 会使用项目级 runtime。
- 如果 git root 解析失败，默认值会回到 `$HOME/.codex/skills/gstack`。
- 本项目明确不希望回退到用户级路径，所以必须保持 git repo 可用。

浏览器 CLI 同样依赖 git root。`.agents/skills/gstack/browse/src/config.ts` 的解析顺序是：

1. `BROWSE_STATE_FILE` 显式指定。
2. `git rev-parse --show-toplevel` 后使用 `<repo>/.gstack/`。
3. 非 git 环境退回 `process.cwd()/.gstack/`。

`.agents/skills/gstack/BROWSER.md` 也说明每个 project root 会有独立 daemon、端口、状态文件、cookies 和日志，状态文件在 `<project>/.gstack/browse.json`。

## Codex skill 命名约定

本项目应优先调用生成后的 Codex skills：

```text
$gstack-office-hours
$gstack-browse
$gstack-qa
$gstack-review
$gstack-autoplan
```

不要调用根 `$gstack`。

原因：

- `.agents/skills/gstack` 是源码 checkout 和 runtime root。
- 根 `.agents/skills/gstack/SKILL.md` 偏 Claude/上游路径，用作总入口并不适合本项目的 Codex 使用方式。
- 生成后的 `.agents/skills/gstack-*` 是 Codex 兼容入口，内部会通过 git root 找到项目级 `.agents/skills/gstack`。

当前 `.agents/skills/` 下的 `gstack-*` 多数是 symlink，例如：

```text
.agents/skills/gstack-browse -> /Users/tanglin/VibeCoding/VoiceAgents/.agents/skills/gstack/.agents/skills/gstack-browse/
.agents/skills/gstack-office-hours -> /Users/tanglin/VibeCoding/VoiceAgents/.agents/skills/gstack/.agents/skills/gstack-office-hours/
```

`.agents/skills/gstack/setup` 中的 `link_codex_skill_dirs()` 说明 Codex 安装使用 `.agents/skills/gstack-*` 这些生成后的 Codex-format skills，而不是直接暴露源码目录里的 Claude-oriented skills。

## 安全、有用的手动命令

所有手动命令建议都从项目根目录执行：

```bash
cd /Users/tanglin/VibeCoding/VoiceAgents
```

### 确认 git root

```bash
git rev-parse --show-toplevel
```

期望：

```text
/Users/tanglin/VibeCoding/VoiceAgents
```

### 查看 gstack 配置默认值

```bash
env HOME="$PWD/.gstack-home" \
  GSTACK_HOME="$PWD/.gstack" \
  GSTACK_STATE_DIR="$PWD/.gstack" \
  PATH="$PWD/.bun/bin:$PATH" \
  "$PWD/.agents/skills/gstack/bin/gstack-config" list
```

当前实测关键默认值：

```text
proactive: true
telemetry: off
update_check: true
skill_prefix: false
checkpoint_mode: explicit
checkpoint_push: false
codex_reviews: enabled
artifacts_sync_mode: off
```

### 查看路径解析

```bash
env HOME="$PWD/.gstack-home" \
  GSTACK_HOME="$PWD/.gstack" \
  GSTACK_STATE_DIR="$PWD/.gstack" \
  PATH="$PWD/.bun/bin:$PATH" \
  "$PWD/.agents/skills/gstack/bin/gstack-paths"
```

### 浏览器状态

```bash
env HOME="$PWD/.gstack-home" \
  GSTACK_HOME="$PWD/.gstack" \
  GSTACK_STATE_DIR="$PWD/.gstack" \
  PATH="$PWD/.bun/bin:$PATH" \
  "$PWD/.agents/skills/gstack/browse/dist/browse" status
```

本次实测输出：

```text
[browse] Starting server...
Status: healthy
Mode: launched
URL: about:blank
Tabs: 1
PID: 24674
```

注意：`browse status` 可能会启动 daemon，并绑定 `127.0.0.1` 随机端口。在 Codex 沙箱中，如果遇到 localhost 绑定或进程检查失败，应申请非沙箱执行。

### 浏览器常用命令

```bash
B="$PWD/.agents/skills/gstack/browse/dist/browse"

env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" \
  "$B" goto https://example.com

env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" \
  "$B" snapshot -i

env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" \
  "$B" text

env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" \
  "$B" screenshot /tmp/gstack-shot.png
```

### 浏览器 daemon 生命周期

```bash
env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" \
  "$PWD/.agents/skills/gstack/browse/dist/browse" status

env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" \
  "$PWD/.agents/skills/gstack/browse/dist/browse" restart

env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" \
  "$PWD/.agents/skills/gstack/browse/dist/browse" stop
```

本次 `stop` 返回了：

```text
[browse] Server connection lost. Restarting...
[browse] [browse] Server crashed twice in a row — aborting
```

随后 `.gstack/browse.json` 不存在，说明 state file 已被清理；但沙箱内 `ps` 被拒绝，无法直接检查 PID。若怀疑残留进程，可在非沙箱 shell 中用 `ps -p <PID>` 或 `pkill -f "gstack.*browse"` 检查/清理。

## Browser daemon 前置条件

gstack 浏览器模型见 `.agents/skills/gstack/ARCHITECTURE.md` 和 `.agents/skills/gstack/BROWSER.md`：

- CLI 是 `.agents/skills/gstack/browse/dist/browse`。
- 首次调用会启动长期运行的 Chromium daemon。
- CLI 与 daemon 通过 `127.0.0.1:<random-port>` HTTP 通信。
- daemon 使用 Playwright 管理 Chromium。
- daemon state file 位于 `<project>/.gstack/browse.json`，包含 `pid`、`port`、`token`、`startedAt`、`binaryVersion`。
- state file 权限设计为 owner-only；HTTP mutating command 需要 bearer token。
- 默认 idle timeout 是 30 分钟。
- 每个 git project root 独立 daemon，避免多 workspace 端口、cookie 和 tab 状态互相污染。

前置条件：

- Bun v1.0+。`.agents/skills/gstack/package.json` 的 `engines` 要求 `bun >=1.0.0`。
- Playwright Chromium。`setup` 会检查并在缺失时运行 `bunx playwright install chromium`。
- macOS/Linux 支持完整测试；Windows 需要 Git Bash/MSYS，且 Node.js 也需要可用，因为 Bun 在 Windows 上启动 Chromium 有已知 pipe transport 问题。
- Codex 沙箱中运行 `$gstack-browse` 或直接 `browse status/goto/...` 可能需要非沙箱权限，因为 daemon 要绑定 localhost、启动后台进程并访问 Playwright 浏览器缓存。

重要环境变量见 `.agents/skills/gstack/BROWSER.md`：

| 变量 | 说明 |
|---|---|
| `BROWSE_PORT` | 固定 HTTP server 端口；默认随机 10000-60000。 |
| `BROWSE_IDLE_TIMEOUT` | idle shutdown timeout，默认 1800000 ms。 |
| `BROWSE_STATE_FILE` | 显式指定 state file；默认 `<repo>/.gstack/browse.json`。 |
| `BROWSE_SERVER_SCRIPT` | server.ts 路径，通常自动探测。 |
| `BROWSE_CDP_URL` / `BROWSE_CDP_PORT` | real-browser/CDP 模式内部使用。 |
| `BROWSE_TUNNEL` | pair-agent tunnel 模式，通常需要 `NGROK_AUTHTOKEN`。 |
| `GSTACK_SECURITY_OFF` | sidebar agent prompt-injection ML classifier kill switch。 |
| `GSTACK_SECURITY_ENSEMBLE` | 设为 `deberta` 时启用更大的 DeBERTa ensemble。 |

## 构建与测试命令

gstack 上游 build/test 命令来自 `.agents/skills/gstack/AGENTS.md` 和 `.agents/skills/gstack/package.json`。

在本项目中手动运行时仍应带项目级 env：

```bash
cd /Users/tanglin/VibeCoding/VoiceAgents/.agents/skills/gstack

env HOME="/Users/tanglin/VibeCoding/VoiceAgents/.gstack-home" \
  GSTACK_HOME="/Users/tanglin/VibeCoding/VoiceAgents/.gstack" \
  GSTACK_STATE_DIR="/Users/tanglin/VibeCoding/VoiceAgents/.gstack" \
  PATH="/Users/tanglin/VibeCoding/VoiceAgents/.bun/bin:$PATH" \
  bun install
```

常用命令：

```bash
bun install              # 安装依赖，通常也准备 Playwright Chromium
bun test                 # 免费测试，不跑高成本 eval
bun run test:free        # free test shards
bun run test:windows     # Windows-safe subset
bun run build            # 生成 docs + 编译 browse/make-pdf 等 binary
bun run gen:skill-docs   # 根据模板重新生成 SKILL.md
bun run gen:skill-docs --host codex
bun run skill:check      # skill health dashboard
bun run dev <cmd>        # 从源码运行 browse CLI，不用编译
```

`package.json` 中 `test` 实际运行：

```bash
bun test browse/test/ test/ make-pdf/test/ \
  --ignore 'test/skill-e2e-*.test.ts' \
  --ignore test/skill-llm-eval.test.ts \
  --ignore test/skill-routing-e2e.test.ts \
  --ignore test/codex-e2e.test.ts \
  --ignore test/gemini-e2e.test.ts
```

高成本/真实模型 eval 由 `EVALS=1` 相关命令触发，例如 `bun run test:evals`、`bun run test:e2e`。这些不应作为普通本地验证默认执行。

## 状态、缓存和日志位置

本项目建议的隔离布局：

```text
.gstack/                 # GSTACK_HOME / GSTACK_STATE_DIR
.gstack-home/            # HOME
.bun/                    # 项目级 Bun
```

`.gstack/` 当前观察到：

```text
.gstack/
├── browse-audit.jsonl
├── claude-available.json
├── last-update-check
└── projects/
    └── VoiceAgents/
        └── timeline.jsonl
```

可能出现的其他项目状态：

| 路径 | 来源/用途 |
|---|---|
| `.gstack/browse.json` | browse daemon pid/port/token/state；daemon 停止后可能消失。 |
| `.gstack/browse-console.log` | 浏览器 console ring buffer 的落盘日志。 |
| `.gstack/browse-network.log` | 网络请求日志。 |
| `.gstack/browse-dialog.log` | dialog 日志。 |
| `.gstack/browse-audit.jsonl` | 浏览器 audit/活动记录。 |
| `.gstack/projects/<SLUG>/timeline.jsonl` | skill timeline。 |
| `.gstack/projects/<SLUG>/learnings.jsonl` | 项目 learnings。 |
| `.gstack/projects/<SLUG>/question-log.jsonl` | question/tuning 记录。 |
| `.gstack/browser-skills/<name>/` | 项目级 browser-skill，优先级高于 global 和 bundled。 |
| `.gstack/domain-skills/<host>.md` | 项目级 domain-skill。 |
| `.gstack/security/attempts.jsonl` | tunnel denial / prompt injection attempt log。 |

`.gstack-home/` 当前观察到：

```text
.gstack-home/
├── .gstack/
│   ├── analytics/
│   ├── projects/
│   ├── sessions/
│   └── slug-cache/
└── Library/Caches/
    ├── bun/
    └── ms-playwright/
```

注意：部分上游脚本仍写 `~/.gstack/...`，所以本项目通过 `HOME="$PWD/.gstack-home"` 把这些写入隔离到 `.gstack-home/.gstack/`。同时设置 `GSTACK_HOME="$PWD/.gstack"` 能让已适配的脚本写入 `.gstack/`。两者并存是当前项目级隔离策略的一部分。

## 常见排障

### 1. skill 找不到项目级 runtime

症状：

- skill 试图访问 `$HOME/.codex/skills/gstack`。
- 报 `gstack install directory not found`。
- `GSTACK_ROOT` 没有指向 `.agents/skills/gstack`。

检查：

```bash
git rev-parse --show-toplevel
test -d "$(git rev-parse --show-toplevel)/.agents/skills/gstack" && echo ok
```

修复：

```bash
cd /Users/tanglin/VibeCoding/VoiceAgents
git init                         # 仅当目录不是 git repo 时
git rev-parse --show-toplevel
```

### 2. Codex skill 缺失或 stale

检查：

```bash
ls -la .agents/skills/gstack-browse
ls -la .agents/skills/gstack-office-hours
find .agents/skills/gstack/.agents/skills -maxdepth 2 -name SKILL.md | sort | head
```

重新生成 Codex skill：

```bash
cd /Users/tanglin/VibeCoding/VoiceAgents/.agents/skills/gstack

env HOME="/Users/tanglin/VibeCoding/VoiceAgents/.gstack-home" \
  GSTACK_HOME="/Users/tanglin/VibeCoding/VoiceAgents/.gstack" \
  GSTACK_STATE_DIR="/Users/tanglin/VibeCoding/VoiceAgents/.gstack" \
  PATH="/Users/tanglin/VibeCoding/VoiceAgents/.bun/bin:$PATH" \
  bun run gen:skill-docs --host codex
```

如果需要重新执行 setup，仍使用项目级 env：

```bash
env HOME="/Users/tanglin/VibeCoding/VoiceAgents/.gstack-home" \
  GSTACK_HOME="/Users/tanglin/VibeCoding/VoiceAgents/.gstack" \
  GSTACK_STATE_DIR="/Users/tanglin/VibeCoding/VoiceAgents/.gstack" \
  PATH="/Users/tanglin/VibeCoding/VoiceAgents/.bun/bin:$PATH" \
  ./setup --host codex
```

### 3. `$gstack-browse` 或 `browse status` 失败

检查 binary：

```bash
test -x .agents/skills/gstack/browse/dist/browse && echo browse-binary-ok
```

重新构建：

```bash
cd .agents/skills/gstack
env HOME="/Users/tanglin/VibeCoding/VoiceAgents/.gstack-home" \
  GSTACK_HOME="/Users/tanglin/VibeCoding/VoiceAgents/.gstack" \
  GSTACK_STATE_DIR="/Users/tanglin/VibeCoding/VoiceAgents/.gstack" \
  PATH="/Users/tanglin/VibeCoding/VoiceAgents/.bun/bin:$PATH" \
  bun install

env HOME="/Users/tanglin/VibeCoding/VoiceAgents/.gstack-home" \
  GSTACK_HOME="/Users/tanglin/VibeCoding/VoiceAgents/.gstack" \
  GSTACK_STATE_DIR="/Users/tanglin/VibeCoding/VoiceAgents/.gstack" \
  PATH="/Users/tanglin/VibeCoding/VoiceAgents/.bun/bin:$PATH" \
  bun run build
```

如果失败信息涉及 localhost、端口、进程检查、Chromium launch、Playwright cache，Codex 沙箱可能拦截了后台进程或 loopback 绑定；需要申请非沙箱执行。

### 4. daemon 状态文件异常

检查：

```bash
ls -la .gstack
test -f .gstack/browse.json && cat .gstack/browse.json
```

`browse.json` 缺失并不一定是错误：daemon 未运行或已停止时可以不存在。若 state file 存在但 health check 失败，CLI 正常会启动新 daemon。

### 5. 误写用户级目录

检查用户级是否被污染：

```bash
ls -la ~/.codex/skills/gstack* 2>/dev/null || true
ls -la ~/.gstack 2>/dev/null || true
```

本项目原则是不依赖这些路径。手动命令统一使用：

```bash
env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" ...
```

### 6. 不要执行根 `$gstack`

`AGENTS.md` 明确要求：

```text
不要调用根 `$gstack`。`.agents/skills/gstack` 是运行时目录和源码 checkout，根 `SKILL.md` 偏 Claude 路径；`$gstack-*` 才是 Codex 兼容入口。
```

正确入口：

```text
$gstack-office-hours
$gstack-browse
$gstack-qa
$gstack-review
$gstack-autoplan
```

### 7. Windows 特殊问题

`.agents/skills/gstack/setup` 和 `README.md` 说明：

- Windows 需要 Git Bash/MSYS。
- Windows 上 Bun 启动 Chromium 有已知问题，setup 会要求 Node.js 并用 Node 验证 Playwright。
- Windows 无 Developer Mode 时 setup 会复制文件而非 symlink；每次 `git pull` 后需要重新运行 setup 刷新 skill 文件。

本项目当前运行在 macOS 路径下，不适用这些 Windows fallback，但排查跨平台问题时需要注意。

## 建议的本项目操作准则

1. 始终从 `/Users/tanglin/VibeCoding/VoiceAgents` 项目根运行 gstack 相关命令。
2. 始终带项目级 `HOME`、`GSTACK_HOME`、`GSTACK_STATE_DIR`、`PATH`。
3. 调用 Codex skill 时使用 `$gstack-*`，不要使用根 `$gstack`。
4. 保持项目为 git repo；若 skill 解析异常，第一步运行 `git rev-parse --show-toplevel`。
5. 浏览器类命令可能启动 daemon 和绑定 localhost；在 Codex 沙箱失败时申请非沙箱执行。
6. 修改 gstack skill 输出时编辑 `.tmpl` 并运行 `bun run gen:skill-docs --host codex`，不要直接改生成的 `SKILL.md`。
7. 普通验证优先使用 `gstack-config list`、`gstack-paths`、`browse status`、`bun test`；避免默认运行 `EVALS=1` 的真实模型测试。
