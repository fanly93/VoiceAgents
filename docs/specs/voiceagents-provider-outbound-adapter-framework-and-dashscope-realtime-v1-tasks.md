# VoiceAgents Provider Outbound Adapter Framework And DashScope Realtime V1 Tasks

Status: PLANNED / NO CODE STARTED
Date: 2026-06-02
Branch: `feat/dashscope-realtime-outbound`
Spec: `docs/specs/voiceagents-provider-outbound-adapter-framework-and-dashscope-realtime-v1.md`
Plan: `docs/superpowers/plans/2026-06-02-provider-outbound-adapter-framework-and-dashscope-realtime-v1.md`

## Task Rules

- Each task has one responsibility.
- Each task should be commit-sized.
- Prefer 2-6 minute atomic implementation steps during execution.
- Use TDD for code behavior: write failing test, verify red, implement, verify green, commit.
- Automated tests must not call real DashScope or require real provider credentials.
- Do not commit `.env`, API keys, Authorization headers, tokens, raw audio, SDP, raw provider payloads, screenshots with secrets, or real PII.

## Phase 1: Provider-Neutral Outbound Contracts

Goal: define fake-testable contracts before changing the existing DashScope proxy behavior.

### Task 1.1: Add outbound transport contract tests

Input:

- Spec sections: Provider-Neutral Outbound Contracts, Test Requirements.
- Existing files: `voiceagents/realtime/contracts.py`, `tests/test_realtime_contracts.py`.

Output:

- New test file `tests/test_realtime_outbound_contracts.py`.
- Failing tests for transport event shape, browser proxy envelope shape, and safe error shape.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py -v
```

Expected before implementation: fail because `voiceagents.realtime.outbound` does not exist.

Commit:

```bash
git add tests/test_realtime_outbound_contracts.py
git commit -m "test: specify realtime outbound contracts"
```

### Task 1.2: Implement outbound contract models

Input:

- Failing tests from Task 1.1.

Output:

- New file `voiceagents/realtime/outbound.py`.
- Pydantic/dataclass models or protocols for outbound JSON events, audio events, close events, safe errors, browser proxy messages, provider connection metadata, and async transport protocol.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py -v
```

Expected: pass.

Commit:

```bash
git add voiceagents/realtime/outbound.py tests/test_realtime_outbound_contracts.py
git commit -m "feat: add realtime outbound contracts"
```

### Task 1.3: Specify provider adapter protocol tests

Input:

- `voiceagents/realtime/outbound.py`.
- Existing DashScope helpers in `voiceagents/realtime/dashscope.py`.

Output:

- Tests that a provider adapter can build URL, headers, session setup message, tool declarations, normalized events, and tool-result messages without exposing secrets.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py -v
```

Expected before implementation: fail on missing adapter protocol.

Commit:

```bash
git add tests/test_realtime_outbound_contracts.py
git commit -m "test: specify realtime provider adapter protocol"
```

### Task 1.4: Implement provider adapter protocol

Input:

- Failing tests from Task 1.3.

Output:

- `NativeRealtimeProviderAdapter` protocol in `voiceagents/realtime/outbound.py`.
- No provider-specific implementation yet.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py -v
```

Expected: pass.

Commit:

```bash
git add voiceagents/realtime/outbound.py tests/test_realtime_outbound_contracts.py
git commit -m "feat: add native realtime adapter protocol"
```

## Phase 2: DashScope Protocol Adapter

Goal: make DashScope protocol mapping explicit and fake-testable before adding real network transport.

### Task 2.1: Add DashScope URL and header tests

Input:

- Official DashScope WebSocket docs.
- `DashScopeRealtimeConfig`.

Output:

- Tests in `tests/test_realtime_dashscope_adapter.py` for:
  - default Beijing WebSocket URL;
  - configured base URL;
  - model query parameter;
  - Authorization header present only inside adapter output;
  - secret absent from `repr`, summaries, normalized events, and model dumps.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Expected before implementation: fail on missing adapter class/functions.

Commit:

```bash
git add tests/test_realtime_dashscope_adapter.py
git commit -m "test: specify dashscope realtime connection mapping"
```

### Task 2.2: Implement DashScope connection mapping

Input:

- Failing tests from Task 2.1.

Output:

- DashScope adapter class or focused functions in `voiceagents/realtime/dashscope.py`.
- URL/header construction that does not mutate config and does not log secrets.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Expected: pass.

Commit:

```bash
git add voiceagents/realtime/dashscope.py tests/test_realtime_dashscope_adapter.py
git commit -m "feat: map dashscope realtime connection settings"
```

### Task 2.3: Add DashScope session.update and tool declaration tests

Input:

- `build_default_realtime_session_config()`.
- Official DashScope session.update and Function Calling docs.

Output:

- Tests proving VoiceAgents instructions, response mode, voice, audio formats, VAD config, and allowed tools map to DashScope-safe session/tool messages.
- Tests proving unsupported `tool_choice` and `parallel_tool_calls` are not emitted.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Expected before implementation: fail.

Commit:

```bash
git add tests/test_realtime_dashscope_adapter.py
git commit -m "test: specify dashscope session and tool mapping"
```

### Task 2.4: Implement DashScope session.update and tool declaration mapping

Input:

- Failing tests from Task 2.3.

Output:

- DashScope session setup message builder.
- DashScope tool declaration mapper.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Expected: pass.

Commit:

```bash
git add voiceagents/realtime/dashscope.py tests/test_realtime_dashscope_adapter.py
git commit -m "feat: map dashscope session tools"
```

### Task 2.5: Add DashScope provider event fixture tests

Input:

- Official DashScope event names from realtime docs.
- Existing `normalize_dashscope_event`, `normalize_dashscope_tool_call`, `build_dashscope_tool_result_event`.

Output:

- Tests for:
  - `session.created` or provider equivalent;
  - transcript user delta/done;
  - assistant transcript delta/done;
  - audio delta as transport-only event;
  - `response.function_call_arguments.done`;
  - `response.done`;
  - provider error safe normalization.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Expected before implementation: fail for unmapped official event names.

Commit:

```bash
git add tests/test_realtime_dashscope_adapter.py
git commit -m "test: specify dashscope official event normalization"
```

### Task 2.6: Implement DashScope official event normalization

Input:

- Failing tests from Task 2.5.

Output:

- DashScope event normalization for official provider events.
- Transport-only audio event classification with no persistence payload.
- Safe error normalization.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Expected: pass.

Commit:

```bash
git add voiceagents/realtime/dashscope.py tests/test_realtime_dashscope_adapter.py
git commit -m "feat: normalize dashscope realtime events"
```

## Phase 3: Proxy Coordinator And Fake Transport

Goal: replace inline DashScope proxy behavior with a reusable coordinator while preserving current fake-proxy tests.

### Task 3.1: Add proxy coordinator auth tests

Input:

- Existing `tests/test_api_realtime_dashscope_proxy.py`.
- Session store token binding.

Output:

- Tests proving missing token, wrong session, wrong provider, expired token, and invalid envelope close the browser WebSocket before provider connection.

Test:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py -v
```

Expected before implementation: existing tests pass; new tests may fail for coordinator-specific connection ordering.

Commit:

```bash
git add tests/test_api_realtime_dashscope_proxy.py
git commit -m "test: specify realtime proxy coordinator auth"
```

### Task 3.2: Implement proxy coordinator auth path

Input:

- Failing tests from Task 3.1.

Output:

- New file `voiceagents/realtime/proxy.py`.
- Coordinator authenticates browser before creating provider transport.
- `voiceagents/api/app.py` route delegates to coordinator or thin DashScope wrapper.

Test:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py -v
```

Expected: pass.

Commit:

```bash
git add voiceagents/realtime/proxy.py voiceagents/api/app.py tests/test_api_realtime_dashscope_proxy.py
git commit -m "feat: add realtime proxy coordinator auth"
```

### Task 3.3: Add fake transport relay tests

Input:

- `voiceagents/realtime/proxy.py`.
- `FakeDashScopeUpstreamTransport`.

Output:

- Tests for browser control -> provider message, provider transcript -> browser event, provider tool request -> backend tool router, backend tool result -> provider message, and provider disconnect -> browser safe close.

Test:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py -v
```

Expected before implementation: fail for tool/disconnect relay paths.

Commit:

```bash
git add tests/test_api_realtime_dashscope_proxy.py
git commit -m "test: specify realtime proxy fake relay"
```

### Task 3.4: Implement fake transport event relay and persistence

Input:

- Failing tests from Task 3.3.

Output:

- Coordinator relays safe browser messages and provider events.
- Coordinator persists DashScope loggable provider events server-side exactly once.

Test:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py tests/test_realtime_dashscope_adapter.py -v
```

Expected: event relay and persistence assertions pass; tool/disconnect assertions may still fail.

Commit:

```bash
git add voiceagents/realtime/proxy.py voiceagents/api/app.py tests/test_api_realtime_dashscope_proxy.py
git commit -m "feat: persist dashscope proxy events"
```

### Task 3.5: Implement provider tool-call routing and result relay

Input:

- Remaining failing tool-call tests from Task 3.3.

Output:

- Coordinator routes tool calls through existing `RealtimeToolRouter`.
- Coordinator sends provider-specific tool result events.

Test:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py tests/test_realtime_dashscope_adapter.py -v
```

Expected: tool request/result relay assertions pass; disconnect assertions may still fail.

Commit:

```bash
git add voiceagents/realtime/proxy.py voiceagents/api/app.py tests/test_api_realtime_dashscope_proxy.py
git commit -m "feat: route dashscope proxy tool calls"
```

### Task 3.6: Implement provider disconnect cleanup

Input:

- Remaining failing disconnect tests from Task 3.3.

Output:

- Coordinator closes both sides deterministically.

Test:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py tests/test_realtime_dashscope_adapter.py -v
```

Expected: pass.

Commit:

```bash
git add voiceagents/realtime/proxy.py voiceagents/api/app.py tests/test_api_realtime_dashscope_proxy.py
git commit -m "feat: close dashscope proxy cleanly"
```

## Phase 4: Real DashScope Outbound Transport

Goal: add real outbound transport behind the fake-tested interface without making tests call DashScope.

### Task 4.0: Decide outbound WebSocket dependency

Input:

- Spec section: DashScope Outbound Transport.
- Existing dependency files.
- Official DashScope WebSocket protocol requirements.

Output:

- A documented dependency decision in the implementation notes or manual checklist.
- Decision states whether to use an existing dependency, add a new dependency, or isolate an optional import.
- Decision states how tests inject fake clients and avoid network.

Test:

```bash
git diff --check
rg -n "DashScope outbound WebSocket|fake transport|network" docs/specs/voiceagents-dashscope-realtime-manual-checklist.md docs/specs/voiceagents-provider-outbound-adapter-framework-and-dashscope-realtime-v1.md
```

Expected: no whitespace errors; dependency and fake-test boundary are documented before transport implementation.

Commit:

```bash
git add docs/specs/voiceagents-dashscope-realtime-manual-checklist.md docs/specs/voiceagents-provider-outbound-adapter-framework-and-dashscope-realtime-v1.md
git commit -m "docs: decide dashscope outbound transport dependency"
```

### Task 4.1: Add DashScope transport construction tests

Input:

- `RealtimeOutboundTransport` protocol.
- DashScope adapter connection mapping.

Output:

- New `tests/test_realtime_dashscope_transport.py`.
- Tests for URL/header use, no secret in safe error, lazy connection, and fake transport compatibility.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_transport.py -v
```

Expected before implementation: fail.

Commit:

```bash
git add tests/test_realtime_dashscope_transport.py
git commit -m "test: specify dashscope outbound transport"
```

### Task 4.2: Implement DashScope outbound transport

Input:

- Failing tests from Task 4.1.

Output:

- New file `voiceagents/realtime/dashscope_transport.py`.
- Async transport with connect/send/receive/close.
- Isolated dependency import or standard-library fallback decision documented inline only where needed.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_transport.py -v
```

Expected: pass without network.

Commit:

```bash
git add voiceagents/realtime/dashscope_transport.py tests/test_realtime_dashscope_transport.py
git commit -m "feat: add dashscope outbound transport"
```

### Task 4.3: Wire real transport factory into app state

Input:

- `create_app(dashscope_upstream_transport=...)`.
- DashScope provider config.

Output:

- `create_app` can use injected fake transport in tests or construct real DashScope transport in local real-provider mode.
- Real transport is never constructed in mock/OpenAI mode.

Test:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py tests/test_api_realtime_client_secret.py -v
```

Expected: pass.

Commit:

```bash
git add voiceagents/api/app.py voiceagents/realtime/dashscope_transport.py tests/test_api_realtime_dashscope_proxy.py
git commit -m "feat: wire dashscope outbound transport factory"
```

## Phase 5: Browser DashScope Smoke Path

Goal: make `/realtime-test` useful for local real DashScope smoke testing without exposing secrets.

### Task 5.1: Add DashScope browser adapter static tests

Input:

- `voiceagents/api/static/realtime-test.html`.
- Existing OpenAI static adapter pattern.

Output:

- Tests requiring `/static/realtime-dashscope-adapter.js` route.
- Tests requiring DashScope adapter functions for proxy URL creation, safe event handling, audio/control send, and tool-result send.
- Tests proving adapter does not contain `DASHSCOPE_API_KEY`, `Authorization`, `tool_call_token`, `client_secret`, or raw audio persistence.

Test:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py -v
```

Expected before implementation: fail.

Commit:

```bash
git add tests/test_api_realtime_test_page.py
git commit -m "test: specify dashscope browser adapter"
```

### Task 5.2: Implement DashScope browser adapter route and module

Input:

- Failing tests from Task 5.1.

Output:

- New `voiceagents/api/static/realtime-dashscope-adapter.js`.
- New FastAPI static JS route.
- Adapter remains browser-safe.

Test:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py -v
```

Expected: pass.

Commit:

```bash
git add voiceagents/api/app.py voiceagents/api/static/realtime-dashscope-adapter.js tests/test_api_realtime_test_page.py
git commit -m "feat: add dashscope browser adapter module"
```

### Task 5.3: Add page harness tests for DashScope tool and audio flow

Input:

- `tests/test_realtime_test_page_failure_modes.py`.
- DashScope adapter module.

Output:

- Node harness tests for:
  - DashScope proxy connect;
  - control start sent once;
  - safe normalized transcript rendering;
  - no DashScope provider event relay to `/v1/realtime/event`;
  - provider tool request routed to backend;
  - tool result sent back to proxy;
  - reconnect cleanup closes WebSocket.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_test_page_failure_modes.py -v
```

Expected before implementation: fail on missing page wiring.

Commit:

```bash
git add tests/test_realtime_test_page_failure_modes.py
git commit -m "test: specify dashscope realtime page flow"
```

### Task 5.4: Wire `/realtime-test` to DashScope adapter

Input:

- Failing tests from Task 5.3.

Output:

- `realtime-test.html` loads DashScope adapter.
- Inline code delegates provider-specific behavior to adapter.
- OpenAI behavior remains unchanged.

Test:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py -v
```

Expected: pass.

Commit:

```bash
git add voiceagents/api/static/realtime-test.html tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py
git commit -m "feat: wire dashscope realtime test page"
```

## Phase 6: Documentation, Manual Check, And Branch Verification

Goal: make the real-provider test flow reproducible and reviewable before implementation is considered complete.

### Task 6.1: Update manual checklist tests and docs

Input:

- Implemented DashScope real outbound flow.
- Existing `docs/specs/voiceagents-dashscope-realtime-manual-checklist.md`.

Output:

- Checklist includes env vars, fake tests, API startup, browser flow, one voice response, one tool call, validation report, and failure modes.
- README and handoff mention real outbound status and safety boundaries.

Test:

```bash
git diff --check
rg -n "VOICEAGENTS_DASHSCOPE_API_KEY|VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS|server_websocket_proxy|real outbound" README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-dashscope-realtime-manual-checklist.md
```

Expected: no whitespace errors; required doc terms present.

Commit:

```bash
git add README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-dashscope-realtime-manual-checklist.md
git commit -m "docs: document dashscope realtime outbound check"
```

### Task 6.2: Run manual DashScope smoke verification

Input:

- Implemented DashScope real outbound flow.
- Updated manual checklist.
- Local server-only DashScope credentials supplied by the operator outside git.

Output:

- Manual verification summary in final response only.
- No raw audio, screenshots with secrets, Authorization headers, tokens, `.env`, provider payload dumps, or validation artifacts committed.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py tests/test_realtime_dashscope_adapter.py tests/test_realtime_dashscope_transport.py tests/test_api_realtime_dashscope_proxy.py -v
```

Then run the manual checklist in `docs/specs/voiceagents-dashscope-realtime-manual-checklist.md` with local env vars.

Expected: focused fake tests pass; manual checklist completes one real DashScope voice interaction and one real tool-call interaction.

Commit:

```bash
git status --short
```

No commit unless manual verification reveals a required docs-only correction.

### Task 6.3: Run focused realtime verification

Input:

- All implementation tasks complete.

Output:

- Focused suite result recorded in final summary, not committed as raw logs.

Test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py tests/test_realtime_dashscope_adapter.py tests/test_realtime_dashscope_transport.py tests/test_api_realtime_dashscope_proxy.py tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py -v
```

Expected: pass.

Commit:

```bash
git status --short
```

No commit unless verification reveals a required docs-only correction.

### Task 6.4: Run full verification

Input:

- Focused suite passing.

Output:

- Full test result and `git diff --check` result recorded in final summary.

Test:

```bash
./.venv/bin/python -m pytest
git diff --check
```

Expected: pass.

Commit:

```bash
git status --short
```

No commit unless verification reveals a required correction.

### Task 6.5: Run pre-landing review

Input:

- Full verification passing.
- Branch contains checkpoint commits.

Output:

- `$gstack-review` findings summarized.
- Findings fixed only after user approval if they change scope.

Test:

```bash
$gstack-review
```

Expected: project-level generated Codex skill `$gstack-review` completes before PR/merge. If manual helper commands are needed, run them with `env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" ...`.

Commit:

```bash
git status --short
```

Commit only if review fixes are applied.
