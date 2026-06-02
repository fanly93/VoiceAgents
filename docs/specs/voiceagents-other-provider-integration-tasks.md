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

## Phase 0: Planning Documents

Goal: lock the provider-neutral design before implementation.

Primary files:

- `docs/designs/voiceagents-other-provider-integration.md`
- `docs/specs/voiceagents-other-provider-integration.md`
- `docs/specs/voiceagents-other-provider-integration-tasks.md`

### Task 0.1: Complete Office-Hours Design And Specs

Status: DONE

Purpose: answer whether the current architecture is OpenAI-locked, define provider-neutral target architecture, choose DashScope first target, and split implementation tasks.

Validation:

```bash
rg -n "DashScope|NativeRealtimeVoiceProvider|CascadedVoiceProvider|qwen3.5-omni-flash-realtime|server_websocket_proxy" docs/designs/voiceagents-other-provider-integration.md docs/specs/voiceagents-other-provider-integration.md docs/specs/voiceagents-other-provider-integration-tasks.md
git diff --check
```

Checkpoint:

```bash
git add docs/designs/voiceagents-other-provider-integration.md docs/specs/voiceagents-other-provider-integration.md docs/specs/voiceagents-other-provider-integration-tasks.md
git commit -m "docs: plan other provider integration"
```

## Phase 1: Provider-Neutral Contracts

Goal: make provider capability and connection semantics explicit before adding DashScope implementation.

Primary files:

- `voiceagents/realtime/contracts.py`
- `voiceagents/realtime/providers.py` or new provider registry module
- `tests/test_realtime_contracts.py`
- `tests/test_realtime_providers.py`

### Task 1.1: Add Provider Capabilities And Connection Modes

Status: TODO

Purpose: model native realtime versus cascaded providers and browser-safe connection metadata.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_contracts.py -v
```

Checkpoint:

```bash
git add voiceagents/realtime/contracts.py tests/test_realtime_contracts.py
git commit -m "feat: add realtime provider capability contracts"
```

### Task 1.2: Add Provider Registry And Factory Tests

Status: TODO

Purpose: construct providers through a registry instead of scattered provider-specific branches.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_providers.py -v
```

Checkpoint:

```bash
git add voiceagents/realtime/providers.py tests/test_realtime_providers.py
git commit -m "feat: add realtime provider registry"
```

## Phase 2: Session-Bound Tool Provider Semantics

Goal: remove the multi-provider risk where tool-call execution reads provider from process env instead of the session binding.

Primary files:

- `voiceagents/api/app.py`
- `voiceagents/realtime/session_store.py`
- `voiceagents/realtime/tool_router.py`
- `tests/test_api_realtime_tool_call.py`
- `tests/test_realtime_session_store.py`

### Task 2.1: Resolve Tool Provider From Session Binding

Status: TODO

Purpose: ensure existing sessions remain bound to their original provider even if `VOICEAGENTS_REALTIME_PROVIDER` changes later.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_tool_call.py tests/test_realtime_session_store.py -v
```

Checkpoint:

```bash
git add voiceagents/api/app.py voiceagents/realtime/session_store.py voiceagents/realtime/tool_router.py tests/test_api_realtime_tool_call.py tests/test_realtime_session_store.py
git commit -m "fix: bind realtime tool calls to session provider"
```

## Phase 3: Provider Diagnostics Generalization

Goal: let diagnostics explain mock, OpenAI, DashScope, and unsupported provider setup safely.

Primary files:

- `voiceagents/realtime/diagnostics.py`
- `tests/test_realtime_diagnostics.py`
- `tests/test_api_realtime_diagnostics.py`
- `scripts/diagnose_realtime_dev.py`
- `README.md`

### Task 3.1: Add Provider-Specific Diagnostics Registry

Status: TODO

Purpose: make diagnostics extensible without adding more OpenAI-specific branches.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_diagnostics.py tests/test_api_realtime_diagnostics.py tests/test_diagnose_realtime_dev_cli.py -v
```

Checkpoint:

```bash
git add voiceagents/realtime/diagnostics.py tests/test_realtime_diagnostics.py tests/test_api_realtime_diagnostics.py scripts/diagnose_realtime_dev.py README.md
git commit -m "feat: generalize realtime provider diagnostics"
```

## Phase 4: DashScope Realtime Provider Skeleton

Goal: add DashScope Qwen-Omni Realtime as a provider behind server-side credentials, using fake transports first.

Primary files:

- `voiceagents/realtime/providers.py` or `voiceagents/realtime/dashscope.py`
- `tests/test_realtime_dashscope_provider.py`
- `README.md`

### Task 4.1: Add DashScope Provider Config And Safe Credential Handling

Status: TODO

Purpose: support `dashscope_realtime` provider config without calling DashScope in automated tests.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_provider.py tests/test_realtime_providers.py -v
```

Checkpoint:

```bash
git add voiceagents/realtime/providers.py voiceagents/realtime/dashscope.py tests/test_realtime_dashscope_provider.py README.md
git commit -m "feat: add dashscope realtime provider config"
```

### Task 4.2: Add DashScope Event Adapter Tests

Status: TODO

Purpose: map DashScope Qwen-Omni realtime events into VoiceAgents normalized transcript, tool-call, response, and error events.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_adapter.py -v
```

Checkpoint:

```bash
git add voiceagents/realtime/dashscope.py tests/test_realtime_dashscope_adapter.py
git commit -m "feat: normalize dashscope realtime events"
```

## Phase 5: Server WebSocket Proxy Path

Goal: keep DashScope API keys server-side while allowing the browser test page to run a DashScope realtime session.

Primary files:

- `voiceagents/api/app.py`
- `voiceagents/api/static/realtime-test.html`
- new DashScope browser adapter if needed
- `tests/test_api_realtime_test_page.py`
- provider/proxy focused tests

### Task 5.1: Add Browser-Safe DashScope Proxy Contract

Status: TODO

Purpose: expose only local VoiceAgents proxy metadata to the browser; never expose DashScope credentials.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py tests/test_api_realtime_client_secret.py -v
```

Checkpoint:

```bash
git add voiceagents/api/app.py voiceagents/api/static/realtime-test.html tests/test_api_realtime_test_page.py tests/test_api_realtime_client_secret.py
git commit -m "feat: add dashscope realtime proxy contract"
```

## Phase 6: Manual Real Provider Verification

Goal: validate DashScope against a real account only after fake-transport tests pass.

Primary files:

- `docs/specs/voiceagents-dashscope-realtime-manual-checklist.md`
- `OPENAI_REALTIME_VOICE_MVP_HANDOFF.md`
- `README.md`

### Task 6.1: Add DashScope Manual Checklist

Status: TODO

Purpose: document local real-provider validation steps, expected events, failure classes, and safe evidence capture.

Validation:

```bash
rg -n "dashscope_realtime|DASHSCOPE_API_KEY|qwen3.5-omni-flash-realtime" README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-dashscope-realtime-manual-checklist.md
git diff --check
```

Checkpoint:

```bash
git add README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-dashscope-realtime-manual-checklist.md
git commit -m "docs: add dashscope realtime validation checklist"
```
