# VoiceAgents 真实语音接入 MVP Spec

Status: DRAFT
Branch: `feat/openai-realtime-voice-mvp`
Date: 2026-05-30
Primary provider in this phase: OpenAI Realtime

## 目标

实现 VoiceAgents 的第一个真实浏览器语音闭环 MVP。

本阶段使用 OpenAI Realtime 作为第一个真实语音模型 provider，但实现不能锁死在 OpenAI。业务工具调用、会话状态、transcript、事件日志、安全边界必须通过 VoiceAgents 内部抽象表达，后续应能新增 DashScope、火山云或其他语音模型 provider，而不是重写订单、物流、商品知识、转人工等业务层。

## 背景

VoiceAgents 已有文本智能客服 SaaS 和上一阶段的 browser/local realtime plumbing：

- `/realtime-test`
- mock realtime provider
- session-bound `tool_call_token`
- `/v1/realtime/tool-call`
- JSONL event log
- redaction
- smoke tests

当前缺口是浏览器还不能用麦克风连接真实语音模型，不能完成真实语音输入、模型语音输出、Realtime 事件监听、工具调用回传和脱敏 transcript 记录。

本阶段先服务研发测试。研发验证基本稳定后，再给商家和客服试用。

## 已验证当前状态

验证日期：2026-05-30

| 模块 | 当前状态 | 缺口 |
|---|---|---|
| `voiceagents/realtime/providers.py` | 已有 `RealtimeProvider`、`MockRealtimeProvider`、`OpenAIRealtimeProvider` 边界 | `OpenAIRealtimeProvider` 还没有真实调用 OpenAI |
| `voiceagents/api/app.py` | `/v1/realtime/client-secret` 会创建本地 session、生成 `tool_call_token`、写 `session_created` | 真实 provider 下还不能返回 OpenAI ephemeral client secret |
| `voiceagents/api/static/realtime-test.html` | 有 Start/Stop/Mute、session panel、tool relay | 没有 `getUserMedia`、`RTCPeerConnection`、远端音频播放 |
| `voiceagents/realtime/tool_router.py` | 已支持订单、物流、商品知识、转人工工具路由 | 需要被浏览器 data channel 事件触发 |
| `voiceagents/realtime/event_log.py` | 已写 JSONL，已过滤 `raw_audio`、`client_secret`、`tool_call_token`、`authorization` | 需要结构化事件和脱敏 transcript 记录 |
| `voiceagents/realtime/redaction.py` | 已支持邮箱、电话、订单号等脱敏 | 需要覆盖 transcript JSONL |

## OpenAI API 依据

本阶段使用 OpenAI 官方 Realtime WebRTC 路径：

- 浏览器/移动端直接采集和播放音频时，OpenAI 推荐使用 WebRTC。
- 标准 OpenAI API key 只能在服务端使用，不能暴露到浏览器。
- 浏览器可以使用服务端创建的 ephemeral client secret 连接 Realtime。
- WebRTC 连接使用 `/v1/realtime/calls`。
- client secret 通过 `/v1/realtime/client_secrets` 创建。

参考：

- https://developers.openai.com/api/docs/guides/realtime
- https://developers.openai.com/api/docs/guides/realtime-webrtc
- https://developers.openai.com/api/docs/guides/voice-agents
- https://api.openai.com/v1/realtime/client_secrets
- https://api.openai.com/v1/realtime/calls

## 产品范围

本阶段必须完成：

1. 浏览器麦克风输入。
2. OpenAI Realtime WebRTC 连接。
3. 浏览器播放模型语音输出。
4. Realtime data channel 事件监听。
5. 订单、物流、商品知识、转人工四类工具调用。
6. 工具结果回传给 OpenAI Realtime。
7. 结构化事件 JSONL。
8. 脱敏逐字 transcript JSONL。
9. 3 分钟连续语音会话验证。

## 非目标

本阶段不做：

- telephony。
- Twilio。
- SIP。
- 真实电话呼入。
- 真实电话呼出。
- 保存 raw audio。
- 保存未脱敏 transcript。
- 接入现有 SaaS 商家配置。
- 接入知识库后台配置。
- 接入客服后台。
- 生产级权限体系。
- 商家可配置 retention policy。
- 长期 transcript 查询 UI。
- 数据库持久化。
- 多租户生产审计后台。

## 架构原则

### Provider-neutral core

OpenAI Realtime 是本阶段第一个真实 provider，但 VoiceAgents 的核心业务层不能依赖 OpenAI 专有事件名。

必须保留并强化以下分层：

```text
Browser / provider adapter
  -> provider-specific WebRTC and data-channel events
  -> normalized VoiceAgents realtime events
  -> /v1/realtime/tool-call
  -> business adapters
  -> normalized tool result
  -> provider adapter sends result back to model
```

后续接入 DashScope、火山云或其他 provider 时，应新增 provider adapter，而不是修改业务工具实现。

### Provider-specific adapter

每个 provider 可以有自己的：

- credential creation request。
- WebRTC 或 WebSocket 连接方式。
- data channel / event stream 事件名。
- tool call event shape。
- transcript event shape。
- voice/model 参数。

但必须映射到 VoiceAgents 内部统一模型：

- `VoiceSessionState`
- `VoiceEvent`
- transcript event
- tool call request
- tool call response
- handoff event
- error event

### Tool boundary

provider 不执行业务工具。工具执行只能通过 VoiceAgents backend：

- `/v1/realtime/tool-call`
- `Authorization: Bearer <tool_call_token>`
- `RealtimeToolRouter`
- Pydantic 参数校验
- tool allowlist
- safe summary

### Secret boundary

浏览器可以持有：

- OpenAI ephemeral client secret。
- VoiceAgents session-bound `tool_call_token`。

浏览器不能持有：

- `OPENAI_API_KEY`
- 任何标准 provider API key

日志不能保存：

- `OPENAI_API_KEY`
- `client_secret`
- `tool_call_token`
- `authorization`
- SDP payload
- raw audio
- audio bytes

## 连接方式与职责边界

本阶段使用 ephemeral token 模式：

1. 浏览器请求 `POST /v1/realtime/client-secret`。
2. 后端使用 `OPENAI_API_KEY` 调用 OpenAI `POST /v1/realtime/client_secrets`。
3. 后端返回 OpenAI ephemeral client secret 和 VoiceAgents 本地 `tool_call_token`。
4. 浏览器创建 `RTCPeerConnection`。
5. 浏览器通过 `navigator.mediaDevices.getUserMedia({ audio: true })` 获取麦克风。
6. 浏览器创建 `oai-events` data channel。
7. 浏览器创建 SDP offer。
8. 浏览器用 ephemeral client secret 调 OpenAI `POST /v1/realtime/calls`。
9. 浏览器设置 SDP answer。
10. 浏览器播放远端 audio track。

职责边界：

- `OpenAIRealtimeProvider` 只负责创建 OpenAI ephemeral client secret。
- 浏览器负责使用 ephemeral client secret 创建 WebRTC call，即调用 OpenAI `/v1/realtime/calls`。
- VoiceAgents 后端不代理 SDP，不进入媒体链路。
- VoiceAgents 后端仍负责本地 session、`tool_call_token`、工具调用、事件日志和 transcript 日志。
- 如果未来 provider 不支持浏览器 WebRTC，应新增 provider-specific connection adapter，不改变业务工具边界。

## Backend 变更

### `OpenAIRealtimeProvider`

修改 `voiceagents/realtime/providers.py`。

必须行为：

- 缺少 `OPENAI_API_KEY` 时返回明确 503，不创建本地 session。
- 调用 `POST https://api.openai.com/v1/realtime/client_secrets`。
- 标准 OpenAI API key 只在服务端使用。
- 如果 `request.safety_subject_id` 存在，服务端请求包含 `OpenAI-Safety-Identifier`。
- 返回 OpenAI response 中的 ephemeral `value`。
- 解析 OpenAI response 中的 `expires_at`。
- 返回本地 session 的 `tool_call_token`，而不是 OpenAI credential。
- 不记录 OpenAI request/response 中的 secret。

`POST /v1/realtime/client-secret` response shape 保持现有 `RealtimeClientSecretResponse`：

```json
{
  "provider": "openai_realtime",
  "session_id": "session-...",
  "call_id": "call-...",
  "client_secret": "ephemeral-secret-from-provider",
  "tool_call_token": "voiceagents-local-token",
  "connection_url": "https://api.openai.com/v1/realtime/calls",
  "expires_at": "provider-expiry-or-null",
  "model": "gpt-realtime-2",
  "voice": "marin",
  "session_config": {
    "instructions": "...",
    "tools": []
  }
}
```

规则：

- `client_secret` 是 provider ephemeral secret，只返回给浏览器一次。
- `tool_call_token` 是 VoiceAgents 本地 relay token，只用于 `/v1/realtime/tool-call` 和 `/v1/realtime/event`。
- `connection_url` 对 OpenAI provider 固定为 `https://api.openai.com/v1/realtime/calls`。
- `OPENAI_API_KEY` 永远不出现在 response body、日志或浏览器 DOM。

默认配置：

```text
VOICEAGENTS_REALTIME_PROVIDER=mock|openai_realtime
OPENAI_API_KEY=<server-only>
VOICEAGENTS_OPENAI_REALTIME_MODEL=gpt-realtime-2
VOICEAGENTS_OPENAI_REALTIME_VOICE=marin
VOICEAGENTS_TRANSCRIPT_LOGGING=off|structured|transcript
```

默认值：

- 默认 `structured`。
- 研发要保存逐字 transcript 时显式设置 `VOICEAGENTS_TRANSCRIPT_LOGGING=transcript`。
- CI 和未配置环境不得默认写 transcript。

### OpenAI session config

OpenAI client secret request body 应包含：

```json
{
  "expires_after": {
    "anchor": "created_at",
    "seconds": 600
  },
  "session": {
    "type": "realtime",
    "model": "gpt-realtime-2",
    "instructions": "<DEFAULT_REALTIME_INSTRUCTIONS>",
    "audio": {
      "output": {
        "voice": "marin"
      }
    },
    "tools": [],
    "tool_choice": "auto"
  }
}
```

`tools` 必须由 VoiceAgents 后端 allowlist 生成，不能在浏览器硬编码一份不同 schema。

工具 schema 来源：

- 以 `voiceagents/realtime/contracts.py` 中的 `build_default_realtime_session_config()` 为单一来源。
- OpenAI adapter 将 `RealtimeToolDefinition` 映射为 OpenAI function tool shape。
- 映射后每个工具必须包含 `type=function`、`name`、`description`、`parameters`。
- 测试必须断言 OpenAI request body 中的工具名集合等于 `ALLOWED_REALTIME_TOOL_NAMES`。
- 浏览器只消费后端返回的 `session_config.tools`，不能维护第二份工具 schema。

### 事件与 transcript endpoint

浏览器必须把 provider events 写入后端。本阶段新增：

```text
POST /v1/realtime/event
```

要求：

- 必须包含 `session_id`、`call_id`、`merchant_id`、`event_type`。
- 必须使用 `Authorization: Bearer <tool_call_token>`，鉴权方式与 `/v1/realtime/tool-call` 一致。
- 如果顶层 payload 或嵌套 payload 包含 blocked keys，返回 422，不写入日志。
- 必须走 redaction。
- 不能接收 raw audio。
- 不能接收 `client_secret`、`tool_call_token`、`authorization`、SDP。
- 可以写结构化 event JSONL。
- 可以写脱敏 transcript JSONL。

该 endpoint 不执行工具调用。工具调用仍只能通过 `/v1/realtime/tool-call`。

Request shape:

```json
{
  "session_id": "session-...",
  "call_id": "call-...",
  "merchant_id": "merchant-demo",
  "provider": "openai_realtime",
  "provider_event_type": "response.output_audio_transcript.delta",
  "event_type": "transcript.assistant.delta",
  "state": "transcribing",
  "speaker": "assistant",
  "turn_id": "turn-...",
  "sequence": 1,
  "text": "Where is ORDER-123456?",
  "latency_ms": 120
}
```

Response shape:

```json
{
  "ok": true,
  "event_id": "uuid",
  "redaction_applied": true
}
```

Error behavior:

- Missing or invalid bearer token: 401/403.
- Unknown session: 403.
- Blocked key present anywhere in payload: 422.
- Invalid enum/event type: 422.

## Browser 变更

修改 `voiceagents/api/static/realtime-test.html`。

必须行为：

- 保留现有研发测试面板。
- Start:
  - 创建 session ID 和 call ID。
  - 调用 `/v1/realtime/client-secret`。
  - 创建 `RTCPeerConnection`。
  - 创建远端 `<audio autoplay>`。
  - 调用 `getUserMedia({ audio: true })`。
  - 添加本地 microphone track。
  - 创建 `oai-events` data channel。
  - 创建 SDP offer。
  - 使用 OpenAI ephemeral client secret 调 `/v1/realtime/calls`。
  - 设置 remote SDP answer。
- Stop:
  - stop 本地 media tracks。
  - close data channel。
  - close peer connection。
  - 清理 JS state 中的 secrets。
- Mute:
  - toggle 本地 audio tracks 的 `enabled`。
- UI 显示：
  - session state
  - provider
  - transcript
  - assistant response
  - tool calls
  - handoff
  - latency
  - provider events
  - errors
- UI 不显示：
  - `client_secret`
  - `tool_call_token`
  - Authorization header
  - OpenAI API key

## Provider event normalization

本阶段必须定义内部 normalized event 层，避免 OpenAI 事件名污染业务层。

建议内部事件类型：

```text
session.connecting
session.connected
session.ended
session.error
transcript.user.delta
transcript.user.done
transcript.assistant.delta
transcript.assistant.done
tool_call.requested
tool_call.result
handoff.requested
response.done
```

OpenAI adapter 负责把 OpenAI provider event 映射到这些内部事件。

后续 DashScope、火山云等 provider 只需要新增 adapter，把各自事件映射到同一组内部事件。

Adapter 所属位置：

- 后端 provider adapter：`voiceagents/realtime/providers.py`，负责 provider credential creation。
- 浏览器 WebRTC adapter：`realtime-test.html` 内的 JS module/function，负责 provider data-channel event normalization 和 provider-specific result submission。
- 内部 normalized event contract：`voiceagents/realtime/contracts.py`，后端用于验证 `/v1/realtime/event` payload。
- 后续如果前端变复杂，可以把浏览器 adapter 拆到独立静态 JS 文件；本阶段不引入前端构建工具。

OpenAI adapter 至少要覆盖以下 OpenAI Realtime 事件族：

| OpenAI event family | Normalized event |
|---|---|
| session / connection ready event | `session.connected` |
| error event | `session.error` |
| user input transcript delta/done event | `transcript.user.delta` / `transcript.user.done` |
| assistant audio transcript delta/done event，例如 `response.output_audio_transcript.delta` | `transcript.assistant.delta` / `transcript.assistant.done` |
| assistant text delta event，例如 `response.output_text.delta` | `transcript.assistant.delta` |
| function/tool call completed argument event | `tool_call.requested` |
| response completion event | `response.done` |

如果 OpenAI 当前 GA 事件名和上表存在差异，实现时以官方 Realtime server/client event reference 为准，但必须通过 adapter 测试证明 provider event 没有泄露到业务工具层。

实现前必须重新核对 OpenAI 官方 Realtime event reference，并在测试 fixture 中固化本阶段使用的 OpenAI event sample。不要凭旧 beta event 名称实现。

## Tool bridge

浏览器 data channel 收到 provider tool/function call 后：

1. 解析 provider event。
2. 通过 provider adapter 映射成 `tool_call.requested`。
3. 校验 tool name 是否在 allowlist：
   - `lookup_order`
   - `lookup_logistics`
   - `query_product_knowledge`
   - `handoff_to_human`
4. 调用 `/v1/realtime/tool-call`。
5. Header 使用 `Authorization: Bearer <tool_call_token>`。
6. 收到 safe tool result。
7. 将结果通过 provider adapter 转回 provider 需要的 event shape。
8. 通过 data channel 发回 OpenAI Realtime。
9. 写结构化事件日志。

OpenAI 工具结果回传规则：

- OpenAI adapter 负责构造 OpenAI 所需的 function call output event。
- function call output 的 `output` 必须使用 `RealtimeToolCallResponse.safe_summary` 和必要的 safe result 字段。
- 不得把未脱敏 arguments、`tool_call_token`、Authorization header 或 raw backend response 写回 provider。
- 工具结果回传后，如 OpenAI 需要显式继续生成 response，adapter 负责发送对应 client event。
- 这些 OpenAI-specific event shape 只能存在于 adapter/browser 连接层，不能进入 `RealtimeToolRouter`。

## Transcript 与事件日志

本阶段保存：

- 结构化事件 JSONL。
- 脱敏逐字 transcript JSONL。

本阶段不保存：

- raw audio。
- 未脱敏 transcript。
- SDP。
- provider API key。
- client secret。
- tool token。
- Authorization header。

建议文件：

```text
.voiceagents/events/realtime-events.jsonl
.voiceagents/transcripts/realtime-transcripts.jsonl
```

`.voiceagents/` 必须保持 gitignored。

`VOICEAGENTS_TRANSCRIPT_LOGGING` 模式：

| 模式 | 行为 |
|---|---|
| `off` | 不写 transcript JSONL；仍可写必要结构化事件 JSONL |
| `structured` | 只写结构化事件 JSONL，不写逐字 transcript |
| `transcript` | 写结构化事件 JSONL，并写脱敏逐字 transcript JSONL |

默认值：

- 默认 `structured`。
- 本地研发要保存逐字 transcript 时显式设置 `VOICEAGENTS_TRANSCRIPT_LOGGING=transcript`。
- `transcript` 模式只保存脱敏文本，不保存未脱敏文本。

逐字 transcript 语义：

- `delta` 事件可以逐条写入，便于调试流式识别。
- 每个 user/assistant turn 必须在 `done` 事件写入一条完整脱敏文本。
- “完整逐字”以每个 turn 的 `done.text_redacted` 为准。
- 如果 provider 只提供 delta，不提供 done，实现必须在 adapter 内按 turn 聚合，并在 turn 结束时写 `transcript_done`。
- transcript 写入前必须脱敏；禁止先写原文再异步脱敏。

Transcript JSONL shape：

```json
{
  "event_id": "uuid",
  "timestamp": "2026-05-30T00:00:00Z",
  "session_id": "session-...",
  "call_id": "call-...",
  "merchant_id": "merchant-demo",
  "speaker": "user",
  "event_type": "transcript_delta",
  "turn_id": "turn-...",
  "sequence": 1,
  "text_redacted": "Where is [ORDER_REDACTED]?",
  "provider": "openai_realtime",
  "provider_event_type": "response.output_audio_transcript.delta",
  "redaction_applied": true
}
```

## 验收标准

1. `VOICEAGENTS_REALTIME_PROVIDER=mock` 时，现有 realtime tests 和 smoke scripts 继续通过。
2. `VOICEAGENTS_REALTIME_PROVIDER=openai_realtime` 且 `OPENAI_API_KEY` 有效时，`/v1/realtime/client-secret` 返回 OpenAI ephemeral client secret 和本地 `tool_call_token`。
3. `/realtime-test` 可以建立 OpenAI Realtime WebRTC session。
4. 浏览器可以采集麦克风输入。
5. 浏览器可以播放模型语音输出。
6. 可以完成 3 分钟连续语音会话，页面不刷新，后端不崩溃。
7. 可以触发并完成订单、物流、商品知识、转人工四类工具调用。
8. 工具结果可以通过 data channel 回传给 OpenAI Realtime。
9. 可以写结构化事件 JSONL。
10. 可以写脱敏 transcript JSONL。
11. JSONL 中没有 raw audio、未脱敏 transcript、OpenAI API key、client secret、tool token、Authorization header、SDP。
12. OpenAI provider-specific events 被隔离在 adapter 层，业务工具层不依赖 OpenAI 事件名。
13. 本阶段不接 telephony、真实电话、SaaS 商家配置、知识库后台、客服后台。
14. `/v1/realtime/event` 可以记录结构化事件和脱敏 transcript，并拒绝 blocked keys。
15. 自动化测试不依赖真实 OpenAI key；真实 OpenAI 3 分钟会话作为手动验收。
16. `/v1/realtime/event` 使用 bearer `tool_call_token` 鉴权，不能匿名写日志。
17. `VOICEAGENTS_TRANSCRIPT_LOGGING` 未配置时不写 transcript JSONL。

## 测试计划

| 层级 | 内容 | 数量 |
|---|---|---|
| Unit | OpenAI provider 配置、request construction、missing key | +4 |
| Unit | provider event normalization | +4 |
| Unit | transcript redaction JSONL repository | +4 |
| Unit | event logging blocked keys，覆盖 SDP/secrets/audio | +3 |
| API | `/v1/realtime/client-secret` mock OpenAI HTTP response | +3 |
| API | `/v1/realtime/event` validation/logging | +3 |
| Static/UI | `/realtime-test` 包含 WebRTC/data channel hooks，不渲染 secrets | +3 |
| Smoke | mock realtime smoke 继续通过 | existing |
| Manual | OpenAI real-mode 3 分钟浏览器语音会话 | +1 checklist |

## 回滚方案

- 设置 `VOICEAGENTS_REALTIME_PROVIDER=mock` 关闭真实 OpenAI Realtime。
- 设置 `VOICEAGENTS_TRANSCRIPT_LOGGING=off` 关闭 transcript 日志。
- 如果 WebRTC 页面变更有问题，回滚本 PR。
- 既有文本 SaaS 智能客服不受影响，因为本阶段不接 SaaS 商家配置、知识库后台、客服后台或 telephony。

## 工作量估计

| 模块 | 估计 |
|---|---|
| Provider + config | 1.5-2h |
| Provider event normalization | 1-2h |
| Browser WebRTC + data channel | 3-5h |
| Tool bridge | 2-3h |
| Transcript/event logging | 2-3h |
| Tests | 2-3h |
| README/smoke/manual checklist | 1-2h |

总计：约 12.5-20h。

## 文件参考

| 文件 | 变更 |
|---|---|
| `voiceagents/realtime/providers.py` | 接入 OpenAI client secret creation |
| `voiceagents/realtime/contracts.py` | 增加 transcript/event/provider normalization contracts |
| `voiceagents/realtime/event_log.py` | 扩展 structured event 与 transcript logging |
| `voiceagents/realtime/redaction.py` | 复用或扩展 transcript redaction |
| `voiceagents/api/app.py` | 新增 `/v1/realtime/event` |
| `voiceagents/api/static/realtime-test.html` | 增加 WebRTC microphone/audio/data-channel flow |
| `scripts/smoke_realtime_api.py` | 保持 mock smoke；补充 real-mode manual checklist |
| `tests/` | 增加 provider、normalization、transcript、event、API、page tests |
| `README.md` | 记录 OpenAI Realtime env vars 和手动验证步骤 |

## 后续 Provider 扩展策略

后续接 DashScope、火山云或其他语音模型 provider 时，优先新增：

```text
DashScopeRealtimeProvider
VolcRealtimeProvider
<Provider>RealtimeEventAdapter
```

而不是修改：

- `RealtimeToolRouter`
- 订单/物流/商品知识/转人工 adapters
- transcript repository
- event log repository
- session store

如果某个 provider 不支持浏览器 WebRTC，只支持服务端 WebSocket 或 SDK，则应新增独立连接 adapter，并复用同一组 normalized events 和 tool-call boundary。

## Out of Scope

- 不实现 DashScope provider。
- 不实现火山云 provider。
- 不做 provider selection UI。
- 不做多 provider fallback。
- 不做 provider cost comparison。
- 不做 telephony provider。
- 不保存 raw audio。
- 不保存未脱敏 transcript。
- 不接生产数据库。
