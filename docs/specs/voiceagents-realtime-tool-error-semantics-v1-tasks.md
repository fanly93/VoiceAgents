# VoiceAgents Realtime Tool Error Semantics v1 Tasks

Status: DRAFT / IN PROGRESS
Source spec: `docs/specs/voiceagents-realtime-tool-error-semantics-v1.md`
Branch: `feat/realtime-tool-error-semantics`

Rules:

- Use TDD: write focused failing tests before implementation.
- Use `./.venv/bin/python` for Python commands.
- Commit each independently verified checkpoint.
- Do not write or commit `.voiceagents/` artifacts.
- Do not print or persist API keys, client secrets, tool tokens, Authorization headers, SDP, raw audio, raw tool arguments, or real PII.
- Do not implement new providers in this branch.

## Phase 1: Tool Response Contract

Goal: add explicit safe tool-call status semantics.

Primary files:

- Modify `voiceagents/realtime/contracts.py`
- Modify `voiceagents/realtime/tool_router.py`
- Modify `tests/test_realtime_contracts.py`
- Modify `tests/test_realtime_tool_router.py`

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_contracts.py tests/test_realtime_tool_router.py -v
```

Checkpoint:

```bash
git add voiceagents/realtime/contracts.py voiceagents/realtime/tool_router.py tests/test_realtime_contracts.py tests/test_realtime_tool_router.py
git commit -m "feat: add realtime tool status semantics"
```

## Phase 2: API Error Details And Event Logging

Goal: return structured safe request-level errors and log response tool status.

Primary files:

- Modify `voiceagents/api/app.py`
- Modify `tests/test_api_realtime_tool_call.py`

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_tool_call.py -v
```

Checkpoint:

```bash
git add voiceagents/api/app.py tests/test_api_realtime_tool_call.py
git commit -m "feat: structure realtime tool-call errors"
```

## Phase 3: Frontend Relay Compatibility And Docs

Goal: keep `/realtime-test` provider relay compatible with new tool response semantics and update handoff docs.

Primary files:

- Modify `voiceagents/api/static/realtime-test.html`
- Modify `tests/test_api_realtime_test_page.py`
- Modify `README.md`
- Modify `OPENAI_REALTIME_VOICE_MVP_HANDOFF.md`
- Update this task file and source spec status.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py -v
rg -n "tool_status|error_message|Realtime Tool Error Semantics" README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-realtime-tool-error-semantics-v1.md docs/specs/voiceagents-realtime-tool-error-semantics-v1-tasks.md
git diff --check
```

Checkpoint:

```bash
git add voiceagents/api/static/realtime-test.html tests/test_api_realtime_test_page.py README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-realtime-tool-error-semantics-v1.md docs/specs/voiceagents-realtime-tool-error-semantics-v1-tasks.md
git commit -m "docs: document realtime tool error semantics"
```

