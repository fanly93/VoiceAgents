# VoiceAgents Other Provider Integration Tasks

Status: PLANNED / NO CODE STARTED
Source spec: `docs/specs/voiceagents-other-provider-integration.md`
Branch: `feat/other-provider-integration-planning`

Rules:

- Use TDD: write focused failing tests before implementation.
- Use `./.venv/bin/python` for Python commands.
- Commit each independently verified checkpoint.
- Do not write or commit `.voiceagents/` artifacts.
- Do not print or persist API keys, client secrets, provider credentials, tool tokens, Authorization headers, SDP, raw audio, or real PII.
- Keep frontend work utilitarian; do not start frontend polish or production provider selection UI.
- Do not change order/logistics/product knowledge/handoff adapters unless a failing test proves the provider boundary requires it.
- Each task below is intended to be a single-responsibility atomic task. If a task grows past one clear behavior, split it before implementation.

## Phase 0: Planning And Consistency

Goal: lock the provider-neutral design before implementation.

### Task 0.1: Complete Office-Hours Design And Specs

Status: DONE

Inputs:

- user goal: DashScope first, provider-neutral base for future voice models;
- existing OpenAI realtime MVP specs and code.

Outputs:

- `docs/designs/voiceagents-other-provider-integration.md`;
- `docs/specs/voiceagents-other-provider-integration.md`;
- `docs/specs/voiceagents-other-provider-integration-tasks.md`.

Validation:

```bash
rg -n "DashScope|NativeRealtimeVoiceProvider|CascadedVoiceProvider|qwen3.5-omni-flash-realtime|server_websocket_proxy" docs/designs/voiceagents-other-provider-integration.md docs/specs/voiceagents-other-provider-integration.md docs/specs/voiceagents-other-provider-integration-tasks.md
git diff --check
```

### Task 0.2: Repair Specs Consistency Before Code

Status: DONE

Inputs:

- gstack document-release consistency review findings;
- Superpowers writing-plans task granularity requirements.

Outputs:

- safety wording distinguishes long-lived credentials from browser-safe ephemeral credentials;
- DashScope proxy contract is explicit;
- provider priorities are split by native realtime versus ASR/TTS adapters;
- this tasks file has four to six phases, atomic tasks, and clear inputs/outputs.

Validation:

```bash
rg -n "browser-safe ephemeral|DashScope proxy contract|Native realtime voice priority|Inputs:|Outputs:" docs/designs/voiceagents-other-provider-integration.md docs/specs/voiceagents-other-provider-integration.md docs/specs/voiceagents-other-provider-integration-tasks.md
git diff --check
```

Checkpoint:

```bash
git add docs/designs/voiceagents-other-provider-integration.md docs/specs/voiceagents-other-provider-integration.md docs/specs/voiceagents-other-provider-integration-tasks.md
git commit -m "docs: align other provider integration specs"
```

### Task 0.3: Repair Autoplan Review Findings

Status: DONE

Inputs:

- gstack-autoplan/plan review focus: product scope, engineering risk, DX, and DashScope proxy blind spots;
- finding: Phase 5 previously returned proxy metadata but did not require a fake-upstream WebSocket relay test.

Outputs:

- spec clarifies that DashScope proxy completion requires a browser-facing route and fake-upstream relay coverage;
- Phase 5 is split into route, auth, envelope, fake relay, page wiring, checklist, and verification tasks.

Validation:

```bash
rg -n "fake-upstream relay|WebSocket support|Proxy Route|Proxy Message Envelope|Fake Upstream Relay" docs/specs/voiceagents-other-provider-integration.md docs/specs/voiceagents-other-provider-integration-tasks.md
git diff --check
```

Checkpoint:

```bash
git add docs/specs/voiceagents-other-provider-integration.md docs/specs/voiceagents-other-provider-integration-tasks.md
git commit -m "docs: tighten dashscope proxy plan"
```

## Phase 1: Provider-Neutral Contracts

Goal: add explicit provider capability and connection contracts without changing runtime behavior.

Primary files:

- `voiceagents/realtime/contracts.py`
- `tests/test_realtime_contracts.py`

### Task 1.1: Add Provider Name For DashScope

Status: TODO

Inputs:

- current `RealtimeProviderName` values: `mock`, `openai_realtime`;
- spec provider value: `dashscope_realtime`.

Outputs:

- `RealtimeProviderName.DASHSCOPE_REALTIME`;
- contract test proving the enum accepts `dashscope_realtime`.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_contracts.py -v
```

### Task 1.2: Add Connection Mode Enum

Status: TODO

Inputs:

- required connection modes from spec: `browser_webrtc_ephemeral`, `server_websocket_proxy`, `server_sdk_proxy`, `cascaded_pipeline`.

Outputs:

- provider-neutral connection mode enum in `voiceagents/realtime/contracts.py`;
- test proving all four values validate and unknown values fail.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_contracts.py -v
```

### Task 1.3: Add Provider Capability Model

Status: TODO

Inputs:

- provider name enum;
- connection mode enum;
- `ResponseMode`.

Outputs:

- provider capability Pydantic model rejecting extra fields;
- test proving capability includes supported modes, response modes, native tool support, default model, and default voice.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_contracts.py -v
```

### Task 1.4: Add Provider Connection Metadata

Status: TODO

Inputs:

- existing `RealtimeClientSecretResponse`;
- response compatibility rules in `docs/specs/voiceagents-other-provider-integration.md`.

Outputs:

- provider-neutral connection metadata fields for `connection_mode` and browser-safe ephemeral credential semantics;
- tests proving OpenAI can expose browser-safe ephemeral metadata while DashScope proxy metadata does not expose a provider API key.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_contracts.py tests/test_realtime_providers.py -v
```

Checkpoint:

```bash
git add voiceagents/realtime/contracts.py tests/test_realtime_contracts.py tests/test_realtime_providers.py
git commit -m "feat: add realtime provider connection contracts"
```

## Phase 2: Provider Registry And Diagnostics

Goal: construct and diagnose providers through explicit provider metadata.

Primary files:

- `voiceagents/realtime/providers.py`
- `voiceagents/realtime/diagnostics.py`
- `tests/test_realtime_providers.py`
- `tests/test_realtime_diagnostics.py`
- `tests/test_api_realtime_diagnostics.py`

### Task 2.1: Add Provider Registry Entries

Status: TODO

Inputs:

- provider capability model from Phase 1;
- current `MockRealtimeProvider` and `OpenAIRealtimeProvider`.

Outputs:

- registry entries for mock, OpenAI realtime, and DashScope realtime capability metadata;
- test proving supported provider names are discoverable.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_providers.py -v
```

### Task 2.2: Add Provider Factory For Mock And OpenAI

Status: TODO

Inputs:

- current provider construction logic in `voiceagents/api/app.py`;
- registry entries from Task 2.1.

Outputs:

- provider factory function that constructs mock and OpenAI providers;
- tests proving current OpenAI and mock provider behavior remains unchanged.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_providers.py tests/test_api_realtime_client_secret.py -v
```

### Task 2.3: Add DashScope Factory Stub

Status: TODO

Inputs:

- DashScope provider name and capability metadata;
- server-only env names from spec.

Outputs:

- DashScope provider stub that can be constructed with fake config;
- test proving missing real `DASHSCOPE_API_KEY` is handled safely and no network call is made.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_providers.py -v
```

### Task 2.4: Generalize Provider Diagnostics

Status: TODO

Inputs:

- current `build_realtime_dev_diagnostics`;
- registry-supported provider names.

Outputs:

- diagnostics use provider metadata rather than OpenAI-only branching;
- unsupported provider still returns safe `fail`.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_diagnostics.py tests/test_api_realtime_diagnostics.py -v
```

### Task 2.5: Add DashScope Diagnostics Checks

Status: TODO

Inputs:

- `VOICEAGENTS_DASHSCOPE_API_KEY`;
- `VOICEAGENTS_DASHSCOPE_REALTIME_MODEL`;
- `VOICEAGENTS_DASHSCOPE_BASE_URL`.

Outputs:

- diagnostics checks for DashScope key presence, model, base URL/region, and connection mode;
- tests proving secret values are never printed.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_diagnostics.py tests/test_diagnose_realtime_dev_cli.py -v
```

Checkpoint:

```bash
git add voiceagents/realtime/providers.py voiceagents/realtime/diagnostics.py tests/test_realtime_providers.py tests/test_realtime_diagnostics.py tests/test_api_realtime_diagnostics.py tests/test_diagnose_realtime_dev_cli.py
git commit -m "feat: add realtime provider registry diagnostics"
```

## Phase 3: Session-Bound Provider Semantics

Goal: make event and tool execution use the session provider binding, not mutable process env.

Primary files:

- `voiceagents/api/app.py`
- `voiceagents/realtime/session_store.py`
- `voiceagents/realtime/tool_router.py`
- `tests/test_api_realtime_tool_call.py`
- `tests/test_realtime_session_store.py`

### Task 3.1: Add Session Provider Lookup Test

Status: TODO

Inputs:

- `InMemoryVoiceSessionStore`;
- existing session metadata: session id, call id, merchant id, provider.

Outputs:

- test proving the store can retrieve the original provider for a session;
- no API behavior change yet.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_session_store.py -v
```

### Task 3.2: Route Tool Calls With Session Provider

Status: TODO

Inputs:

- `RealtimeToolCallRequest`;
- bearer `tool_call_token`;
- session provider from store.

Outputs:

- `/v1/realtime/tool-call` passes the session provider into `RealtimeToolRouter`;
- test proving changing `VOICEAGENTS_REALTIME_PROVIDER` after session creation does not rebind the tool call.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_tool_call.py tests/test_realtime_session_store.py -v
```

### Task 3.3: Log Tool Events With Session Provider

Status: TODO

Inputs:

- safe `RealtimeToolCallResponse`;
- session provider from store.

Outputs:

- tool-call event log records the session provider, not the current env provider;
- test proving event repository sees the original session provider.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_tool_call.py -v
```

Checkpoint:

```bash
git add voiceagents/api/app.py voiceagents/realtime/session_store.py voiceagents/realtime/tool_router.py tests/test_api_realtime_tool_call.py tests/test_realtime_session_store.py
git commit -m "fix: bind realtime tool calls to session provider"
```

## Phase 4: DashScope Provider And Event Adapter

Goal: add DashScope model configuration and normalized event mapping with fake transports only.

Primary files:

- `voiceagents/realtime/dashscope.py`
- `tests/test_realtime_dashscope_provider.py`
- `tests/test_realtime_dashscope_adapter.py`
- `README.md`

### Task 4.1: Add DashScope Config Model

Status: TODO

Inputs:

- server env names from spec;
- default model `qwen3.5-omni-flash-realtime`.

Outputs:

- DashScope config object with base URL, model, voice, and API key presence;
- tests proving config defaults and missing key behavior.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_provider.py -v
```

### Task 4.2: Add DashScope Provider Skeleton

Status: TODO

Inputs:

- DashScope config object;
- provider-neutral connection response contract.

Outputs:

- DashScope provider returns browser-safe `server_websocket_proxy` metadata with a local proxy URL;
- test proving `DASHSCOPE_API_KEY` is not in the response.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_provider.py tests/test_realtime_providers.py -v
```

### Task 4.3: Add DashScope Session Event Normalization

Status: TODO

Inputs:

- representative fake DashScope session/connection/error events;
- `NormalizedRealtimeEventType`.

Outputs:

- DashScope adapter maps lifecycle and provider error events to safe normalized events;
- tests with fake fixtures.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

### Task 4.4: Add DashScope Transcript Event Normalization

Status: TODO

Inputs:

- representative fake user/assistant transcript partial/final events;
- transcript event contract.

Outputs:

- DashScope adapter maps user and assistant transcript events to normalized transcript payloads;
- tests proving raw provider payload is not persisted as raw text outside allowed contract fields.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py tests/test_realtime_contracts.py -v
```

### Task 4.5: Add DashScope Tool Event Normalization

Status: TODO

Inputs:

- representative fake DashScope native function/tool-call event;
- allowed tool names.

Outputs:

- DashScope adapter maps native tool-call request to `RealtimeToolCallRequest`;
- tests proving unknown tool names are not routed as allowed tools.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py tests/test_realtime_tool_router.py -v
```

### Task 4.6: Add DashScope Safe Tool Result Event Builder

Status: TODO

Inputs:

- safe `RealtimeToolCallResponse`;
- provider call id.

Outputs:

- DashScope provider-specific tool-result event builder;
- tests proving failed tool responses use safe `tool_status` / `error_message` semantics and do not include raw arguments.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py tests/test_api_realtime_tool_call.py -v
```

Checkpoint:

```bash
git add voiceagents/realtime/dashscope.py tests/test_realtime_dashscope_provider.py tests/test_realtime_dashscope_adapter.py README.md
git commit -m "feat: add dashscope realtime provider adapter"
```

## Phase 5: Browser-Safe Proxy And Manual Verification

Goal: expose a utilitarian DashScope developer path with a fake-tested proxy boundary and without exposing provider credentials.

Primary files:

- `voiceagents/api/app.py`
- `voiceagents/api/static/realtime-test.html`
- `voiceagents/api/static/realtime-dashscope-adapter.js`
- `tests/test_api_realtime_test_page.py`
- `tests/test_api_realtime_client_secret.py`
- `tests/test_api_realtime_dashscope_proxy.py`
- `docs/specs/voiceagents-dashscope-realtime-manual-checklist.md`
- `README.md`
- `OPENAI_REALTIME_VOICE_MVP_HANDOFF.md`

### Task 5.1: Decide And Document Proxy Endpoint

Status: TODO

Inputs:

- DashScope proxy contract from spec;
- FastAPI/Starlette native WebSocket support for browser-facing proxy routes.

Outputs:

- exact local proxy route documented in README or manual checklist;
- route discovery test proving the route is declared without requiring real DashScope credentials.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_client_secret.py tests/test_api_realtime_dashscope_proxy.py -v
```

### Task 5.2: Return DashScope Proxy Metadata To Browser

Status: TODO

Inputs:

- DashScope provider skeleton;
- client-secret endpoint.

Outputs:

- `/v1/realtime/client-secret` returns DashScope provider, model, `server_websocket_proxy`, and local proxy URL;
- tests proving response does not include `DASHSCOPE_API_KEY`.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_client_secret.py -v
```

### Task 5.3: Add Proxy Route Authentication

Status: TODO

Inputs:

- exact proxy route from Task 5.1;
- session-bound `tool_call_token`;
- `InMemoryVoiceSessionStore`.

Outputs:

- browser-facing WebSocket proxy rejects missing, malformed, expired, or wrong-session tokens;
- tests prove rejected attempts never construct DashScope upstream transport.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py tests/test_realtime_session_store.py -v
```

### Task 5.4: Add Proxy Message Envelope Validation

Status: TODO

Inputs:

- browser-to-proxy message types: audio/control/tool-result;
- blocked secret keys from event-log safety rules.

Outputs:

- proxy accepts only the allowed message envelope;
- proxy rejects messages containing provider API keys, Authorization headers, client secrets, SDP, raw tool arguments, or unexpected top-level fields.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py tests/test_realtime_contracts.py -v
```

### Task 5.5: Add Fake Upstream Relay

Status: TODO

Inputs:

- fake DashScope upstream transport;
- proxy message envelope;
- DashScope event adapter from Phase 4.

Outputs:

- fake browser WebSocket message can traverse VoiceAgents proxy to fake upstream;
- fake upstream provider event is normalized and sent back to browser as a safe response;
- no automated test calls real DashScope.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py tests/test_realtime_dashscope_adapter.py -v
```

### Task 5.6: Add Outbound Transport Dependency Decision

Status: TODO

Inputs:

- fake upstream relay result;
- DashScope official WebSocket requirements;
- current project dependencies.

Outputs:

- implementation either adds a named outbound WebSocket client dependency behind the transport interface or documents why the real outbound transport remains manual/deferred;
- tests still use fake transport and do not require real DashScope credentials.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py -v
git diff --check
```

### Task 5.7: Add Utilitarian DashScope Test Page Wiring

Status: TODO

Inputs:

- `/realtime-test` current OpenAI wiring;
- DashScope proxy metadata.

Outputs:

- `/realtime-test` can show provider, model, connection mode, and safe DashScope connection status;
- OpenAI WebRTC path remains unchanged.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py -v
```

### Task 5.8: Add DashScope Manual Checklist

Status: TODO

Inputs:

- fake-transport test evidence;
- required real-provider env vars.

Outputs:

- `docs/specs/voiceagents-dashscope-realtime-manual-checklist.md`;
- README and handoff references for local DashScope validation.

Validation:

```bash
rg -n "dashscope_realtime|DASHSCOPE_API_KEY|qwen3.5-omni-flash-realtime|server_websocket_proxy" README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-dashscope-realtime-manual-checklist.md
git diff --check
```

### Task 5.9: Run Focused And Full Verification

Status: TODO

Inputs:

- all code and docs from Phases 1-5.

Outputs:

- focused realtime provider tests pass;
- full Python test suite passes;
- no secret-bearing artifacts are staged.

Validation:

```bash
./.venv/bin/python -m pytest
git diff --check
git status --short
```

Checkpoint:

```bash
git add voiceagents/api/app.py voiceagents/api/static/realtime-test.html voiceagents/api/static/realtime-dashscope-adapter.js tests/test_api_realtime_test_page.py tests/test_api_realtime_client_secret.py tests/test_api_realtime_dashscope_proxy.py docs/specs/voiceagents-dashscope-realtime-manual-checklist.md README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md
git commit -m "feat: expose dashscope realtime proxy path"
```
