# VoiceAgents 真实语音接入 MVP Tasks

Status: DRAFT
Source spec: `docs/specs/voiceagents-openai-realtime-voice-mvp.md`
Branch: `feat/openai-realtime-voice-mvp`

Rules:

- 不实现 telephony、Twilio、SIP、真实电话呼入/呼出。
- 不保存 raw audio。
- 不保存未脱敏 transcript。
- 不接入现有 SaaS 商家配置、知识库后台、客服后台。
- 不提交真实 OpenAI key、真实 PII、`.voiceagents/` 本地日志。
- OpenAI 是本阶段首个真实 provider，但业务层必须保持 provider-neutral。
- 每个 task 尽量可单独 commit。
- 每个 task 必须有明确输入、输出和验证方式。
- 自动化测试不得依赖真实 `OPENAI_API_KEY`。
- 真实 OpenAI 3 分钟会话只作为手动验收。

---

## Phase 1: Contracts And Provider-Neutral Foundation

目标：先建立 provider-neutral 的内部事件、transcript、logging contract，避免后续浏览器和 OpenAI 事件名污染业务层。

### Task 1.1: Add Normalized Realtime Event Enum

Purpose: define provider-neutral event names.

Inputs:

- Source spec provider event normalization section
- Existing `voiceagents/realtime/contracts.py`

Outputs:

- Updated `voiceagents/realtime/contracts.py`
- Updated `tests/test_realtime_contracts.py`

Required outputs:

- `NormalizedRealtimeEventType`
- values include `session.connecting`, `session.connected`, `session.ended`, `session.error`, `transcript.user.delta`, `transcript.user.done`, `transcript.assistant.delta`, `transcript.assistant.done`, `tool_call.requested`, `tool_call.result`, `handoff.requested`, `response.done`

Validation:

```bash
python3 -m pytest tests/test_realtime_contracts.py
```

### Task 1.2: Add Realtime Event Ingest Contract

Purpose: encode `/v1/realtime/event` request/response shape.

Inputs:

- Source spec `/v1/realtime/event` section
- `NormalizedRealtimeEventType`
- Existing `RealtimeProviderName`
- Existing `VoiceSessionState`

Outputs:

- Updated `voiceagents/realtime/contracts.py`
- Updated `tests/test_realtime_contracts.py`

Required outputs:

- `RealtimeEventIngestRequest`
- `RealtimeEventIngestResponse`
- request forbids extra fields
- request supports `speaker`, `turn_id`, `sequence`, `text`, `latency_ms`, `provider_event_type`

Validation:

```bash
python3 -m pytest tests/test_realtime_contracts.py
```

### Task 1.3: Add Transcript Event Contract

Purpose: encode redacted transcript JSONL payload.

Inputs:

- Source spec transcript JSONL shape
- Existing redaction model

Outputs:

- Updated `voiceagents/realtime/contracts.py`
- Updated `tests/test_realtime_contracts.py`

Required outputs:

- `RealtimeTranscriptEvent`
- `speaker` limited to `user|assistant`
- `text_redacted` required and non-empty
- `turn_id` and `sequence` supported

Validation:

```bash
python3 -m pytest tests/test_realtime_contracts.py
```

### Task 1.4: Add Transcript Logging Mode Enum

Purpose: make transcript logging mode explicit and testable.

Inputs:

- Source spec `VOICEAGENTS_TRANSCRIPT_LOGGING` section

Outputs:

- Updated `voiceagents/realtime/contracts.py`
- Updated `tests/test_realtime_contracts.py`

Required outputs:

- `TranscriptLoggingMode`
- values `off`, `structured`, `transcript`
- default behavior documented in tests as `structured`

Validation:

```bash
python3 -m pytest tests/test_realtime_contracts.py
```

### Task 1.5: Add OpenAI Tool Schema Mapper Contract Tests

Purpose: prove backend tool definitions can map to provider-specific function tools.

Inputs:

- `build_default_realtime_session_config()`
- `ALLOWED_REALTIME_TOOL_NAMES`
- Source spec tool schema section

Outputs:

- New or updated mapper in `voiceagents/realtime/providers.py` or `voiceagents/realtime/contracts.py`
- Updated `tests/test_realtime_providers.py`

Required outputs:

- mapper returns tools with `type`, `name`, `description`, `parameters`
- mapped tool names equal `ALLOWED_REALTIME_TOOL_NAMES`

Validation:

```bash
python3 -m pytest tests/test_realtime_providers.py
```

---

## Phase 2: OpenAI Provider And Backend Event Ingest

目标：让后端能真实创建 OpenAI ephemeral client secret，并能安全接收浏览器 provider events。

### Task 2.1: Add OpenAI Client Secret HTTP Boundary

Purpose: isolate outbound OpenAI HTTP request construction.

Inputs:

- `OPENAI_API_KEY`
- `VOICEAGENTS_OPENAI_REALTIME_MODEL`
- `VOICEAGENTS_OPENAI_REALTIME_VOICE`
- Source spec OpenAI session config

Outputs:

- Updated `voiceagents/realtime/providers.py`
- Updated `tests/test_realtime_providers.py`

Required outputs:

- request URL `https://api.openai.com/v1/realtime/client_secrets`
- Authorization header uses server-side API key
- optional `OpenAI-Safety-Identifier`
- request body includes `expires_after`, `session.type`, `session.model`, `session.audio.output.voice`, `session.tools`, `tool_choice`

Validation:

```bash
python3 -m pytest tests/test_realtime_providers.py
```

### Task 2.2: Parse OpenAI Client Secret Response

Purpose: convert OpenAI response into existing `RealtimeClientSecretResponse`.

Inputs:

- Mock OpenAI response body
- Existing `RealtimeClientSecretRequest`

Outputs:

- Updated `OpenAIRealtimeProvider.create_client_secret()`
- Updated `tests/test_realtime_providers.py`

Required outputs:

- `client_secret` uses OpenAI `value`
- `expires_at` parsed from OpenAI response
- `connection_url` is `https://api.openai.com/v1/realtime/calls`
- `model` and `voice` reflect configured values

Validation:

```bash
python3 -m pytest tests/test_realtime_providers.py
```

### Task 2.3: Preserve Missing-Key Safe Failure

Purpose: ensure provider failure does not create local sessions.

Inputs:

- Existing missing key behavior
- `VOICEAGENTS_REALTIME_PROVIDER=openai_realtime`

Outputs:

- Updated `tests/test_api_realtime_client_secret.py`

Required outputs:

- missing `OPENAI_API_KEY` returns 503
- `InMemoryVoiceSessionStore` has no created session
- response body does not expose secrets

Validation:

```bash
python3 -m pytest tests/test_api_realtime_client_secret.py
```

### Task 2.4: Add Event Ingest Endpoint Skeleton

Purpose: expose authenticated provider event logging boundary.

Inputs:

- `RealtimeEventIngestRequest`
- `RealtimeEventIngestResponse`
- `InMemoryVoiceSessionStore`
- Existing bearer token extraction

Outputs:

- Updated `voiceagents/api/app.py`
- New or updated `tests/test_api_realtime_event.py`

Required outputs:

- `POST /v1/realtime/event`
- requires `Authorization: Bearer <tool_call_token>`
- rejects missing/malformed auth
- rejects invalid token
- returns `{ok, event_id, redaction_applied}`

Validation:

```bash
python3 -m pytest tests/test_api_realtime_event.py
```

### Task 2.5: Reject Blocked Event Keys

Purpose: prevent secrets, SDP, and audio payloads from entering logs.

Inputs:

- Source spec blocked keys
- Existing `BLOCKED_EVENT_KEYS`

Outputs:

- Updated `voiceagents/realtime/event_log.py` or validation helper
- Updated `tests/test_api_realtime_event.py`
- Updated `tests/test_realtime_event_log.py`

Required outputs:

- blocked top-level keys return 422
- blocked nested keys return 422
- keys include `raw_audio`, `audio`, `audio_bytes`, `client_secret`, `tool_call_token`, `authorization`, `sdp`

Validation:

```bash
python3 -m pytest tests/test_api_realtime_event.py tests/test_realtime_event_log.py
```

---

## Phase 3: Transcript And Structured Logging

目标：保存结构化事件和脱敏逐字 transcript，但不保存 raw audio 或未脱敏文本。

### Task 3.1: Add Transcript JSONL Repository

Purpose: append redacted transcript lines to `.voiceagents/transcripts/`.

Inputs:

- `RealtimeTranscriptEvent`
- Existing `Redactor`

Outputs:

- Updated or new repository in `voiceagents/realtime/event_log.py`
- New `tests/test_realtime_transcript_log.py`

Required outputs:

- default path `.voiceagents/transcripts/realtime-transcripts.jsonl`
- writes one JSON object per line
- creates parent directory

Validation:

```bash
python3 -m pytest tests/test_realtime_transcript_log.py
```

### Task 3.2: Redact Transcript Before Write

Purpose: prevent unredacted transcript persistence.

Inputs:

- Email, phone, order-like sample transcript
- Existing `redact_mapping`

Outputs:

- Updated transcript repository
- Updated `tests/test_realtime_transcript_log.py`

Required outputs:

- transcript text redacted before write
- `redaction_applied` true when redaction occurs
- raw text absent from file content

Validation:

```bash
python3 -m pytest tests/test_realtime_transcript_log.py
```

### Task 3.3: Enforce Transcript Logging Modes

Purpose: make `VOICEAGENTS_TRANSCRIPT_LOGGING` behavior deterministic.

Inputs:

- `TranscriptLoggingMode`
- Environment variable `VOICEAGENTS_TRANSCRIPT_LOGGING`

Outputs:

- Mode resolver in app or realtime module
- Updated `tests/test_api_realtime_event.py`

Required outputs:

- unset resolves to `structured`
- `off` writes no transcript JSONL
- `structured` writes no transcript JSONL
- `transcript` writes transcript JSONL
- structured event JSONL still works for `structured` and `transcript`

Validation:

```bash
python3 -m pytest tests/test_api_realtime_event.py
```

### Task 3.4: Write Transcript Done Events

Purpose: persist complete per-turn transcript text.

Inputs:

- `RealtimeEventIngestRequest` with `event_type=transcript.user.done`
- `RealtimeEventIngestRequest` with `event_type=transcript.assistant.done`

Outputs:

- Updated event ingest handler
- Updated `tests/test_api_realtime_event.py`

Required outputs:

- writes `RealtimeTranscriptEvent` for user done
- writes `RealtimeTranscriptEvent` for assistant done
- includes `turn_id`, `sequence`, `provider_event_type`

Validation:

```bash
python3 -m pytest tests/test_api_realtime_event.py
```

### Task 3.5: Preserve Structured VoiceEvent Logging

Purpose: keep existing event log behavior while adding transcript logging.

Inputs:

- Existing `JsonlVoiceEventRepository`
- Event ingest requests

Outputs:

- Updated event ingest handler
- Updated `tests/test_api_realtime_event.py`

Required outputs:

- session/tool/error events write structured VoiceEvent JSONL
- transcript events may also write structured VoiceEvent JSONL
- event log never includes secrets, SDP, audio bytes, or raw audio

Validation:

```bash
python3 -m pytest tests/test_api_realtime_event.py tests/test_realtime_event_log.py
```

---

## Phase 4: Browser WebRTC And Tool Bridge

目标：让 `/realtime-test` 能创建真实 OpenAI WebRTC 会话，监听 data channel，调用后端工具，并把结果回传给 OpenAI。

### Task 4.1: Add Browser Realtime State Object

Purpose: keep WebRTC resources and secrets out of DOM.

Inputs:

- Existing `realtime-test.html`

Outputs:

- Updated `voiceagents/api/static/realtime-test.html`
- Updated `tests/test_api_realtime_test_page.py`

Required outputs:

- state tracks peer connection, data channel, local stream, remote audio, session IDs, token values
- `client_secret` and `tool_call_token` are never written to visible DOM

Validation:

```bash
python3 -m pytest tests/test_api_realtime_test_page.py
```

### Task 4.2: Add Microphone And Remote Audio Setup

Purpose: wire browser audio capture and playback.

Inputs:

- Browser `navigator.mediaDevices.getUserMedia`
- Existing Start/Stop/Mute controls

Outputs:

- Updated `realtime-test.html`
- Updated `tests/test_api_realtime_test_page.py`

Required outputs:

- calls `getUserMedia({ audio: true })`
- adds microphone track to `RTCPeerConnection`
- creates autoplay remote audio element
- Stop closes tracks
- Mute toggles local track `enabled`

Validation:

```bash
python3 -m pytest tests/test_api_realtime_test_page.py
```

### Task 4.3: Add OpenAI WebRTC Call Creation

Purpose: use ephemeral client secret to create OpenAI `/v1/realtime/calls`.

Inputs:

- `client_secret` from `/v1/realtime/client-secret`
- `connection_url`
- Browser SDP offer

Outputs:

- Updated `realtime-test.html`
- Updated `tests/test_api_realtime_test_page.py`

Required outputs:

- creates SDP offer
- posts SDP to `connection_url`
- uses `Authorization: Bearer <client_secret>`
- uses `Content-Type: application/sdp`
- sets remote SDP answer
- does not log/render client secret

Validation:

```bash
python3 -m pytest tests/test_api_realtime_test_page.py
```

### Task 4.4: Add Browser Provider Event Normalizer

Purpose: map OpenAI data-channel events to normalized events.

Inputs:

- Source spec event mapping table
- OpenAI event fixture samples

Outputs:

- JS normalizer in `realtime-test.html`
- Updated `tests/test_api_realtime_test_page.py`

Required outputs:

- maps transcript delta/done events
- maps tool call requested event
- maps response done
- maps error
- normalized event names match backend contract

Validation:

```bash
python3 -m pytest tests/test_api_realtime_test_page.py
```

### Task 4.5: Relay Normalized Events To Backend

Purpose: persist provider lifecycle and transcript events.

Inputs:

- Normalized browser events
- `/v1/realtime/event`
- `tool_call_token`

Outputs:

- Updated `realtime-test.html`
- Updated `tests/test_api_realtime_test_page.py`

Required outputs:

- posts normalized events to backend
- uses bearer `tool_call_token`
- never sends `client_secret`, SDP, audio, or raw audio bytes

Validation:

```bash
python3 -m pytest tests/test_api_realtime_test_page.py
```

### Task 4.6: Relay Tool Calls To Backend

Purpose: connect OpenAI tool call events to existing tool router.

Inputs:

- OpenAI tool call event sample
- Existing `relayToolCall`
- `/v1/realtime/tool-call`

Outputs:

- Updated `realtime-test.html`
- Updated `tests/test_api_realtime_test_page.py`

Required outputs:

- extracts tool name and JSON arguments
- calls `/v1/realtime/tool-call`
- shows safe summary in Tool Calls panel
- handoff result updates Handoff panel

Validation:

```bash
python3 -m pytest tests/test_api_realtime_test_page.py
```

### Task 4.7: Send Tool Results Back To OpenAI

Purpose: complete provider tool loop.

Inputs:

- `RealtimeToolCallResponse`
- OpenAI call id/item id from provider event
- data channel

Outputs:

- Updated OpenAI browser adapter in `realtime-test.html`
- Updated `tests/test_api_realtime_test_page.py`

Required outputs:

- sends provider-specific function call output event
- output uses `safe_summary` and safe result fields
- sends continue/response event if required by OpenAI GA flow
- does not send token, auth header, raw backend response, or unredacted arguments

Validation:

```bash
python3 -m pytest tests/test_api_realtime_test_page.py
```

---

## Phase 5: Verification, Docs, And Manual Real-Mode Checklist

目标：把 mock 自动化验证、真实 OpenAI 手动验收和文档收口补齐。

### Task 5.1: Update README Env Vars

Purpose: document how to run mock and real provider modes.

Inputs:

- Source spec config section
- Existing README realtime section

Outputs:

- Updated `README.md`

Required outputs:

- documents `VOICEAGENTS_REALTIME_PROVIDER`
- documents `OPENAI_API_KEY`
- documents `VOICEAGENTS_OPENAI_REALTIME_MODEL`
- documents `VOICEAGENTS_OPENAI_REALTIME_VOICE`
- documents `VOICEAGENTS_TRANSCRIPT_LOGGING`
- states OpenAI key is server-only

Validation:

```bash
rg -n "VOICEAGENTS_REALTIME_PROVIDER|OPENAI_API_KEY|VOICEAGENTS_TRANSCRIPT_LOGGING" README.md
```

### Task 5.2: Add Real-Mode Manual Checklist

Purpose: make 3-minute OpenAI verification reproducible.

Inputs:

- Source spec acceptance criteria

Outputs:

- Updated `README.md` or new `docs/specs/voiceagents-openai-realtime-voice-mvp-manual-checklist.md`

Required outputs:

- start API command
- open `/realtime-test`
- grant microphone permission
- complete 3-minute voice session
- trigger four tools
- verify JSONL contains redacted events/transcripts
- verify JSONL does not contain secrets, SDP, raw audio, or unredacted transcript

Validation:

```bash
rg -n "3 分钟|/realtime-test|raw audio|tool_call_token|client_secret" README.md docs/specs
```

### Task 5.3: Update Realtime Smoke Expectations

Purpose: preserve mock-mode smoke while real mode remains manual.

Inputs:

- Existing `scripts/smoke_realtime_api.py`
- Existing smoke docs

Outputs:

- Updated smoke script or docs
- Updated tests if examples are parsed

Required outputs:

- mock smoke still validates health, client-secret, tool-call, unknown tool, missing auth
- no real OpenAI key required
- real-mode checklist documented separately

Validation:

```bash
python3 scripts/smoke_realtime_api.py
```

### Task 5.4: Run Focused Realtime Tests

Purpose: verify changed realtime surface.

Inputs:

- Phase 1-4 implementation

Outputs:

- Test evidence

Validation:

```bash
python3 -m pytest tests/test_realtime_contracts.py tests/test_realtime_providers.py tests/test_api_realtime_client_secret.py tests/test_api_realtime_event.py tests/test_realtime_event_log.py tests/test_realtime_transcript_log.py tests/test_api_realtime_test_page.py tests/test_api_realtime_tool_call.py
```

### Task 5.5: Run Full Test Suite

Purpose: catch regressions outside realtime.

Inputs:

- All implementation changes

Outputs:

- Full test evidence

Validation:

```bash
python3 -m pytest
```

### Task 5.6: Run Manual OpenAI Realtime Verification

Purpose: prove real voice loop works with provider credentials.

Inputs:

- Valid `OPENAI_API_KEY`
- Browser with microphone permission
- API running with `VOICEAGENTS_REALTIME_PROVIDER=openai_realtime`
- Manual checklist from Task 5.2

Outputs:

- Manual verification notes
- Evidence that four tools can be triggered
- Evidence that logs are redacted and contain no blocked data

Validation:

```text
Manual pass/fail checklist recorded in PR notes.
```

### Task 5.7: Run Pre-Merge Review

Purpose: satisfy project workflow before merging.

Inputs:

- Completed implementation branch
- Passing focused/full tests

Outputs:

- `$gstack-review` findings or clean result

Validation:

```text
$gstack-review completed on feature branch before merge.
```
