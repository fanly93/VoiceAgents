# VoiceAgents Realtime MVP / Pilot Validation Harness Handoff

更新时间：2026-06-01

本文档是新会话继续工作的主入口。新会话应先阅读本文件，然后直接从“下一阶段建议”开始，不需要重新从零探索项目。

## 一句话状态

OpenAI Realtime 真实语音 MVP、failure-mode 验证、真实语音手动验证、Pilot Validation Harness v1 和本地 validation report viewer 都已经完成。当前文档记录最终状态、验证证据和下一阶段产品切口。

## 当前 Git 状态

已合并基线：

```bash
main / origin/main
```

合并记录：

```text
PR #8: https://github.com/fanly93/VoiceAgents/pull/8
Merge commit: 015ad92 Add pilot validation harness
Merged at: 2026-06-01T14:54:19Z
```

Pilot Validation Harness 关键提交：

```text
80de35e fix: require observed validation session state
f54b530 fix: avoid validation scan false failures
e0358fa docs: align pilot validation branch metadata
2696b53 docs: refresh pilot validation handoff
0fc1911 fix: preserve safe validation event names
9a11b6b test: preserve failure-mode harness with validation init
f896bfc docs: document validation harness completion
923d323 feat: add realtime validation harness
f0c08f8 docs: add pilot validation harness tasks
25b162e docs: spec pilot validation harness
72b9e0b origin/main docs: archive failure-mode validation merge
```

分支原名是 `feat/product-cut-discovery`，后续已重命名为 `feat/pilot-validation-harness`。merge 前已修复当前阶段 spec/tasks/review 文档里的旧分支名 drift。

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

## 已完成阶段：Pilot Validation Harness v1

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
Status: IMPLEMENTED / MERGED
```

这些文档已在 PR #8 merge 前对齐到 `feat/pilot-validation-harness`。

### 已实现功能

后端新增：

- 固定五个验证场景。
- `GET /v1/realtime/validation-scenarios`
- `POST /v1/realtime/validation-runs`
- `POST /v1/realtime/validation-runs/{run_id}/finish`
- `GET /v1/realtime/validation-report-runs`
- `GET /v1/realtime/validation-report-runs/{run_id}`
- server-generated `run_id`
- 本地 path-safe repository
- 自动 pass/fail checks
- 脱敏 summary/report 写入
- 从 `.voiceagents/validation-runs/<run_id>/summary.json` 读取本地 report viewer summary

前端新增：

- `/realtime-test` 的 Validation Run 区域。
- `/realtime-validation-reports` 本地 validation report viewer。
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

Validation report viewer v1 是 local-only 工具，只读取本机 `.voiceagents/validation-runs/` 产物。它没有 public sharing、auth、上传、托管导出或生产 report portal；试点/demo 前的 report prep 目标是 1-3 分钟内在本地完成。

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

PR #8 merge 前最终完整验证记录：

```bash
./.venv/bin/python -m pytest
# 183 passed, 1 warning
```

格式检查记录：

```bash
git diff --check
# pass
```

`$gstack-review` 已在 merge 前完成，发现并修复两个 informational findings：

- 合法 provider event 名称 `response.output_audio_transcript.done` 不再触发 blocked-secret scan 假失败。
- `session_observed` 不再接受 `idle` 这类未真正观察到会话的状态。

## 当前未完成事项

### Blocking

无。Pilot Validation Harness v1 已完成、review、验证、PR 并合并。

### Follow-up

- Realtime Voice Dev Diagnostics v1 已完成：`GET /v1/realtime/dev-diagnostics`、`/realtime-test` 的 `Run Diagnostics`、`scripts/diagnose_realtime_dev.py`。
- Realtime Tool Error Semantics v1 已完成：`tool_status` / `error_message`、结构化 tool-call HTTP 错误、adapter exception 安全降级、event log 使用真实 tool status、失败工具结果不回传 provider。
- Validation Harness v1 还没有 CLI，但当前没有明确痛点，先不做。
- Validation report viewer v1 只解决本地查看和 1-3 分钟 report prep；public sharing/auth 或生产 report portal 已记录为阶段 2，当前先后置。
- 客服后台接手页面 / support workbench 已记录为阶段 3，当前先后置。
- 真实浏览器自动化的 fake microphone 路线仍不稳定；真实语音验证仍建议用真实麦克风或手机播放辅助。

## 下一阶段建议

进入下一阶段前，从干净 `main` 新建 feature branch。不要继续在已合并的 `feat/pilot-validation-harness` 上开发。

推荐切口：

1. Provider adapter boundary hardening：为后续 DashScope、火山云或其他 provider 接入做 provider-neutral contract tests 和 event normalization 校验。
2. Other model/provider integration planning：在不改业务工具层的前提下，明确 DashScope、火山云或其他 provider 的 server credential、browser/server connection adapter、event normalization 和 tool result mapping。
3. Realtime session lifecycle cleanup：检查 session、tool token、event log TTL、重复提交、结束状态、handoff 状态转换、异常断线后的状态一致性。
4. Pilot demo report sharing/auth：阶段 2，已在 `docs/roadmap/voiceagents-phase-2-pilot-merchant-worksplit.md` 记录分工，当前先后置。
5. Human handoff context viewer / support workbench：阶段 3，已在 `docs/roadmap/voiceagents-phase-3-customer-support-worksplit.md` 记录分工，当前先后置。

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

PR #8 merge 前已修复当前阶段文档里的旧分支名 drift。后续新需求应从干净 `main` 新建分支，不要复用旧 feature branch。

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

这是 local-only 输出，`.voiceagents/validation-runs/` remains gitignored，不提交。当前本地 viewer URL 是 `/realtime-validation-reports`，读取 `summary.json`；v1 没有 public sharing/auth。

### 5. 浏览器音频自动化

`--use-file-for-fake-audio-capture` 在当前环境不稳定。需要真实语音验证时，可以使用用户麦克风或用户手机播放测试音频辅助。

## 快速启动清单

新需求开局直接执行：

```bash
git switch main
git pull --ff-only
git status --short --branch
```

然后从 `main` 新建 feature branch，按项目规则走：

```text
spec/tasks -> implementation/tests -> $gstack-review -> PR/merge -> post-merge archive
```
