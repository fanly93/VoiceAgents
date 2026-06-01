# VoiceAgents Pilot Demo Report Viewer Tasks

Status: REVIEWED / READY FOR IMPLEMENTATION
Source spec: `docs/specs/voiceagents-pilot-demo-report-viewer.md`
Source design: `docs/designs/voiceagents-pilot-demo-report-viewer.md`
Consistency review: `docs/reviews/autoplan-pilot-demo-report-viewer-2026-06-02.md`
Branch: `feat/pilot-demo-report-viewer`

This document is the project-level task tracker for the Pilot Demo Report Viewer. The implementation must remain local-only, restrained, easy to understand, and safe to forward.

Rules:

- Use the isolated project virtual environment for Python commands: `./.venv/bin/python`.
- Do not use system Python.
- Do not save or render raw audio, SDP, client secrets, API keys, tool tokens, Authorization headers, raw tool arguments, real PII, or unredacted transcripts.
- Do not commit `.voiceagents/validation-runs/` output artifacts.
- Avoid flashy frontend work; prioritize readable information architecture and Chinese-first copyable summaries.
- Keep v1 to one selected run at a time. Multi-run packets are deferred.
- Keep each task small enough for a focused test and checkpoint commit.

---

## Phase 1: Report View Contracts

Goal: define the decision-friendly report view model before adding endpoints or UI.

Primary files:

- Modify or extend `voiceagents/realtime/validation.py`
- Create or extend `tests/test_realtime_validation.py`

### Task 1.1: Add Readiness Derivation

Purpose: convert validation checks into boss-readable readiness.

Outputs:

- Readiness values:
  - `ready_for_pilot`
  - `needs_another_validation`
  - `blocked`
- Deterministic derivation from `ValidationRunSummary`.
- Tests for pass, non-critical fail, provider-error fail, and blocked-secret fail.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py -k "readiness" -v
```

Checkpoint:

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: derive validation report readiness"
```

### Task 1.2: Add Report View Models

Purpose: create a backend-safe response shape for the viewer.

Outputs:

- `ValidationRunListItem`
- `ValidationRunReport`
- decision summary fields
- audience sections
- copy summary text
- warning list for failed checks
- no absolute local filesystem paths in report responses

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py -k "report_view" -v
```

Checkpoint:

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: add validation report view model"
```

---

## Phase 2: Local Report Repository Reads

Goal: safely list and load existing validation summaries from `.voiceagents/validation-runs/`.

Primary files:

- Modify `voiceagents/realtime/validation.py`
- Extend `tests/test_realtime_validation.py`

### Task 2.1: List Saved Validation Runs

Purpose: let the viewer find recent local validation runs.

Outputs:

- repository method to list saved runs newest first
- newest run can be selected by the UI without a separate endpoint
- graceful behavior when root directory does not exist
- malformed run directories skipped or surfaced safely

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py -k "list_saved_runs" -v
```

Checkpoint:

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: list saved validation runs"
```

### Task 2.2: Load One Report Safely

Purpose: read a single run by server-validated `run_id` and build the report model.

Outputs:

- repository method to load one run report
- path safety for `run_id`
- missing run and malformed summary errors
- serialized report blocked-token safety scan

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py -k "load_report" -v
```

Checkpoint:

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: load validation report safely"
```

---

## Phase 3: API Endpoints

Goal: expose local read-only endpoints for the report viewer.

Primary files:

- Modify `voiceagents/api/app.py`
- Create or extend `tests/test_api_realtime_validation.py`

### Task 3.1: Add Run List Endpoint

Endpoint:

```text
GET /v1/realtime/validation-report-runs
```

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_validation.py -k "validation_report_runs" -v
```

Checkpoint:

```bash
git add voiceagents/api/app.py tests/test_api_realtime_validation.py
git commit -m "feat: expose validation report run list"
```

### Task 3.2: Add Run Detail Endpoint

Endpoint:

```text
GET /v1/realtime/validation-report-runs/{run_id}
```

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_validation.py -k "validation_report_detail" -v
```

Checkpoint:

```bash
git add voiceagents/api/app.py tests/test_api_realtime_validation.py
git commit -m "feat: expose validation report detail"
```

---

## Phase 4: Static Report Viewer Page

Goal: provide a readable local page for recent runs and one selected run.

Primary files:

- Create `voiceagents/api/static/realtime-validation-reports.html`
- Modify `voiceagents/api/app.py`
- Create `tests/test_api_realtime_validation_report_page.py`
- Create `tests/test_realtime_validation_report_page.py`
- Extend API/static page tests as needed

### Task 4.1: Serve Report Viewer Page

Purpose: add the local page route and static shell.

Route:

```text
/realtime-validation-reports
```

Required shell elements:

- run list
- readiness banner
- scenario coverage section
- business proof section
- audience sections
- copy summary textarea or panel
- copy button
- empty state
- error state

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_validation_report_page.py -k "validation_reports" -v
```

Checkpoint:

```bash
git add voiceagents/api/app.py voiceagents/api/static/realtime-validation-reports.html tests/test_api_realtime_validation_report_page.py
git commit -m "feat: serve validation report viewer"
```

### Task 4.2: Load Runs And Render Empty/Error States

Purpose: show useful state before a report exists and when loading fails.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation_report_page.py -k "load_runs" -v
```

Checkpoint:

```bash
git add voiceagents/api/static/realtime-validation-reports.html tests/test_realtime_validation_report_page.py
git commit -m "feat: load validation report runs"
```

### Task 4.3: Render Selected Run Detail

Purpose: make one validation run understandable in 30 seconds.

Required rendering:

- readiness label
- scenario label
- pass/fail check summary
- business proof bullets
- boss / decision-maker section
- customer-service section
- technical section
- warnings for failed checks

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation_report_page.py -k "render_report_detail" -v
```

Checkpoint:

```bash
git add voiceagents/api/static/realtime-validation-reports.html tests/test_realtime_validation_report_page.py
git commit -m "feat: render validation report detail"
```

### Task 4.4: Add Copyable WeChat/Feishu Summary

Purpose: replace manual post-demo rewriting.

Outputs:

- visible copy summary text
- copy button
- browser test for copied text or fallback selectable text
- Chinese-first summary includes scenario, readiness, evidence, and next action

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation_report_page.py -k "copy_summary" -v
```

Checkpoint:

```bash
git add voiceagents/api/static/realtime-validation-reports.html tests/test_realtime_validation_report_page.py
git commit -m "feat: add copyable validation report summary"
```

---

## Phase 5: Documentation And Verification

Goal: document usage, verify the branch, and run merge-before review.

### Task 5.1: Document Local Report Viewer Usage

Files:

- `README.md`
- `OPENAI_REALTIME_VOICE_MVP_HANDOFF.md`

Must document:

- local viewer URL,
- local-only artifact boundary,
- no public sharing/auth in v1,
- report prep target: 1-3 minutes,
- `.voiceagents/validation-runs/` remains gitignored.

Validation:

```bash
rg -n "realtime-validation-reports|validation report viewer|validation-runs" README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md
```

Checkpoint:

```bash
git add README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md
git commit -m "docs: document validation report viewer"
```

### Task 5.2: Full Verification

Run:

```bash
./.venv/bin/python -m pytest
git diff --check
```

Checkpoint task docs if needed:

```bash
git add docs/specs/voiceagents-pilot-demo-report-viewer-tasks.md
git commit -m "docs: finalize pilot demo report viewer tasks"
```

### Task 5.3: Merge-Before Review

Run project-level `$gstack-review` before merge.

Review focus:

- local-only report endpoints,
- path-safe summary reads,
- no blocked data rendered,
- no public sharing assumptions,
- Chinese-first copy summary is clear enough for non-engineering readers,
- UI remains simple and operational.

After review:

1. Fix findings.
2. Run focused tests.
3. Commit fixes.
4. Run final full verification.
5. Push / PR / merge.

---

## Suggested Development Order

1. Phase 1 defines report semantics.
2. Phase 2 safely reads saved runs.
3. Phase 3 exposes read-only local APIs.
4. Phase 4 builds the restrained local viewer.
5. Phase 5 documents, verifies, reviews, and ships.

Do not implement UI before the report model is tested. The value is in the decision summary and copy text, not layout polish.
