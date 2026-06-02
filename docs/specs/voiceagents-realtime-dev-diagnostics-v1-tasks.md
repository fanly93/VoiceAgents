# VoiceAgents Realtime Dev Diagnostics v1 Tasks

Status: DRAFT / IN PROGRESS
Source spec: `docs/specs/voiceagents-realtime-dev-diagnostics-v1.md`
Branch: `feat/realtime-dev-diagnostics`

Rules:

- Use TDD: write focused failing tests before implementation.
- Use `./.venv/bin/python` for Python commands.
- Commit each independently verified checkpoint.
- Do not write or commit `.voiceagents/` artifacts.
- Do not print or persist API keys, client secrets, tool tokens, Authorization headers, SDP, raw audio, or real PII.
- Do not work on report viewer, public sharing/auth, merchant frontend, or support workbench tasks.

## Phase 1: Backend Diagnostics Contract

Goal: expose safe realtime dev diagnostics without calling any provider.

Primary files:

- Create `voiceagents/realtime/diagnostics.py`
- Modify `voiceagents/api/app.py`
- Create `tests/test_realtime_diagnostics.py`
- Create or modify `tests/test_api_realtime_diagnostics.py`

### Task 1.1: Add Diagnostics Models And Environment Checks

Purpose: model pass/warn/fail checks for realtime dev preflight.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_diagnostics.py -v
```

Checkpoint:

```bash
git add voiceagents/realtime/diagnostics.py tests/test_realtime_diagnostics.py
git commit -m "feat: add realtime diagnostics checks"
```

### Task 1.2: Expose Dev Diagnostics Endpoint

Purpose: return safe server-side diagnostics from `GET /v1/realtime/dev-diagnostics`.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_diagnostics.py -v
```

Checkpoint:

```bash
git add voiceagents/api/app.py tests/test_api_realtime_diagnostics.py
git commit -m "feat: expose realtime dev diagnostics"
```

## Phase 2: Realtime Test Page Diagnostics

Goal: let a developer run diagnostics from `/realtime-test` before starting a session.

Primary files:

- Modify `voiceagents/api/static/realtime-test.html`
- Modify `tests/test_api_realtime_test_page.py`
- Modify `tests/test_realtime_test_page_failure_modes.py` or add a focused JS harness test

### Task 2.1: Add Diagnostics Button And Safe Panel

Purpose: render diagnostics output without exposing secrets.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py -v
```

Checkpoint:

```bash
git add voiceagents/api/static/realtime-test.html tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py
git commit -m "feat: show realtime diagnostics on test page"
```

## Phase 3: Local Diagnostics Script And Docs

Goal: allow a developer to run the preflight from terminal against a running local API.

Primary files:

- Create `scripts/diagnose_realtime_dev.py`
- Create `tests/test_diagnose_realtime_dev_cli.py`
- Modify `README.md`
- Modify `OPENAI_REALTIME_VOICE_MVP_HANDOFF.md`

### Task 3.1: Add Local Diagnostics Script

Purpose: check `/health` and `/v1/realtime/dev-diagnostics`, print safe results, and exit non-zero on fail.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_diagnose_realtime_dev_cli.py -v
```

Checkpoint:

```bash
git add scripts/diagnose_realtime_dev.py tests/test_diagnose_realtime_dev_cli.py
git commit -m "feat: add realtime diagnostics script"
```

### Task 3.2: Document Diagnostics Usage And Handoff

Purpose: explain when to use diagnostics and keep future session handoff aligned.

Validation:

```bash
rg -n "diagnose_realtime_dev|dev-diagnostics|Realtime Voice Dev Diagnostics" README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-realtime-dev-diagnostics-v1.md docs/specs/voiceagents-realtime-dev-diagnostics-v1-tasks.md
git diff --check
```

Checkpoint:

```bash
git add README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-realtime-dev-diagnostics-v1.md docs/specs/voiceagents-realtime-dev-diagnostics-v1-tasks.md
git commit -m "docs: document realtime dev diagnostics"
```

