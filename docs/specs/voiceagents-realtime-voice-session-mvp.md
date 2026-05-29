# VoiceAgents Realtime Voice Session MVP Spec

Status: DRAFT
Branch: `feat/voice-phase-design`
Source design: `docs/designs/voiceagents-realtime-voice-session-mvp.md`
Date: 2026-05-29

## Goal

Build the first realtime voice-session MVP for VoiceAgents without implementing production telephony.

The MVP must prove that live browser speech can drive existing business tools and enter safe handoff states. It should use OpenAI Realtime as the first real provider, but all provider-specific behavior must sit behind a provider interface so a later backend proxy, telephony adapter, or chained ASR/CallFlow/TTS route can be added without rewriting the business layer.

## Non-Goals

- No production telephony.
- No real phone numbers.
- No inbound or outbound calling.
- No Twilio or other telephony provider integration.
- No real human call transfer.
- No audio recording storage.
- No merchant-facing sales demo UI.
- No real customer PII in repo, fixtures, local logs, or tests.
- No database migration in this phase; database persistence is represented by repository interfaces only.

## Product Scope

The first version uses a minimal browser test page:

- Start/stop realtime session.
- Capture microphone input.
- Connect to OpenAI Realtime over WebRTC using backend-minted ephemeral credentials.
- Support text and voice response modes.
- Display transcript, assistant response text, session state, tool calls, handoff state, latency, and provider events.

Supported call paths:

- Order status lookup.
- Logistics tracking lookup.
- Product knowledge consultation.
- Refund/return handoff.
- Complaint handoff.
- Customer-requested-human handoff.
- Low confidence or unclear speech handoff or retry.

## Architecture

```text
Browser test page
  -> POST /v1/realtime/client-secret
  -> WebRTC connection to OpenAI Realtime
  -> receives Realtime function call events
  -> POST /v1/realtime/tool-call
  -> sends function_call_output back to Realtime

VoiceAgents backend
  -> RealtimeProvider interface
  -> OpenAIRealtimeProvider implementation
  -> VoiceSessionStore interface
  -> VoiceEventRepository interface
  -> InMemoryVoiceSessionStore
  -> JsonlVoiceEventRepository
  -> redaction hook
  -> existing CallFlowService and adapters
```

## OpenAI API Basis

The design relies on the current OpenAI Realtime guidance checked on 2026-05-29:

- Realtime sessions are intended for low-latency live audio.
- Browser/mobile clients that capture or play audio directly should use WebRTC.
- Standard OpenAI API keys must stay server-side; browsers receive ephemeral credentials or server-initialized session payloads only.
- Realtime function tools allow the application to execute business logic and return `function_call_output`.

References:

- https://developers.openai.com/api/docs/guides/realtime
- https://developers.openai.com/api/docs/guides/voice-agents
- https://developers.openai.com/api/docs/guides/realtime-webrtc
- https://developers.openai.com/api/docs/guides/realtime-mcp

## Backend Modules

Add a new package:

```text
voiceagents/realtime/
  __init__.py
  contracts.py
  providers.py
  session_store.py
  event_log.py
  redaction.py
  tool_router.py
```

`voiceagents/api/app.py` wires the new endpoints without changing existing `/health` or `/v1/calls/simulate` behavior.

## Contracts

### Enums

`VoiceSessionState`:

- `idle`
- `listening`
- `transcribing`
- `thinking`
- `tool_calling`
- `speaking`
- `handoff_pending`
- `ended`
- `error`

`ResponseMode`:

- `text`
- `voice`

`RealtimeProviderName`:

- `mock`
- `openai_realtime`

### Client Secret Request

`RealtimeClientSecretRequest`

Fields:

- `session_id: str`
- `call_id: str`
- `merchant_id: str`
- `response_mode: ResponseMode`
- `locale: str`
- `safety_subject_id: str | None`

Validation:

- required IDs must be non-empty
- response mode must be `text` or `voice`
- `safety_subject_id` must be privacy-preserving when present; do not accept raw phone, email, or customer name

### Client Secret Response

`RealtimeClientSecretResponse`

Fields:

- `provider: RealtimeProviderName`
- `session_id: str`
- `call_id: str`
- `client_secret: str | None`
- `tool_call_token: str`
- `connection_url: str | None`
- `expires_at: str | None`
- `model: str`
- `voice: str | None`

Rules:

- never return a standard OpenAI API key
- never write `client_secret` or `tool_call_token` to event logs
- `tool_call_token` is a VoiceAgents session-bound relay token, not an OpenAI credential
- mock provider may return deterministic fake credentials

### Tool Call Request

`RealtimeToolCallRequest`

Fields:

- `session_id: str`
- `call_id: str`
- `merchant_id: str`
- `tool_call_token: str`
- `tool_name: str`
- `arguments: dict[str, Any]`

Allowed tools:

- `lookup_order`
- `lookup_logistics`
- `query_product_knowledge`
- `handoff_to_human`

Rules:

- reject unknown tool names
- reject requests whose `tool_call_token` does not match the session
- validate arguments using a per-tool Pydantic schema
- do not allow callers to name Python modules, classes, import paths, files, shell commands, or arbitrary functions

### Tool Call Response

`RealtimeToolCallResponse`

Fields:

- `ok: bool`
- `tool_name: str`
- `result: dict[str, Any]`
- `safe_summary: str`
- `handoff_required: bool`
- `handoff_reason: HandoffReason`
- `error_code: ToolErrorCode | None`

Rules:

- result must contain safe fields only
- tool errors must be mapped to existing `ToolErrorCode`
- handoff paths must return handoff-safe structured output

### Voice Event

`VoiceEvent`

Fields:

- `event_id: str`
- `timestamp: str`
- `session_id: str`
- `call_id: str`
- `merchant_id: str`
- `state: VoiceSessionState`
- `event_type: str`
- `transcript_text_redacted: str | None`
- `response_text_redacted: str | None`
- `tool_name: str | None`
- `tool_arguments_redacted: dict[str, Any] | None`
- `tool_result_summary: str | None`
- `handoff_reason: HandoffReason | None`
- `latency_ms: int | None`
- `provider: RealtimeProviderName`
- `provider_event_type: str | None`
- `redaction_applied: bool`

Rules:

- no raw audio
- no phone numbers, emails, real order IDs, or unredacted PII

## Provider Abstraction

`RealtimeProvider` protocol:

- `create_client_secret(request: RealtimeClientSecretRequest) -> RealtimeClientSecretResponse`

Implementations:

- `MockRealtimeProvider`
- `OpenAIRealtimeProvider`

Configuration:

- `VOICEAGENTS_REALTIME_PROVIDER=mock|openai_realtime`
- `OPENAI_API_KEY` is required only for `openai_realtime`
- `VOICEAGENTS_OPENAI_REALTIME_MODEL`, default to a documented realtime model at implementation time
- `VOICEAGENTS_OPENAI_REALTIME_VOICE`, default configurable

The provider must not execute business tools. It only creates provider-specific session credentials or connection data.

## Tool Router

`RealtimeToolRouter` maps approved Realtime tool calls to existing backend logic.

Tool schemas:

- `lookup_order`: `order_id: str`
- `lookup_logistics`: `order_id: str`
- `query_product_knowledge`: `query: str`, `locale: str | None`
- `handoff_to_human`: `reason: HandoffReason`, `summary: str`

Execution:

- order/logistics/product calls use existing adapters and contracts
- handoff uses existing handoff contract/adapter
- unsafe or unsupported flows return structured handoff response

Do not let the model freely decide return/refund approval.

## Session Store

`VoiceSessionStore` interface:

- `create_session(...)`
- `get_session(session_id)`
- `update_state(session_id, state)`
- `append_transcript(session_id, role, text)`
- `append_tool_call(session_id, tool_name, safe_summary)`
- `mark_handoff(session_id, handoff_reason, handoff_id)`
- `end_session(session_id)`

First implementation:

- `InMemoryVoiceSessionStore`

Future implementation:

- database-backed session store using the same interface

## Event Repository

`VoiceEventRepository` interface:

- `append(event: VoiceEvent) -> None`

First implementation:

- `JsonlVoiceEventRepository`

Configuration:

- `VOICEAGENTS_EVENT_LOG_PATH`
- if unset, use a local ignored path under `.voiceagents/events/realtime-events.jsonl`

Rules:

- create parent directory if missing
- append one JSON object per line
- run redaction before writing
- never write raw audio
- never write provider client secrets or tool-call relay tokens

## Redaction

`Redactor` interface:

- `redact_text(text: str) -> RedactionResult`
- `redact_mapping(data: dict[str, Any]) -> RedactionResult`

First rules:

- redact email-like strings
- redact phone-like strings
- redact order-like IDs

Known limitation:

- customer names and addresses are not reliably detected in this phase; real pilot data remains blocked until a stricter privacy policy is designed.

## API Endpoints

### `POST /v1/realtime/client-secret`

Creates or initializes a voice session and returns provider connection data.

Test requirements:

- mock provider returns deterministic credentials
- openai provider fails clearly when `OPENAI_API_KEY` is missing
- response never includes a standard API key
- session is created in session store
- event log records session creation

### `POST /v1/realtime/tool-call`

Executes an approved tool call for a realtime session.

Test requirements:

- known tools return expected structured response
- unknown tools return 400
- invalid arguments return 422
- handoff tool sets session state to `handoff_pending`
- event log records redacted tool arguments and safe result summary

## Browser Test Page

Use a minimal static page, served by FastAPI, with vanilla HTML/CSS/JS unless implementation review finds a strong reason to introduce a frontend toolchain.

Suggested route:

- `GET /realtime-test`

Controls:

- start session
- stop session
- mute/unmute
- response mode toggle: text/voice

Visible panels:

- session state
- transcript
- assistant response
- tool calls
- handoff banner
- latency
- provider events

Hard rule:

- browser fetches ephemeral credentials from the backend
- browser never embeds or displays `OPENAI_API_KEY`

## Testing Strategy

Unit tests:

- contracts
- provider interface and mock provider
- openai provider missing-key error
- redaction rules
- session store
- JSONL event repository
- tool router allowlist and schema validation

API tests:

- `/v1/realtime/client-secret`
- `/v1/realtime/tool-call`
- `/realtime-test` serves static page

Smoke tests:

- mock realtime client-secret flow
- mock tool-call flow for order/logistics/product/handoff

Manual verification:

- with real OpenAI credentials, browser can start a Realtime session
- function calls can be relayed through backend and returned to Realtime
- handoff path enters `handoff_pending`

## Acceptance Criteria

The phase is complete when:

- all tests pass
- existing `/health` and `/v1/calls/simulate` still pass
- mock Realtime session endpoint works without OpenAI credentials
- OpenAI provider path fails safely without `OPENAI_API_KEY`
- browser test page is available locally
- tool-call endpoint executes only allowlisted tools
- event log contains redacted structured events and no raw audio
- documentation explains setup, env vars, mock mode, and real OpenAI mode

## Deferred

- production phone provider integration
- SIP/WebSocket telephony media pipeline
- real human transfer
- merchant-specific configuration UI
- database persistence implementation
- production observability dashboards
- real call recording evaluation
- full PII detection for names/addresses
