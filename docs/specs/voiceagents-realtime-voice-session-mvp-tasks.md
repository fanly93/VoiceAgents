# VoiceAgents Realtime Voice Session MVP Tasks

Status: DRAFT
Source spec: `docs/specs/voiceagents-realtime-voice-session-mvp.md`

Rules:

- Do not implement production telephony.
- Do not store raw audio.
- Do not commit real PII.
- Do not commit `.voiceagents/` local event logs.
- Each task is intended to be separately commit-able.
- Each task has explicit inputs and outputs.
- Each task should include or preserve focused tests.
- Real OpenAI credentials are optional for local manual verification; automated tests must pass without them.

---

## Phase 1: Realtime Contracts And Provider Boundary

### Task 1.1: Create Realtime Package Boundary

Purpose: establish module boundaries without behavior.

Inputs:

- Existing `voiceagents/` package
- Source spec

Outputs:

- `voiceagents/realtime/__init__.py`

Validation:

```bash
python3 -m pytest tests/test_backend_package.py
```

### Task 1.2: Add Realtime Enums

Purpose: define stable state, provider, and response-mode values.

Inputs:

- Source spec enum list

Outputs:

- `voiceagents/realtime/contracts.py`
- `tests/test_realtime_contracts.py`

Required outputs:

- `VoiceSessionState`
- `ResponseMode`
- `RealtimeProviderName`

Validation:

```bash
python3 -m pytest tests/test_realtime_contracts.py
```

### Task 1.3: Add Client Secret Contracts

Purpose: encode provider credential request and response shapes.

Inputs:

- Source spec client-secret section

Outputs:

- Updated `voiceagents/realtime/contracts.py`
- Updated `tests/test_realtime_contracts.py`

Required outputs:

- `RealtimeClientSecretRequest`
- `RealtimeClientSecretResponse`
- response includes `tool_call_token`
- response includes `session_config`

Validation:

```bash
python3 -m pytest tests/test_realtime_contracts.py
```

### Task 1.4: Add Tool Call Contracts

Purpose: encode the unified Realtime tool-call API boundary.

Inputs:

- Source spec tool-call section
- Existing `ToolErrorCode`
- Existing `HandoffReason`

Outputs:

- Updated `voiceagents/realtime/contracts.py`
- Updated `tests/test_realtime_contracts.py`

Required outputs:

- `RealtimeToolCallRequest`
- `RealtimeToolCallResponse`
- request does not include `tool_call_token` in the JSON body
- API layer will read `tool_call_token` from an HTTP authorization header

Validation:

```bash
python3 -m pytest tests/test_realtime_contracts.py
```

### Task 1.5: Add Realtime Session Config Contracts

Purpose: make backend-generated Realtime instructions and tool definitions the source of truth.

Inputs:

- allowed Realtime tool list from source spec
- per-tool argument schema requirements
- unclear speech and handoff policy from source spec

Outputs:

- Updated `voiceagents/realtime/contracts.py`
- Updated `tests/test_realtime_contracts.py`

Required outputs:

- `RealtimeSessionConfig`
- `RealtimeToolDefinition`
- tests that tools are serializable and contain only allowlisted tool names

Validation:

```bash
python3 -m pytest tests/test_realtime_contracts.py
```

### Task 1.6: Add Voice Event Contract

Purpose: define the structured event log payload.

Inputs:

- Source spec event fields

Outputs:

- Updated `voiceagents/realtime/contracts.py`
- Updated `tests/test_realtime_contracts.py`

Required outputs:

- `VoiceEvent`

Validation:

```bash
python3 -m pytest tests/test_realtime_contracts.py
```

### Task 1.7: Add Provider Protocol And Mock Provider

Purpose: keep provider-specific session creation outside business logic.

Inputs:

- `RealtimeClientSecretRequest`
- `RealtimeClientSecretResponse`

Outputs:

- `voiceagents/realtime/providers.py`
- `tests/test_realtime_providers.py`

Required behavior:

- `MockRealtimeProvider.create_client_secret()` returns deterministic fake credentials.
- `OpenAIRealtimeProvider.create_client_secret()` exists but may be minimal until endpoint wiring.

Validation:

```bash
python3 -m pytest tests/test_realtime_providers.py
```

---

## Phase 2: Session Store, Event Log, And Redaction

### Task 2.1: Add Redaction Result And Text Redactor

Purpose: prevent obvious PII from being written to event logs.

Inputs:

- Redaction rules from source spec

Outputs:

- `voiceagents/realtime/redaction.py`
- `tests/test_realtime_redaction.py`

Required behavior:

- redact email-like strings
- redact phone-like strings
- redact order-like IDs
- report whether redaction was applied

Validation:

```bash
python3 -m pytest tests/test_realtime_redaction.py
```

### Task 2.2: Add Mapping Redaction

Purpose: redact tool arguments before event logging.

Inputs:

- `redact_text`
- dict-like tool arguments

Outputs:

- Updated `voiceagents/realtime/redaction.py`
- Updated `tests/test_realtime_redaction.py`

Validation:

```bash
python3 -m pytest tests/test_realtime_redaction.py
```

### Task 2.3: Add Session Store Interface And In-Memory Store

Purpose: track runtime voice session state without introducing a database.

Inputs:

- `VoiceSessionState`
- Source spec session store methods

Outputs:

- `voiceagents/realtime/session_store.py`
- `tests/test_realtime_session_store.py`

Required behavior:

- create session
- create session-bound `tool_call_token` with `secrets.token_urlsafe(32)` or stronger entropy
- store only a token hash; do not retain plaintext token after returning it once
- record token expiry at or before provider credential expiry
- use a default token TTL of 10 minutes when provider expiry is unavailable
- validate token with constant-time comparison
- reject expired tokens
- get session
- update state
- append transcript
- append tool call summary
- mark handoff
- end session

Validation:

```bash
python3 -m pytest tests/test_realtime_session_store.py
```

### Task 2.4: Add Voice Event Repository Interface

Purpose: reserve a database-compatible persistence boundary.

Inputs:

- `VoiceEvent`

Outputs:

- `voiceagents/realtime/event_log.py`
- `tests/test_realtime_event_log.py`

Required behavior:

- define append interface
- add a no-op or in-memory test implementation if useful

Validation:

```bash
python3 -m pytest tests/test_realtime_event_log.py
```

### Task 2.5: Add JSONL Event Repository

Purpose: write redacted structured event logs for local debugging.

Inputs:

- `VoiceEvent`
- redactor
- configured log path

Outputs:

- Updated `voiceagents/realtime/event_log.py`
- Updated `tests/test_realtime_event_log.py`

Required behavior:

- create parent directory
- append one JSON object per line
- reject or omit raw audio fields
- write redacted text only
- omit provider credentials and tool-call relay tokens
- default `.voiceagents/` path is ignored by git

Validation:

```bash
python3 -m pytest tests/test_realtime_event_log.py
```

---

## Phase 3: Realtime Tool Router And API Endpoints

### Task 3.1: Add Tool Router Allowlist

Purpose: reject unknown Realtime function calls before any business logic runs.

Inputs:

- allowed tool list from source spec
- session store token verifier

Outputs:

- `voiceagents/realtime/tool_router.py`
- `tests/test_realtime_tool_router.py`

Required behavior:

- unknown `tool_name` raises a typed error or returns a rejected response
- invalid, expired, or missing `tool_call_token` raises a typed error or returns a rejected response
- tool definitions can be generated from the same allowlist

Validation:

```bash
python3 -m pytest tests/test_realtime_tool_router.py
```

### Task 3.2: Add Tool Argument Schemas

Purpose: validate Realtime tool arguments per tool.

Inputs:

- `lookup_order`
- `lookup_logistics`
- `query_product_knowledge`
- `handoff_to_human`

Outputs:

- Updated `voiceagents/realtime/tool_router.py`
- Updated `tests/test_realtime_tool_router.py`

Validation:

```bash
python3 -m pytest tests/test_realtime_tool_router.py
```

### Task 3.3: Route Order And Logistics Tools

Purpose: execute approved order/logistics tool calls through existing adapters.

Inputs:

- `RealtimeToolCallRequest`
- existing mock order/logistics adapters

Outputs:

- Updated `voiceagents/realtime/tool_router.py`
- Updated `tests/test_realtime_tool_router.py`

Expected output:

- safe order/logistics summaries
- `handoff_required=false` for known successful mock calls

Validation:

```bash
python3 -m pytest tests/test_realtime_tool_router.py
```

### Task 3.4: Route Product Knowledge And Handoff Tools

Purpose: execute product consultation and handoff-safe paths.

Inputs:

- existing mock knowledge/handoff adapters

Outputs:

- Updated `voiceagents/realtime/tool_router.py`
- Updated `tests/test_realtime_tool_router.py`

Expected output:

- known product query returns safe answer
- explicit handoff tool returns `handoff_required=true`

Validation:

```bash
python3 -m pytest tests/test_realtime_tool_router.py
```

### Task 3.5: Add Client Secret API Endpoint

Purpose: expose provider credential creation through FastAPI.

Inputs:

- `RealtimeClientSecretRequest`
- provider factory
- session store
- event repository

Outputs:

- Updated `voiceagents/api/app.py`
- `tests/test_api_realtime_client_secret.py`

Required behavior:

- mock provider returns deterministic fake credential
- response does not include standard API key
- response includes session-bound `tool_call_token`
- response includes backend-generated `session_config.instructions`
- response includes backend-generated `session_config.tools`
- generated tools match the backend allowlist and argument schemas
- event log does not write provider credential or `tool_call_token`
- session is created

Validation:

```bash
python3 -m pytest tests/test_api_realtime_client_secret.py
```

### Task 3.6: Add Tool Call API Endpoint

Purpose: expose the unified backend tool execution endpoint.

Inputs:

- `RealtimeToolCallRequest`
- HTTP authorization header with `tool_call_token`
- `RealtimeToolRouter`
- session store
- event repository

Outputs:

- Updated `voiceagents/api/app.py`
- `tests/test_api_realtime_tool_call.py`

Required behavior:

- successful tool call returns HTTP 200
- missing or malformed authorization header returns HTTP 401 or 403
- invalid `tool_call_token` returns HTTP 403
- expired `tool_call_token` returns HTTP 403
- unknown tool returns HTTP 400
- invalid arguments return HTTP 422
- handoff tool updates session state

Validation:

```bash
python3 -m pytest tests/test_api_realtime_tool_call.py
```

---

## Phase 4: Minimal Browser Test Page

### Task 4.1: Add Static Browser Test Page

Purpose: provide a local UI shell without adding a frontend build system.

Inputs:

- Source spec UI requirements

Outputs:

- `voiceagents/api/static/realtime-test.html`
- `tests/test_api_realtime_test_page.py`

Required behavior:

- page includes start/stop controls
- page includes transcript, response, state, tool call, handoff, latency, and provider event regions

Validation:

```bash
python3 -m pytest tests/test_api_realtime_test_page.py
```

### Task 4.2: Serve Test Page From FastAPI

Purpose: make the browser page available locally.

Inputs:

- static HTML file

Outputs:

- Updated `voiceagents/api/app.py`
- Updated `tests/test_api_realtime_test_page.py`

Required route:

- `GET /realtime-test`

Validation:

```bash
python3 -m pytest tests/test_api_realtime_test_page.py
```

### Task 4.3: Add Browser Session Bootstrap JavaScript

Purpose: connect the page to `/v1/realtime/client-secret`.

Inputs:

- endpoint contract
- test page DOM

Outputs:

- Updated `voiceagents/api/static/realtime-test.html`
- Updated `tests/test_api_realtime_test_page.py`

Required behavior:

- JS references `/v1/realtime/client-secret`
- JS reads `session_config.instructions` and `session_config.tools` from the response
- no standard OpenAI API key appears in static assets
- `client_secret` and `tool_call_token` are not rendered into visible event panels

Validation:

```bash
python3 -m pytest tests/test_api_realtime_test_page.py
```

### Task 4.4: Add Tool Call Relay JavaScript

Purpose: relay Realtime function calls to backend tool execution.

Inputs:

- `POST /v1/realtime/tool-call`
- Realtime function-call event shape

Outputs:

- Updated `voiceagents/api/static/realtime-test.html`
- Updated `tests/test_api_realtime_test_page.py`

Required behavior:

- JS references `/v1/realtime/tool-call`
- JS sends `tool_call_token` only through an HTTP authorization header
- JS uses backend-returned tool definitions when configuring the Realtime session
- UI has a tool-call list region

Validation:

```bash
python3 -m pytest tests/test_api_realtime_test_page.py
```

---

## Phase 5: Documentation, Verification, And Review

### Task 5.1: Document Realtime Voice MVP Setup

Purpose: make mock and OpenAI modes understandable.

Inputs:

- README
- source spec

Outputs:

- Updated `README.md`

Required content:

- environment variables
- mock provider mode
- OpenAI provider mode
- browser test page URL
- no telephony/no audio storage warning
- `.voiceagents/` event logs are local-only and gitignored
- tool-call relay tokens are short-lived session credentials and must not be logged

Validation:

```bash
python3 -m pytest
```

### Task 5.2: Add Realtime Smoke Script

Purpose: verify backend Realtime endpoints without real OpenAI credentials.

Inputs:

- running local API server
- mock provider mode

Outputs:

- `scripts/smoke_realtime_api.py`

Required behavior:

- call `/v1/realtime/client-secret`
- call `/v1/realtime/tool-call` for order/logistics/product/handoff using authorization header token
- fail on unknown tool if it does not reject
- fail if a tool call without authorization is accepted

Validation:

```bash
python3 -m py_compile scripts/smoke_realtime_api.py
```

### Task 5.3: Run Full Test Suite

Purpose: ensure existing backend behavior was not broken.

Inputs:

- completed implementation

Outputs:

- terminal evidence

Validation:

```bash
python3 -m pytest
python3 scripts/validate_call_evaluations.py data/call-evaluations/sample.json
```

### Task 5.4: Run Local Realtime Smoke

Purpose: verify mock Realtime endpoints over HTTP.

Inputs:

- running local API server
- `scripts/smoke_realtime_api.py`

Outputs:

- terminal evidence

Validation:

```bash
python3 -m uvicorn voiceagents.api.main:app --host 127.0.0.1 --port 8767
python3 scripts/smoke_realtime_api.py --base-url http://127.0.0.1:8767
```

### Task 5.5: Run `$gstack-review`

Purpose: review the feature branch before implementation is considered complete.

Inputs:

- completed implementation commits
- source spec
- this task plan

Outputs:

- review result

Validation:

```bash
$gstack-review
```

Stop for user approval before fixing any non-mechanical review findings.

---

## Implementation Approval Gate

Do not start implementation until this spec, task plan, and review are explicitly approved.
