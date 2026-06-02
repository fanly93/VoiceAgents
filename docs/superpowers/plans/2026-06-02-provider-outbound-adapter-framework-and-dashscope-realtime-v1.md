# Provider Outbound Adapter Framework And DashScope Realtime V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This plan mirrors `docs/specs/voiceagents-provider-outbound-adapter-framework-and-dashscope-realtime-v1-tasks.md`; do not renumber or merge tasks during execution.

**Goal:** Build a provider-neutral outbound realtime adapter framework and implement DashScope Qwen-Omni-Realtime real server WebSocket connectivity for local testing.

**Architecture:** Keep VoiceAgents business tools, event ingestion, transcript logging, validation reports, and session binding provider-neutral. Add a fake-testable outbound transport and proxy coordinator under `voiceagents/realtime/`, then implement DashScope-specific protocol mapping and real WebSocket transport behind that interface. DashScope provider events are persisted by the server proxy path; the browser renders safe events but does not relay DashScope provider events to `/v1/realtime/event`.

**Tech Stack:** Python, FastAPI/Starlette WebSocket, Pydantic, pytest, Node-based static page harness tests, project-level gstack review.

---

## Source Documents

- Spec: `docs/specs/voiceagents-provider-outbound-adapter-framework-and-dashscope-realtime-v1.md`
- Tasks: `docs/specs/voiceagents-provider-outbound-adapter-framework-and-dashscope-realtime-v1-tasks.md`
- Design clarification: `docs/designs/voiceagents-provider-outbound-adapter-framework.md`

## Execution Rules

- Execute tasks in order.
- Each task is checkpoint-commit sized.
- For code behavior, write failing tests first, verify red, implement, verify green, then commit.
- Automated tests must not call real DashScope or require real provider credentials.
- Do not commit `.env`, API keys, Authorization headers, tokens, raw audio, SDP, raw provider payloads, screenshots with secrets, or real PII.
- Use project-level `$gstack-review` before PR/merge.

## File Map

- Create `voiceagents/realtime/outbound.py`: provider-neutral outbound event, proxy message, transport, and adapter contracts.
- Create `voiceagents/realtime/proxy.py`: authenticated browser/provider proxy coordinator.
- Create `voiceagents/realtime/dashscope_transport.py`: real DashScope outbound WebSocket transport behind the neutral protocol.
- Create `voiceagents/api/static/realtime-dashscope-adapter.js`: browser-safe DashScope proxy adapter.
- Modify `voiceagents/realtime/dashscope.py`: DashScope URL/header/session/tool/event/result mapping.
- Modify `voiceagents/api/app.py`: static JS route and DashScope proxy delegation/factory wiring.
- Modify `voiceagents/api/static/realtime-test.html`: load and call DashScope adapter while preserving OpenAI path.
- Modify tests under `tests/`: fake-only coverage for contracts, adapter, transport, proxy, and page flow.
- Modify docs: README, handoff, DashScope manual checklist.

## Phase 1: Provider-Neutral Outbound Contracts

### Task 1.1: Add outbound transport contract tests

**Files:**
- Create: `tests/test_realtime_outbound_contracts.py`

- [ ] **Step 1: Write failing tests**

Cover transport event shape, browser proxy envelope shape, blocked keys, and safe error shape.

- [ ] **Step 2: Verify red**

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py -v
```

Expected: fail because `voiceagents.realtime.outbound` does not exist.

- [ ] **Step 3: Commit**

```bash
git add tests/test_realtime_outbound_contracts.py
git commit -m "test: specify realtime outbound contracts"
```

### Task 1.2: Implement outbound contract models

**Files:**
- Create: `voiceagents/realtime/outbound.py`
- Modify: `tests/test_realtime_outbound_contracts.py`

- [ ] **Step 1: Implement minimal models and protocols**

Add outbound JSON/audio/close/error event models, browser proxy message models, and async transport protocol.

- [ ] **Step 2: Verify green**

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/realtime/outbound.py tests/test_realtime_outbound_contracts.py
git commit -m "feat: add realtime outbound contracts"
```

### Task 1.3: Specify provider adapter protocol tests

**Files:**
- Modify: `tests/test_realtime_outbound_contracts.py`

- [ ] **Step 1: Write failing tests**

Specify URL/header/session/tool/event/result adapter behavior without provider secret leakage.

- [ ] **Step 2: Verify red**

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py -v
```

Expected: fail on missing adapter protocol.

- [ ] **Step 3: Commit**

```bash
git add tests/test_realtime_outbound_contracts.py
git commit -m "test: specify realtime provider adapter protocol"
```

### Task 1.4: Implement provider adapter protocol

**Files:**
- Modify: `voiceagents/realtime/outbound.py`
- Modify: `tests/test_realtime_outbound_contracts.py`

- [ ] **Step 1: Implement protocol**

Add `NativeRealtimeProviderAdapter` protocol only; do not add provider-specific behavior here.

- [ ] **Step 2: Verify green**

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/realtime/outbound.py tests/test_realtime_outbound_contracts.py
git commit -m "feat: add native realtime adapter protocol"
```

## Phase 2: DashScope Protocol Adapter

### Task 2.1: Add DashScope URL and header tests

**Files:**
- Modify: `tests/test_realtime_dashscope_adapter.py`

- [ ] **Step 1: Write failing tests**

Cover default URL, configured base URL, model query param, Authorization header construction, and secret-free summaries/dumps.

- [ ] **Step 2: Verify red**

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Expected: fail on missing adapter class/functions.

- [ ] **Step 3: Commit**

```bash
git add tests/test_realtime_dashscope_adapter.py
git commit -m "test: specify dashscope realtime connection mapping"
```

### Task 2.2: Implement DashScope connection mapping

**Files:**
- Modify: `voiceagents/realtime/dashscope.py`
- Modify: `tests/test_realtime_dashscope_adapter.py`

- [ ] **Step 1: Implement connection mapping**

Add DashScope URL/header builders without logging or returning provider secrets to browser-safe DTOs.

- [ ] **Step 2: Verify green**

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/realtime/dashscope.py tests/test_realtime_dashscope_adapter.py
git commit -m "feat: map dashscope realtime connection settings"
```

### Task 2.3: Add DashScope session.update and tool declaration tests

**Files:**
- Modify: `tests/test_realtime_dashscope_adapter.py`

- [ ] **Step 1: Write failing tests**

Cover instructions, response mode, voice, audio formats, VAD config, allowed tools, and absence of unsupported `tool_choice` / `parallel_tool_calls`.

- [ ] **Step 2: Verify red**

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Expected: fail on missing session/tool mapping.

- [ ] **Step 3: Commit**

```bash
git add tests/test_realtime_dashscope_adapter.py
git commit -m "test: specify dashscope session and tool mapping"
```

### Task 2.4: Implement DashScope session.update and tool declaration mapping

**Files:**
- Modify: `voiceagents/realtime/dashscope.py`
- Modify: `tests/test_realtime_dashscope_adapter.py`

- [ ] **Step 1: Implement mapping**

Add session setup message builder and DashScope tool declaration mapper.

- [ ] **Step 2: Verify green**

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/realtime/dashscope.py tests/test_realtime_dashscope_adapter.py
git commit -m "feat: map dashscope session tools"
```

### Task 2.5: Add DashScope provider event fixture tests

**Files:**
- Modify: `tests/test_realtime_dashscope_adapter.py`

- [ ] **Step 1: Write failing tests**

Cover official session, transcript, audio transport-only, function-call, response done, and safe error events.

- [ ] **Step 2: Verify red**

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Expected: fail for unmapped official event names.

- [ ] **Step 3: Commit**

```bash
git add tests/test_realtime_dashscope_adapter.py
git commit -m "test: specify dashscope official event normalization"
```

### Task 2.6: Implement DashScope official event normalization

**Files:**
- Modify: `voiceagents/realtime/dashscope.py`
- Modify: `tests/test_realtime_dashscope_adapter.py`

- [ ] **Step 1: Implement event normalization**

Map loggable events into VoiceAgents contracts and raw audio/audio deltas into transport-only events.

- [ ] **Step 2: Verify green**

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/realtime/dashscope.py tests/test_realtime_dashscope_adapter.py
git commit -m "feat: normalize dashscope realtime events"
```

## Phase 3: Proxy Coordinator And Fake Transport

### Task 3.1: Add proxy coordinator auth tests

**Files:**
- Modify: `tests/test_api_realtime_dashscope_proxy.py`

- [ ] **Step 1: Write failing tests**

Cover missing token, wrong session, wrong provider, expired token, invalid envelope, and no provider connect before auth.

- [ ] **Step 2: Verify red**

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py -v
```

Expected: existing tests pass; new ordering assertions may fail.

- [ ] **Step 3: Commit**

```bash
git add tests/test_api_realtime_dashscope_proxy.py
git commit -m "test: specify realtime proxy coordinator auth"
```

### Task 3.2: Implement proxy coordinator auth path

**Files:**
- Create: `voiceagents/realtime/proxy.py`
- Modify: `voiceagents/api/app.py`
- Modify: `tests/test_api_realtime_dashscope_proxy.py`

- [ ] **Step 1: Implement auth-first coordinator**

Authenticate browser token/session/provider before provider transport construction.

- [ ] **Step 2: Verify green**

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/realtime/proxy.py voiceagents/api/app.py tests/test_api_realtime_dashscope_proxy.py
git commit -m "feat: add realtime proxy coordinator auth"
```

### Task 3.3: Add fake transport relay tests

**Files:**
- Modify: `tests/test_api_realtime_dashscope_proxy.py`

- [ ] **Step 1: Write failing tests**

Cover browser control -> provider, provider transcript -> browser, server-side event persistence exactly once, provider tool request -> backend router, backend result -> provider, and disconnect -> safe close.

- [ ] **Step 2: Verify red**

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py -v
```

Expected: fail for tool, persistence, and disconnect relay paths.

- [ ] **Step 3: Commit**

```bash
git add tests/test_api_realtime_dashscope_proxy.py
git commit -m "test: specify realtime proxy fake relay"
```

### Task 3.4: Implement fake transport event relay and persistence

**Files:**
- Modify: `voiceagents/realtime/proxy.py`
- Modify: `voiceagents/api/app.py`
- Modify: `tests/test_api_realtime_dashscope_proxy.py`

- [ ] **Step 1: Implement relay**

Relay safe browser messages and provider events, then persist DashScope loggable events server-side exactly once.

- [ ] **Step 2: Verify partial green**

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py tests/test_realtime_dashscope_adapter.py -v
```

Expected: event relay and persistence assertions pass; tool/disconnect assertions may still fail.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/realtime/proxy.py voiceagents/api/app.py tests/test_api_realtime_dashscope_proxy.py
git commit -m "feat: persist dashscope proxy events"
```

### Task 3.5: Implement provider tool-call routing and result relay

**Files:**
- Modify: `voiceagents/realtime/proxy.py`
- Modify: `voiceagents/api/app.py`
- Modify: `tests/test_api_realtime_dashscope_proxy.py`

- [ ] **Step 1: Implement tool handling**

Route provider tool calls through `RealtimeToolRouter` and send provider-specific tool results.

- [ ] **Step 2: Verify partial green**

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py tests/test_realtime_dashscope_adapter.py -v
```

Expected: tool request/result relay assertions pass; disconnect assertions may still fail.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/realtime/proxy.py voiceagents/api/app.py tests/test_api_realtime_dashscope_proxy.py
git commit -m "feat: route dashscope proxy tool calls"
```

### Task 3.6: Implement provider disconnect cleanup

**Files:**
- Modify: `voiceagents/realtime/proxy.py`
- Modify: `voiceagents/api/app.py`
- Modify: `tests/test_api_realtime_dashscope_proxy.py`

- [ ] **Step 1: Implement cleanup**

Close browser and provider sides deterministically on provider disconnect, browser disconnect, and validation failure.

- [ ] **Step 2: Verify green**

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py tests/test_realtime_dashscope_adapter.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/realtime/proxy.py voiceagents/api/app.py tests/test_api_realtime_dashscope_proxy.py
git commit -m "feat: close dashscope proxy cleanly"
```

## Phase 4: Real DashScope Outbound Transport

### Task 4.0: Decide outbound WebSocket dependency

**Files:**
- Modify: `docs/specs/voiceagents-dashscope-realtime-manual-checklist.md`
- Modify: `docs/specs/voiceagents-provider-outbound-adapter-framework-and-dashscope-realtime-v1.md`

- [ ] **Step 1: Record dependency decision**

Document whether to use an existing dependency, add a new dependency, or isolate an optional import. Include fake-client test strategy.

- [ ] **Step 2: Verify docs**

```bash
git diff --check
rg -n "DashScope outbound WebSocket|fake transport|network" docs/specs/voiceagents-dashscope-realtime-manual-checklist.md docs/specs/voiceagents-provider-outbound-adapter-framework-and-dashscope-realtime-v1.md
```

Expected: no whitespace errors; dependency and fake-test boundary are documented.

- [ ] **Step 3: Commit**

```bash
git add docs/specs/voiceagents-dashscope-realtime-manual-checklist.md docs/specs/voiceagents-provider-outbound-adapter-framework-and-dashscope-realtime-v1.md
git commit -m "docs: decide dashscope outbound transport dependency"
```

### Task 4.1: Add DashScope transport construction tests

**Files:**
- Create: `tests/test_realtime_dashscope_transport.py`

- [ ] **Step 1: Write failing tests**

Cover URL/header use, no secret in safe error, lazy connection, fake client injection, and close behavior.

- [ ] **Step 2: Verify red**

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_transport.py -v
```

Expected: fail because `voiceagents.realtime.dashscope_transport` does not exist.

- [ ] **Step 3: Commit**

```bash
git add tests/test_realtime_dashscope_transport.py
git commit -m "test: specify dashscope outbound transport"
```

### Task 4.2: Implement DashScope outbound transport

**Files:**
- Create: `voiceagents/realtime/dashscope_transport.py`
- Modify: `tests/test_realtime_dashscope_transport.py`

- [ ] **Step 1: Implement fake-injectable transport**

Add async connect/send/receive/close with injectable client factory. Tests must not open network connections.

- [ ] **Step 2: Verify green**

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_transport.py -v
```

Expected: pass without network.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/realtime/dashscope_transport.py tests/test_realtime_dashscope_transport.py
git commit -m "feat: add dashscope outbound transport"
```

### Task 4.3: Wire real transport factory into app state

**Files:**
- Modify: `voiceagents/api/app.py`
- Modify: `voiceagents/realtime/dashscope_transport.py`
- Modify: `tests/test_api_realtime_dashscope_proxy.py`

- [ ] **Step 1: Wire factory**

Use injected fake transport in tests or construct real transport in DashScope proxy mode only.

- [ ] **Step 2: Verify green**

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py tests/test_api_realtime_client_secret.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/api/app.py voiceagents/realtime/dashscope_transport.py tests/test_api_realtime_dashscope_proxy.py
git commit -m "feat: wire dashscope outbound transport factory"
```

## Phase 5: Browser DashScope Smoke Path

### Task 5.1: Add DashScope browser adapter static tests

**Files:**
- Modify: `tests/test_api_realtime_test_page.py`

- [ ] **Step 1: Write failing tests**

Cover `/static/realtime-dashscope-adapter.js` route, adapter functions, and absence of secret-bearing strings.

- [ ] **Step 2: Verify red**

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py -v
```

Expected: fail because adapter route/module is missing.

- [ ] **Step 3: Commit**

```bash
git add tests/test_api_realtime_test_page.py
git commit -m "test: specify dashscope browser adapter"
```

### Task 5.2: Implement DashScope browser adapter route and module

**Files:**
- Create: `voiceagents/api/static/realtime-dashscope-adapter.js`
- Modify: `voiceagents/api/app.py`
- Modify: `tests/test_api_realtime_test_page.py`

- [ ] **Step 1: Implement route and module**

Serve a browser-safe DashScope adapter. Do not include provider API keys, Authorization headers, token rendering, or raw audio persistence.

- [ ] **Step 2: Verify green**

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/api/app.py voiceagents/api/static/realtime-dashscope-adapter.js tests/test_api_realtime_test_page.py
git commit -m "feat: add dashscope browser adapter module"
```

### Task 5.3: Add page harness tests for DashScope tool and audio flow

**Files:**
- Modify: `tests/test_realtime_test_page_failure_modes.py`

- [ ] **Step 1: Write failing tests**

Cover proxy connect, control start, safe transcript rendering, no DashScope browser relay to `/v1/realtime/event`, backend tool relay, provider tool result send, and reconnect cleanup.

- [ ] **Step 2: Verify red**

```bash
./.venv/bin/python -m pytest tests/test_realtime_test_page_failure_modes.py -v
```

Expected: fail on missing page wiring.

- [ ] **Step 3: Commit**

```bash
git add tests/test_realtime_test_page_failure_modes.py
git commit -m "test: specify dashscope realtime page flow"
```

### Task 5.4: Wire `/realtime-test` to DashScope adapter

**Files:**
- Modify: `voiceagents/api/static/realtime-test.html`
- Modify: `tests/test_api_realtime_test_page.py`
- Modify: `tests/test_realtime_test_page_failure_modes.py`

- [ ] **Step 1: Wire page**

Load DashScope adapter and delegate DashScope proxy behavior to it. Preserve OpenAI WebRTC behavior.

- [ ] **Step 2: Verify green**

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add voiceagents/api/static/realtime-test.html tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py
git commit -m "feat: wire dashscope realtime test page"
```

## Phase 6: Documentation, Manual Check, And Branch Verification

### Task 6.1: Update manual checklist tests and docs

**Files:**
- Modify: `docs/specs/voiceagents-dashscope-realtime-manual-checklist.md`
- Modify: `README.md`
- Modify: `OPENAI_REALTIME_VOICE_MVP_HANDOFF.md`

- [ ] **Step 1: Update docs**

Document real outbound status, env vars, fake tests, manual smoke flow, and failure modes.

- [ ] **Step 2: Verify docs**

```bash
git diff --check
rg -n "VOICEAGENTS_DASHSCOPE_API_KEY|VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS|server_websocket_proxy|real outbound" README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-dashscope-realtime-manual-checklist.md
```

Expected: no whitespace errors and required terms present.

- [ ] **Step 3: Commit**

```bash
git add README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-dashscope-realtime-manual-checklist.md
git commit -m "docs: document dashscope realtime outbound check"
```

### Task 6.2: Run manual DashScope smoke verification

**Files:**
- No planned file edits.

- [ ] **Step 1: Run focused fake tests**

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py tests/test_realtime_dashscope_adapter.py tests/test_realtime_dashscope_transport.py tests/test_api_realtime_dashscope_proxy.py -v
```

Expected: pass.

- [ ] **Step 2: Run manual checklist**

Use `docs/specs/voiceagents-dashscope-realtime-manual-checklist.md` with local env vars supplied outside git.

Expected: one real DashScope voice interaction and one real tool-call interaction complete without secret leakage.

- [ ] **Step 3: Confirm no artifacts**

```bash
git status --short
```

Expected: no raw audio, screenshots with secrets, Authorization headers, tokens, `.env`, or provider payload dumps are staged or committed.

### Task 6.3: Run focused realtime verification

**Files:**
- No planned file edits.

- [ ] **Step 1: Run focused suite**

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py tests/test_realtime_dashscope_adapter.py tests/test_realtime_dashscope_transport.py tests/test_api_realtime_dashscope_proxy.py tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py -v
```

Expected: pass.

### Task 6.4: Run full verification

**Files:**
- No planned file edits.

- [ ] **Step 1: Run full suite**

```bash
./.venv/bin/python -m pytest
git diff --check
```

Expected: pass.

### Task 6.5: Run pre-landing review

**Files:**
- No planned file edits unless review findings require fixes.

- [ ] **Step 1: Invoke project-level review skill**

Use the generated Codex skill:

```text
$gstack-review
```

Expected: review completed before PR/merge.

- [ ] **Step 2: Fix approved findings**

If review findings change scope, ask for user approval before editing. If findings are small correctness fixes, use TDD and checkpoint commits.

## Self-Review Checklist

- [ ] Every spec acceptance criterion maps to at least one task.
- [ ] Task numbering in this plan mirrors the tasks document.
- [ ] No task requires real DashScope credentials in automated tests.
- [ ] Manual real-provider verification is documented but does not commit raw artifacts.
- [ ] OpenAI behavior is preserved.
- [ ] DashScope-specific behavior lives in DashScope adapter/transport/browser module, not business tool adapters.
- [ ] GLM and Volc are follow-up adapters, not hidden scope in this branch.
