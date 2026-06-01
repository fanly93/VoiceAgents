# VoiceAgents Realtime MVP / Pilot Validation Harness Handoff

更新时间：2026-06-01

本文档是新会话继续工作的主入口。新会话应先阅读本文件，然后直接从“下一步任务”开始，不需要重新从零探索项目。

## 一句话状态

OpenAI Realtime 真实语音 MVP、failure-mode 验证和真实语音手动验证主体已经完成；当前正在 `feat/pilot-validation-harness` 分支上收口 Pilot Validation Harness v1。该分支已实现本地验证报告能力，当前最重要的下一步是按 gstack workflow 做 merge 前 `$gstack-review`，修复 findings 后再合并回 `main`。

## 当前 Git 状态

当前分支：

```bash
feat/pilot-validation-harness
```

当前状态：

```bash
git status --short --branch
# ## feat/pilot-validation-harness...origin/main [ahead 6]
```

当前分支从 `origin/main` 派生，领先 6 个提交。最近提交：

```text
0fc1911 fix: preserve safe validation event names
9a11b6b test: preserve failure-mode harness with validation init
f896bfc docs: document validation harness completion
923d323 feat: add realtime validation harness
f0c08f8 docs: add pilot validation harness tasks
25b162e docs: spec pilot validation harness
72b9e0b origin/main docs: archive failure-mode validation merge
```

注意：分支原名是 `feat/product-cut-discovery`，已重命名为 `feat/pilot-validation-harness`。部分 spec/tasks 文件里的 `Branch:` 元数据可能仍残留旧分支名，这是 merge 前 docs/code drift 检查需要修掉的小问题。

## 项目规则

项目级规则见 `AGENTS.md`。关键点如下：

- 使用项目级 gstack，位于 `.agents/skills/`。
- 优先使用 `$gstack-office-hours`、`$gstack-browse`、`$gstack-qa`、`$gstack-review`、`$gstack-autoplan`。
- 不要调用根 `$gstack`。
- 每个新需求必须从干净 `main` 新建 feature branch。
- `$gstack-review` 必须在 feature branch 合并前运行。
- Python 命令必须使用隔离环境，例如 `./.venv/bin/python`，不要使用系统 Python。
- 每完成一个小功能、修复或文档更新，都应先测试再 checkpoint commit。
- 探索性测试、浏览器自动化产物、合成音频、验证报告默认放到已忽略目录，例如 `test-artifacts/` 或 `.voiceagents/`。

手动运行 gstack 命令时使用项目级环境：

```bash
env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" <gstack-command>
```

## 已完成阶段

### 1. OpenAI Realtime Voice MVP

已完成并合并到 `main`：

- 浏览器麦克风输入。
- OpenAI Realtime WebRTC 会话。
- 浏览器播放模型语音输出。
- `Text / Voice` 模式切换。
- `Mute` 控制本地麦克风音轨，不是静音模型输出。
- `Stop` 清理 data channel、peer connection、本地 tracks、remote audio 和 secret-bearing state。
- OpenAI tool call relay。
- provider events 和 transcript 日志。
- 安全脱敏，不保存 raw audio、SDP、API key、client secret、tool token、Authorization header、未脱敏 transcript。

主要文件：

```text
voiceagents/api/app.py
voiceagents/api/static/realtime-test.html
voiceagents/api/static/realtime-openai-adapter.js
voiceagents/realtime/contracts.py
voiceagents/realtime/event_log.py
voiceagents/realtime/providers.py
voiceagents/realtime/session_store.py
voiceagents/realtime/tool_router.py
```

### 2. Failure-mode 验证

已完成并归档：

- 浏览器 failure-mode 自动化模拟覆盖。
- OpenAI adapter 错误路径覆盖。
- event log error、provider error、data channel error 等异常路径已纳入测试。
- 不再需要在当前阶段继续围绕 failure-mode 做新分支。

相关基线：

```text
origin/main commit 72b9e0b docs: archive failure-mode validation merge
```

### 3. 真实语音人工验证

已完成核心验证：

- `/realtime-test` 可以连接 OpenAI Realtime。
- Text 模式下只有文字输出，没有语音输出，这是符合预期的。
- Voice 模式下有语音输出，这是符合预期的。
- Mute 只影响本地麦克风输入，模型已经开始说话时点击 Mute 不会静音模型声音。
- 3 分钟以上真实语音会话已经跑通。
- 工具链路已验证过订单、物流、商品知识、转人工等主要路径。
- 后来用户确认订单/物流两个工具不再继续测旧占位数据。

已发现并修正过的关键问题：

- 测试数据一度使用 `ORDER-REDACTED-001` 这类明显占位数据，后来已改为更真实的合成测试订单号。
- 浏览器假麦克风音频注入不稳定，用户确认可用真实麦克风或手机播放方式辅助测试。
- 需要把验证结果保存成可复查报告，因此进入 Pilot Validation Harness v1。

## 当前阶段：Pilot Validation Harness v1

### 目标

在现有 `/realtime-test` 页面上增加本地验证工具，让研发、试点商家 demo、客服接手上下文三个目标都能留下脱敏验证证据。

验证结果保存为：

```text
.voiceagents/validation-runs/<run_id>/summary.json
.voiceagents/validation-runs/<run_id>/report.md
```

这些输出在 `.voiceagents/` 下，是本地 gitignored 产物，不提交。

### 已完成的 spec / plan / tasks

相关文档：

```text
docs/specs/voiceagents-pilot-validation-harness-v1.md
docs/specs/voiceagents-pilot-validation-harness-v1-tasks.md
docs/superpowers/plans/2026-06-01-pilot-validation-harness-v1.md
docs/reviews/plan-eng-review-pilot-validation-harness-v1-2026-06-01.md
```

状态：

```text
Status: IMPLEMENTED
```

注意：如果这些文档里仍写 `Branch: feat/product-cut-discovery`，应在 merge 前作为 docs drift 修复为 `feat/pilot-validation-harness`。

### 已实现功能

后端新增：

- 固定五个验证场景。
- `GET /v1/realtime/validation-scenarios`
- `POST /v1/realtime/validation-runs`
- `POST /v1/realtime/validation-runs/{run_id}/finish`
- server-generated `run_id`
- 本地 path-safe repository
- 自动 pass/fail checks
- 脱敏 summary/report 写入

前端新增：

- `/realtime-test` 的 Validation Run 区域。
- scenario selector。
- `Start Validation Run`。
- `Finish Run`。
- heard voice、voice quality、business answer、demo ready、notes 等人工检查项。
- 当前 `run_id` 显示。
- 保存结果提示。
- JS 测试辅助接口 `window.voiceAgentsRealtimeTest`。

五个固定场景：

```text
order_status
logistics_tracking
product_knowledge
knowledge_low_confidence_handoff
customer_requested_human
```

主要实现文件：

```text
voiceagents/realtime/validation.py
voiceagents/api/app.py
voiceagents/api/static/realtime-test.html
```

主要测试文件：

```text
tests/test_realtime_validation.py
tests/test_api_realtime_validation.py
tests/test_realtime_test_page_validation_flow.py
tests/test_api_realtime_test_page.py
tests/test_realtime_test_page_failure_modes.py
```

### 安全边界

Validation Harness 不保存：

- raw audio
- audio bytes
- SDP
- OpenAI API key
- client secret
- tool call token
- Authorization header
- raw tool arguments
- 未脱敏 transcript
- 真实客户 PII

实现里已经修过一个安全扫描误伤问题：

- blocked text token 和 blocked field name 分离。
- 保留合法 event 名称，例如 `output_audio_transcript`。
- 防止因为 generic `audio` token 误伤正常 provider event 名称。

## 最近验证结果

当前分支最后一次完整验证记录：

```bash
./.venv/bin/python -m pytest
# 182 passed, 1 warning
```

格式检查记录：

```bash
git diff --check
# pass
```

本 handoff 更新是 docs-only 修改；如果新会话接手后要继续 merge 前流程，应重新跑一次验证，不要只依赖历史结果。

## 当前未完成事项

### Blocking

当前分支还没有执行 merge 前 `$gstack-review`。按项目 workflow，必须先 review，再修复 findings，再合并。

### High

需要修复可能的文档元数据 drift：

- `docs/specs/voiceagents-pilot-validation-harness-v1.md`
- `docs/specs/voiceagents-pilot-validation-harness-v1-tasks.md`

重点检查是否仍写旧分支名 `feat/product-cut-discovery`。

### Medium

需要最终确认 README、handoff、spec、tasks 与当前实现一致：

- endpoint 名称是否一致。
- validation run 保存路径是否一致。
- 五个场景是否一致。
- 测试数据是否不再使用明显占位字符串。
- out-of-scope 是否仍明确：不做商家后台、不做客服后台、不做生产审计、不接电话供应商、不保存 raw audio。

### Low

后续可改进但不阻塞当前合并：

- 真实浏览器自动化的 fake microphone 路线仍不稳定。
- Validation Harness v1 还没有 CLI。
- 还没有商家可读的漂亮报告页面。
- 还没有客服后台接手页面。

## 下一步任务

建议新会话按下面顺序继续：

### Step 1: 确认状态

```bash
git status --short --branch
git log --oneline --decorate --max-count=8
```

期望看到：

```text
## feat/pilot-validation-harness...origin/main [ahead 6]
```

如果看到 docs-only handoff 修改未提交，这是正常的，先处理本文档更新的 checkpoint。

### Step 2: 提交本文档 checkpoint

如果本 handoff 是唯一修改，建议提交：

```bash
git add OPENAI_REALTIME_VOICE_MVP_HANDOFF.md
git commit -m "docs: refresh pilot validation handoff"
```

提交前可检查：

```bash
git diff --check
```

### Step 3: 修复明显 docs drift

检查并修复旧分支名：

```bash
rg "feat/product-cut-discovery|product-cut-discovery" .
```

预期把当前阶段相关文档改为：

```text
feat/pilot-validation-harness
```

这一步是 docs-only，可单独 commit。

### Step 4: 跑 merge 前验证

```bash
./.venv/bin/python -m pytest
git diff --check
```

### Step 5: 运行 `$gstack-review`

按项目级 gstack 环境执行 merge 前 review。不要在合并后才做，因为 `$gstack-review` 依赖当前分支 vs base branch 的 diff。

推荐审查重点：

- specs 和代码是否一致。
- validation endpoints 是否只作为 local/dev harness。
- 保存报告是否严格脱敏。
- `.voiceagents/validation-runs/` 是否未提交。
- 旧 failure-mode 测试是否仍通过。
- 是否引入不必要的生产逻辑变化。

### Step 6: 修复 review findings

按严重程度修复：

```text
Critical / High / Medium / Low
```

每个独立修复应：

1. 写或更新测试。
2. 修代码或文档。
3. 跑 focused test。
4. 小 commit。

### Step 7: 最终验证并准备 merge

最终至少跑：

```bash
./.venv/bin/python -m pytest
git diff --check
```

通过后再 push / PR / merge。

### Step 8: merge 后归档

合并回 `main` 后，做 docs-only post-merge archive checkpoint：

- 更新 handoff。
- 更新 README。
- 更新 spec/tasks 状态。
- 记录最终测试结果。
- 明确下一阶段产品切口。

## 新会话不要重复做的事

不要重新从零探索以下内容：

- 不需要重新确认 OpenAI Realtime MVP 是否存在，已经实现并合并。
- 不需要重新做 failure-mode 分支，已经完成。
- 不需要继续纠结 `Text / Voice` 基本语义：Text 是文本输出，Voice 是语音输出。
- 不需要把 Mute 当成模型输出静音，它只控制本地麦克风输入。
- 不需要继续使用明显占位订单号，例如 `ORDER-REDACTED-001`。
- 不需要尝试把 `.voiceagents/validation-runs/` 提交进 git。
- 不需要用系统 Python。

## 可能踩坑

### 1. gstack skill 入口

使用项目级 `$gstack-*` skills，不要调用根 `$gstack`。

### 2. 分支名 drift

当前分支已经是：

```text
feat/pilot-validation-harness
```

如果文档里还出现旧分支：

```text
feat/product-cut-discovery
```

那是历史残留，应修复。

### 3. 测试数据

测试数据必须真实感合成，不要用明显占位或泄漏真实 PII。

当前推荐合成订单格式类似：

```text
ORD-20260601-1842
```

### 4. 验证产物

验证报告写入：

```text
.voiceagents/validation-runs/<run_id>/
```

这是本地输出，不提交。

### 5. 浏览器音频自动化

`--use-file-for-fake-audio-capture` 在当前环境不稳定。需要真实语音验证时，可以使用用户麦克风或用户手机播放测试音频辅助。

## 建议的下一阶段产品方向

当前阶段完成并 merge 后，下一阶段不建议继续只围绕测试页打磨。用户已经明确三个方向都需要：

1. 研发/自己用来稳定验收真实语音能力。
2. 给试点商家看 demo 并收集反馈。
3. 让客服团队能接手转人工上下文。

Pilot Validation Harness v1 覆盖了第 1 个方向，并为第 2、3 个方向留下报告基础。后续更合理的产品切口可能是：

- Pilot demo report viewer：把本地 report 变成更适合试点商家看的页面。
- Human handoff context viewer：把转人工上下文整理成客服可接手的结构。
- Validation scenario runner v2：把五个场景做成更明确的 guided workflow。

但在进入这些新功能前，必须先完成当前分支的 `$gstack-review`、修复 findings、merge 和 post-merge archive。

## 快速启动清单

新会话开局直接执行：

```bash
git status --short --branch
rg "feat/product-cut-discovery|product-cut-discovery" .
git diff --check
./.venv/bin/python -m pytest
```

然后进入：

```text
$gstack-review -> 修复 findings -> full verification -> PR/merge -> post-merge archive
```
