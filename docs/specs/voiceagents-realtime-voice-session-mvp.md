# VoiceAgents Realtime Voice Session MVP Spec

Status: IMPLEMENTED
Branch: `feat/voice-phase-design`
Source design: `docs/designs/voiceagents-realtime-voice-session-mvp.md`
Date: 2026-05-29
Merged PR: https://github.com/fanly93/VoiceAgents/pull/1
Merge commit: `ab79475`

## Goal

Build the first browser/local realtime plumbing MVP for VoiceAgents without implementing production telephony.

The MVP must prove that a browser test surface can initialize a realtime-like session, receive backend-generated tool definitions, relay tool calls to existing business tools, and enter safe handoff states. Provider-specific behavior sits behind a provider interface so real OpenAI Realtime WebRTC, a later backend proxy, a telephony adapter, or a chained ASR/CallFlow/TTS route can be added without rewriting the business layer.

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
- No real OpenAI Realtime WebRTC session wiring.
- No browser microphone capture or audio playback.
- No live speech-to-speech model verification.

## Product Scope

The first version uses a minimal browser test page:

- Start/stop realtime session.
- Bootstrap a browser test session through backend provider credentials.
- Use mock-mode HTTP verification for automated tests.
- Support text and voice response modes.
- Display transcript, assistant response text, session state, tool calls, handoff state, latency, and provider events.
- Use backend-generated Realtime session instructions and tool definitions.

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
  -> receives provider connection data and backend-generated session config
  -> can relay simulated Realtime function call events
  -> POST /v1/realtime/tool-call
  -> displays safe tool result or handoff state

VoiceAgents backend
  -> RealtimeProvider interface
  -> MockRealtimeProvider implementation
  -> OpenAIRealtimeProvider boundary with missing-key safe failure
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
- `session_config: RealtimeSessionConfig`

Rules:

- never return a standard OpenAI API key
- never write `client_secret` or `tool_call_token` to event logs
- `tool_call_token` is a VoiceAgents session-bound relay token, not an OpenAI credential
- `tool_call_token` must be generated with `secrets.token_urlsafe(32)` or stronger entropy
- `tool_call_token` must expire no later than the provider credential and must be invalid after session end
- when provider expiry is unavailable, `tool_call_token` must expire within 10 minutes by default
- server-side session state must store only a token hash; the plaintext token is returned once in the client-secret response and never retained
- token validation must use constant-time comparison, such as `hmac.compare_digest`
- mock provider may return deterministic fake credentials

### Realtime Session Config

`RealtimeSessionConfig`

Fields:

- `instructions: str`
- `tools: list[RealtimeToolDefinition]`

`RealtimeToolDefinition`

Fields:

- `name: str`
- `description: str`
- `parameters_schema: dict[str, Any]`

Rules:

- generated server-side from the backend tool allowlist and Pydantic schemas
- browser code must not hardcode a divergent tool schema
- tool definitions must include only the allowed tools listed in this spec
- instructions must tell the model to ask one clarification question when speech, order ID, or intent is unclear
- if the clarification still fails, the model must call `handoff_to_human` with `low_asr_confidence` or `order_id_unconfirmed`
- instructions must tell the model not to approve refunds, returns, or compensation outside backend tool results or handoff policy

### Tool Call Request

`RealtimeToolCallRequest`

HTTP authorization:

- required header: `Authorization: Bearer <tool_call_token>`
- do not accept `tool_call_token` in the JSON request body

Fields:

- `session_id: str`
- `call_id: str`
- `merchant_id: str`
- `tool_name: str`
- `arguments: dict[str, Any]`

Allowed tools:

- `lookup_order`
- `lookup_logistics`
- `query_product_knowledge`
- `handoff_to_human`

Rules:

- reject unknown tool names
- reject requests whose authorization header is missing, malformed, expired, or does not match the session
- validate arguments using a per-tool Pydantic schema
- do not allow callers to name Python modules, classes, import paths, files, shell commands, or arbitrary functions
- never write authorization header values to event logs

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
- `OpenAIRealtimeProvider` boundary with missing-key safe failure; real OpenAI session creation is deferred

Configuration:

- `VOICEAGENTS_REALTIME_PROVIDER=mock|openai_realtime`
- `OPENAI_API_KEY` is required only for `openai_realtime`
- `VOICEAGENTS_OPENAI_REALTIME_MODEL`, default configurable for the future real provider implementation
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
- `verify_tool_call_token(session_id, token)`
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
- the default `.voiceagents/` log path must stay ignored by git

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
- response includes backend-generated session instructions and tool definitions
- real OpenAI session creation remains deferred; this endpoint only verifies the provider boundary and missing-key failure path for `openai_realtime`
- session is created in session store
- event log records session creation
- event log does not contain provider credentials or `tool_call_token`

### `POST /v1/realtime/tool-call`

Executes an approved tool call for a realtime session.

Test requirements:

- known tools return expected structured response
- unknown tools return 400
- invalid arguments return 422
- missing or malformed authorization header returns 401 or 403
- wrong or expired `tool_call_token` returns 403
- handoff tool sets session state to `handoff_pending`
- event log records redacted tool arguments and safe result summary
- event log does not contain authorization header values or `tool_call_token`

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
- browser uses backend-returned `session_config.tools` and `session_config.instructions`
- browser sends the tool-call relay token only in the HTTP authorization header
- browser never embeds or displays `OPENAI_API_KEY`
- browser never writes `client_secret` or `tool_call_token` into visible event panels

## Testing Strategy

Unit tests:

- contracts
- provider interface and mock provider
- openai provider missing-key error
- session config/tool definition generation from backend schemas
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
- missing/wrong/expired tool-call token rejection

Manual verification:

- mock-mode browser test page can start a local session
- mock-mode function calls can be relayed through backend and displayed locally
- handoff path enters `handoff_pending`
- unclear speech or unconfirmed order ID causes one clarification attempt, then handoff if still unresolved

## Acceptance Criteria

The phase is complete when:

- all tests pass
- existing `/health` and `/v1/calls/simulate` still pass
- mock Realtime session endpoint works without OpenAI credentials
- OpenAI provider path fails safely without `OPENAI_API_KEY`
- browser test page is available locally
- tool-call endpoint executes only allowlisted tools
- tool-call endpoint requires a valid session-bound authorization header
- Realtime tool definitions are generated from backend allowlist and schemas
- unclear speech and unconfirmed order IDs have a documented clarification-then-handoff policy
- event log contains redacted structured events and no raw audio, provider credentials, relay tokens, or unredacted PII
- default local event-log path is ignored by git
- documentation explains setup, env vars, mock mode, and the deferred real OpenAI provider boundary

## Deferred

- production phone provider integration
- SIP/WebSocket telephony media pipeline
- real human transfer
- merchant-specific configuration UI
- database persistence implementation
- production observability dashboards
- real call recording evaluation
- full PII detection for names/addresses
- real OpenAI Realtime WebRTC session creation
- browser microphone capture and audio playback
- live speech-to-speech voice model verification
