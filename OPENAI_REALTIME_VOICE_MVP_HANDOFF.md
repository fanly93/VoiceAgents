# OpenAI Realtime 真实语音接入 MVP 交接文档

更新时间：2026-05-30

## 当前任务

当前正在推进 VoiceAgents 下一阶段任务：OpenAI Realtime 真实语音接入 MVP。

目标是在现有文本智能客服和上一阶段 browser/local realtime plumbing 基础上，做一个研发测试可用的真实语音 MVP：

- 浏览器麦克风输入。
- OpenAI Realtime WebRTC 真实语音会话。
- 浏览器播放模型语音输出。
- 使用现有 `tool_call_token` / tool relay 执行订单、物流、商品知识、转人工工具。
- 保存结构化事件 JSONL 和脱敏 transcript JSONL。
- 不接电话供应商，不接真实电话，不存 raw audio，不接 SaaS 商家配置/知识库后台/客服后台。

## 当前 Git 状态

当前分支：

```bash
feat/openai-realtime-voice-mvp
```

当前工作区状态：

```bash
git status --short --branch
# ## feat/openai-realtime-voice-mvp
```

工作区干净。

最近相关提交：

```bash
8dff895 docs: review openai realtime voice mvp plan
fc66a87 docs: task openai realtime voice mvp
346b09c docs: spec openai realtime voice mvp
6bc1b56 Merge pull request #3 from fanly93/docs/gstack-review-before-merge
```

本阶段目前只完成了 spec、tasks、autoplan/review 文档，没有开始代码实现。

## 重要项目规范

本项目使用项目级 gstack，规则在 `AGENTS.md`。

关键点：

- 使用 `.agents/skills/` 下的项目级 gstack。
- 优先使用 `$gstack-office-hours`、`$gstack-browse`、`$gstack-qa`、`$gstack-review`、`$gstack-autoplan`。
- 不要调用根 `$gstack`。
- 每个新需求必须从干净 `main` 新建 feature branch。
- `$gstack-review` 要在 feature branch 合并前运行；在 `main` 上运行会因为没有分支 diff 而失去 review 意义。
- 手动运行 gstack 命令时使用项目级环境：

```bash
env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" <gstack-command>
```

## 已完成内容

### 1. 已完成 spec

文件：

```text
docs/specs/voiceagents-openai-realtime-voice-mvp.md
```

状态：

```text
Status: DRAFT
```

主要内容：

- 明确本阶段使用 OpenAI Realtime 作为第一个真实语音 provider。
- 明确不能把核心业务逻辑锁死到 OpenAI。
- 明确 provider-neutral core：
  - 后端 provider adapter 只负责 credential creation。
  - 浏览器 WebRTC adapter 负责 provider event normalization、provider-specific result submission、turn 聚合。
  - 业务工具仍通过现有 `RealtimeToolRouter`。
- 明确 `/v1/realtime/client-secret` 返回 OpenAI ephemeral client secret 和本地 `tool_call_token`。
- 明确新增 `/v1/realtime/event`，用于浏览器写入 provider events / transcript events。
- 明确 `tool_call_token` 必须绑定 `session_id`、`call_id`、`merchant_id`、`provider`。
- 明确所有日志禁止保存：
  - raw audio
  - audio bytes
  - SDP
  - OpenAI API key
  - client secret
  - tool token
  - Authorization header
  - 未脱敏 transcript
  - 未脱敏 tool arguments
- 明确 `VOICEAGENTS_TRANSCRIPT_LOGGING=off|structured|transcript`：
  - 默认 `structured`
  - `off` 不写 transcript text
  - `structured` 只写结构化事件，可写 `text_redacted`
  - `transcript` 写结构化事件和脱敏 transcript JSONL
- 明确真实 provider 开发端点必须加 gate：
  - `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=false|true`
  - 默认 `false`
  - 未开启时真实 provider client-secret endpoint 返回 403，不调用 OpenAI，不创建 session
  - 仅本地研发/内网测试，不是生产鉴权方案
- 明确后续 DashScope、火山云扩展方式：
  - 新增 `<Provider>RealtimeProvider`
  - 新增 `<Provider>RealtimeEventAdapter`
  - 不改 `RealtimeToolRouter`、业务 adapter、transcript repository、event log repository、session store

### 2. 已完成 tasks 拆分

文件：

```text
docs/specs/voiceagents-openai-realtime-voice-mvp-tasks.md
```

状态：

```text
Status: DRAFT
```

共 5 个 phase：

1. Phase 1: Contracts And Provider-Neutral Foundation
2. Phase 2: OpenAI Provider And Backend Event Ingest
3. Phase 3: Transcript And Structured Logging
4. Phase 4: Browser WebRTC And Tool Bridge
5. Phase 5: Verification, Docs, And Manual Real-Mode Checklist

每个 task 都写了：

- Purpose
- Inputs
- Outputs
- Required outputs
- Validation

后续实现应严格按该 task 文档逐 phase、逐 task 执行；每个 task 尽量单独 commit。

### 3. 已完成 autoplan/review

文件：

```text
docs/reviews/autoplan-openai-realtime-voice-mvp-2026-05-30.md
```

状态：

```text
Status: REVIEWED_WITH_PLAN_FIXES
```

review 结论：

- 产品范围合理。
- 不接 telephony / raw audio / SaaS backend 的边界合理。
- 实现前必须强化安全边界、PII 日志边界、浏览器失败路径、provider-neutral adapter。
- 这些问题已全部转成 spec/tasks 的明确要求。

第一次 review 发现的问题已修：

- Blocking: `/v1/realtime/client-secret` 缺少真实 provider dev gate。
- Blocking: raw transcript 可能进入 structured event JSONL。
- High: raw tool arguments 可能进入日志或 DOM。
- High: WebRTC 失败路径验证不足。
- High: OpenAI adapter 放在 HTML 内会削弱 provider-neutral 架构。
- Medium: `/v1/realtime/event` token/session/call/merchant/provider 绑定不明确。
- Medium: OpenAI GA event correctness 没有独立任务。

第二次独立 review 结论：

- No blocking findings found。
- 发现 2 个 high 和 3 个 medium/low，已修：
  - `RealtimeEventIngestRequest` 增加 tool event 安全字段：`tool_name`、`provider_call_id`、`tool_status`、`safe_summary`。
  - Task 4.7 改为更新 `voiceagents/api/static/realtime-openai-adapter.js`，`realtime-test.html` 只做 wiring。
  - 移除 `.gstack` restore 注释，避免本地工具状态进入 spec package。
  - Task 5.6 补充 `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true`。
  - review artifact 已加入 git 并提交。

## 当前明确未完成内容

还没有进入代码实现阶段。以下都未完成：

- 没有实现 `OpenAIRealtimeProvider` 的真实 OpenAI client secret HTTP 调用。
- 没有实现 `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS` gate。
- 没有实现 `/v1/realtime/event`。
- 没有实现 token/session/call/merchant/provider mismatch 校验。
- 没有实现 transcript JSONL repository。
- 没有实现 structured event JSONL 的 raw text / raw tool arguments 清洗。
- 没有新增 `voiceagents/api/static/realtime-openai-adapter.js`。
- 没有改 `/realtime-test` 接入真实 WebRTC。
- 没有新增 OpenAI Realtime event fixtures。
- 没有补 README real-mode 文档。
- 没有跑实现相关测试。
- 没有做真实 OpenAI 3 分钟手动验证。
- 没有 push / PR / merge。

## 当前阶段边界

当前阶段必须做：

- 浏览器 WebRTC + OpenAI Realtime。
- 后端创建 OpenAI ephemeral client secret。
- 浏览器用 ephemeral secret 调 OpenAI `/v1/realtime/calls`。
- 浏览器 data channel 监听 provider events。
- Browser adapter 将 OpenAI events 转成内部 normalized events。
- 工具调用仍走 `/v1/realtime/tool-call`。
- 工具结果经 browser adapter 回传给 OpenAI。
- 结构化事件和脱敏 transcript JSONL。
- mock provider 自动化测试继续通过。

当前阶段明确不做：

- 不接 telephony。
- 不接 Twilio。
- 不接 SIP。
- 不做真实电话呼入/呼出。
- 不保存 raw audio。
- 不保存未脱敏 transcript。
- 不接现有 SaaS 商家配置。
- 不接知识库后台。
- 不接客服后台。
- 不接生产数据库。
- 不做生产级权限体系。
- 不实现 DashScope / 火山云真实 provider。
- 不做 provider selection UI。
- 不做 provider fallback。
- 不做 provider cost comparison。

## 下一步建议流程

按 gstack workflow，下一步不是直接开始写代码，而是先让用户确认：

1. 用户批准当前 spec / tasks / autoplan review。
2. 批准后进入代码实现阶段。
3. 严格按 `docs/specs/voiceagents-openai-realtime-voice-mvp-tasks.md` 逐 phase / 逐 task 实现。
4. 每个 task 尽量单独 commit。
5. 每个 phase 后跑对应测试。
6. Phase 5 跑 focused tests、full tests、mock smoke、manual checklist。
7. 实现完成后，在 feature branch 上运行 `$gstack-review`。
8. 修复 review findings。
9. push 分支、创建 PR、merge。

## 实现顺序建议

### Phase 1: Contracts And Provider-Neutral Foundation

先做 contracts，避免 OpenAI 事件名污染业务层。

关键 task：

- Task 1.1: Add Normalized Realtime Event Enum
- Task 1.2: Add Realtime Event Ingest Contract
- Task 1.3: Add Transcript Event Contract
- Task 1.4: Add Transcript Logging Mode Enum
- Task 1.5: Add OpenAI Tool Schema Mapper Contract Tests

重点注意：

- `RealtimeEventIngestRequest` 要支持安全 tool event 字段：
  - `tool_name`
  - `provider_call_id`
  - `tool_status`
  - `safe_summary`
- request 要 forbids extra fields。
- raw tool arguments 不进入 event ingest contract。

### Phase 2: OpenAI Provider And Backend Event Ingest

关键 task：

- Task 2.0: Gate Real Provider Dev Endpoints
- Task 2.1: Add OpenAI Client Secret HTTP Boundary
- Task 2.2: Parse OpenAI Client Secret Response
- Task 2.3: Preserve Missing-Key Safe Failure
- Task 2.4: Add Event Ingest Endpoint Skeleton
- Task 2.5: Reject Blocked Event Keys

重点注意：

- `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS` 默认 `false`。
- 未开启时真实 provider endpoint 返回 403。
- 403 不调用 OpenAI，不创建本地 session。
- `OPENAI_API_KEY` 只能在服务端使用。
- `/v1/realtime/event` 使用 bearer `tool_call_token`。
- token 必须绑定 session/call/merchant/provider。

### Phase 3: Transcript And Structured Logging

关键 task：

- Task 3.1: Add Transcript JSONL Repository
- Task 3.2: Redact Transcript Before Write
- Task 3.3: Enforce Transcript Logging Modes
- Task 3.4: Write Transcript Done Events
- Task 3.5: Preserve Structured VoiceEvent Logging
- Task 3.6: Strip Raw Text And Tool Arguments From All JSONL

重点注意：

- 不允许先写原文再异步脱敏。
- 原始 `text` 不得出现在任何 JSONL。
- `VOICEAGENTS_TRANSCRIPT_LOGGING=off` 不写 transcript text。
- `structured` 只写结构化事件，不写 transcript JSONL。
- `transcript` 写 transcript JSONL，但只写脱敏文本。
- 测试要 grep JSONL 内容，确认原始 email、phone、order id、tool arguments 都不存在。

### Phase 4: Browser WebRTC And Tool Bridge

关键 task：

- Task 4.0: Verify OpenAI Realtime Event Fixtures
- Task 4.1: Add Browser Realtime State Object
- Task 4.2: Add Microphone And Remote Audio Setup
- Task 4.3: Add OpenAI WebRTC Call Creation
- Task 4.4: Add Browser Provider Event Normalizer
- Task 4.5: Relay Normalized Events To Backend
- Task 4.6: Relay Tool Calls To Backend
- Task 4.7: Send Tool Results Back To OpenAI
- Task 4.8: Handle Browser WebRTC Error And Cleanup Paths

重点注意：

- 先核对当前 OpenAI Realtime 官方 event reference。
- fixture 输出到 `tests/fixtures/openai_realtime_events.json`。
- 新增 `voiceagents/api/static/realtime-openai-adapter.js`。
- `realtime-test.html` 只做 wiring、状态、DOM、资源生命周期。
- OpenAI-specific event shape 不进入 `RealtimeToolRouter`。
- 浏览器 DOM 不显示 token、secret、Authorization、未脱敏 transcript、raw tool arguments。
- WebRTC 错误路径要覆盖：
  - 麦克风权限拒绝
  - client-secret 失败
  - SDP exchange 失败
  - data channel close/error
  - Stop 清理
  - Mute
  - 失败后重连

### Phase 5: Verification, Docs, And Manual Real-Mode Checklist

关键 task：

- Task 5.1: Update README Env Vars
- Task 5.2: Add Real-Mode Manual Checklist
- Task 5.3: Update Realtime Smoke Expectations
- Task 5.4: Run Focused Realtime Tests
- Task 5.5: Run Full Test Suite
- Task 5.6: Run Manual OpenAI Realtime Verification
- Task 5.7: Run Browser Failure-Mode Verification
- Task 5.8: Run Pre-Merge Review

重点注意：

- 自动化测试不依赖真实 OpenAI key。
- real-mode 手动验证需要：
  - valid `OPENAI_API_KEY`
  - `VOICEAGENTS_REALTIME_PROVIDER=openai_realtime`
  - `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true`
  - browser microphone permission
- README 要明确 server-only key。
- README 要明确 real provider dev endpoint 不得公网暴露。
- mock smoke 要继续通过。

## 推荐新会话开局命令

新会话开始后先执行：

```bash
git status --short --branch
git log --oneline -5
sed -n '1,220p' AGENTS.md
sed -n '1,220p' docs/specs/voiceagents-openai-realtime-voice-mvp.md
sed -n '1,260p' docs/specs/voiceagents-openai-realtime-voice-mvp-tasks.md
sed -n '1,180p' docs/reviews/autoplan-openai-realtime-voice-mvp-2026-05-30.md
```

然后确认用户是否批准进入实现。

如果用户批准，建议先从 Task 1.1 开始，用 TDD 方式：

1. 先写/更新 contract tests。
2. 实现最小代码。
3. 跑 task 对应 pytest。
4. commit 当前 task。
5. 继续下一个 task。

## 已知验证结果

当前文档阶段已执行：

```bash
git diff --check
```

结果：通过。

还没有执行实现阶段测试，因为还未开始代码实现。

## 重要提醒

- 不要在 `main` 上继续实现。
- 当前分支就是本任务 feature branch：`feat/openai-realtime-voice-mvp`。
- 如果新会话发现不在该分支，先切回：

```bash
git switch feat/openai-realtime-voice-mvp
```

- 不要把真实 `OPENAI_API_KEY` 写入代码、README 示例实际值、日志或 JSONL。
- 不要为了测试保存 raw audio。
- 不要把未脱敏 transcript 或 raw tool arguments 写入 JSONL。
- 实现阶段如需要查 OpenAI Realtime API，必须使用官方 OpenAI docs，并确认当前 GA event names。
