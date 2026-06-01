# VoiceAgents Pilot Validation Harness v1 Tasks

Status: IMPLEMENTED
Source spec: `docs/specs/voiceagents-pilot-validation-harness-v1.md`
Detailed TDD implementation plan: `docs/superpowers/plans/2026-06-01-pilot-validation-harness-v1.md`
Plan review: `docs/reviews/plan-eng-review-pilot-validation-harness-v1-2026-06-01.md`
Branch: `feat/pilot-validation-harness`

This document is the project-level task tracker for the Pilot Validation Harness v1 feature. The detailed red/green/refactor steps, code snippets, and expected pytest output remain in the Superpowers implementation plan. If this task tracker and the detailed plan ever disagree, update this tracker and the detailed plan in the same docs checkpoint before coding.

Rules:

- Each task should have one responsibility and should be small enough for a focused checkpoint.
- Each task should be testable by itself or with a narrow focused test.
- Each task should be committed independently after its focused verification passes.
- Use the isolated project virtual environment for all Python commands: `./.venv/bin/python`.
- Do not use system Python.
- Do not save raw audio, raw SDP, client secrets, API keys, raw tool arguments, or real PII.
- Do not commit `.voiceagents/validation-runs/` output artifacts.
- Implementation should follow `superpowers:test-driven-development`.
- Parallel work is allowed only when tasks do not touch the same files or shared contracts.

---

## Phase 1: Validation Contracts And Scenario Catalog

Goal: define the fixed validation scenarios and provider-neutral validation contracts before adding API or browser behavior.

Primary files:

- Create `voiceagents/realtime/validation.py`
- Create `tests/test_realtime_validation.py`

### Task 1.1: Add Fixed Validation Scenario Catalog

Purpose: define the five fixed Pilot Validation Harness scenarios with realistic synthetic prompts.

Inputs:

- Source spec standard scenarios table
- Existing tool names: `lookup_order`, `lookup_logistics`, `query_product_knowledge`, `handoff_to_human`
- Default synthetic order fixture: `ORD-20260601-1842`

Outputs:

- `ValidationScenario`
- `STANDARD_VALIDATION_SCENARIOS`
- Scenario IDs exactly:
  - `order_status`
  - `logistics_tracking`
  - `product_knowledge`
  - `knowledge_low_confidence_handoff`
  - `customer_requested_human`

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py::test_standard_validation_scenarios_are_fixed_and_realistic -v
```

Commit checkpoint:

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: add validation scenario catalog"
```

### Task 1.2: Add Validation Start And Finish Request Models

Purpose: encode the local validation run API contracts with strict Pydantic models.

Inputs:

- Source spec API scope
- Existing `RealtimeProviderName`
- Existing `ResponseMode`
- Scenario catalog from Task 1.1

Outputs:

- `ValidationRunStartRequest`
- `ValidationRunStartResponse`
- `ValidationManualAssertions`
- `ValidationRunObservation`
- `ValidationRunFinishRequest`
- `ValidationRunFinishResponse`
- All models reject extra fields.

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py::test_validation_models_reject_extra_fields tests/test_realtime_validation.py::test_finish_request_captures_manual_and_observed_data -v
```

Commit checkpoint:

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: add validation run contracts"
```

### Task 1.3: Add Validation Check And Summary Models

Purpose: make pass/fail output explicit and serializable before persistence exists.

Inputs:

- Source spec pass/fail rules
- Models from Task 1.2

Outputs:

- `ValidationCheck`
- `ValidationRunSummary`
- Status values `pass` and `fail`
- Check names:
  - `scenario_known`
  - `session_observed`
  - `expected_tools_observed`
  - `expected_handoff_observed`
  - `transcript_observed`
  - `assistant_response_observed`
  - `provider_errors_absent`
  - `manual_voice_confirmed`
  - `manual_business_confirmed`
  - `blocked_secret_scan_passed`

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py::test_summary_model_serializes_required_checks -v
```

Commit checkpoint:

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: add validation summary checks"
```

---

## Phase 2: Local Validation Repository And Report Rendering

Goal: save redacted validation evidence under `.voiceagents/validation-runs/` with path safety and deterministic checks.

Primary files:

- Modify `voiceagents/realtime/validation.py`
- Modify `tests/test_realtime_validation.py`

### Task 2.1: Add Run ID Generation And Path-Safe Repository

Purpose: create local validation run directories without allowing client-controlled paths.

Inputs:

- Source spec persistence section
- Default root `.voiceagents/validation-runs/`
- Run ID format begins with `vrun-YYYYMMDD-HHMMSS-` and ends with eight lowercase hex characters.

Outputs:

- `ValidationRunRepository`
- Server-generated run IDs
- `summary.json` and `report.md` target paths
- Path resolution constrained under `.voiceagents/validation-runs/`

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py::test_validation_repository_creates_safe_run_paths -v
```

Commit checkpoint:

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: add validation run repository"
```

### Task 2.2: Add Redacted Summary Writing

Purpose: write `summary.json` with redacted transcript, assistant response, provider events, manual notes, and handoff reason.

Inputs:

- Existing redaction helpers
- `ValidationRunFinishRequest`
- Safety requirements from source spec

Outputs:

- Redacted `summary.json`
- No API keys, client secrets, SDP, raw audio fields, raw tool arguments, or real PII in saved summary
- Blocked-secret scan result included in checks

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py::test_validation_summary_is_redacted_before_write -v
```

Commit checkpoint:

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: write redacted validation summary"
```

### Task 2.3: Add Markdown Report Rendering

Purpose: render a concise `report.md` for developer, pilot merchant, and support-review readers.

Inputs:

- Redacted `ValidationRunSummary`
- Source spec users and acceptance criteria

Outputs:

- `report.md`
- Scenario metadata
- Overall status
- Check table
- Manual assertions
- Redacted transcript and assistant response snippets
- Report path returned by repository finish flow

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py::test_validation_report_contains_redacted_status_and_checks -v
```

Commit checkpoint:

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: render validation report"
```

### Task 2.4: Add Automatic Pass/Fail Evaluation

Purpose: compute deterministic pass/fail checks from observed tools, handoff, transcript, assistant response, provider events, manual assertions, and secret scan.

Inputs:

- Scenario catalog from Task 1.1
- Finish request observation from Task 1.2
- Pass/fail rules from source spec

Outputs:

- `evaluate_validation_checks`
- Overall status `pass` only when every required check passes
- Provider error detection for markers including `provider_error=`, `event_log_error=`, `data_channel_error`, and `OpenAI SDP exchange failed`

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py::test_validation_checks_fail_when_expected_tool_missing tests/test_realtime_validation.py::test_validation_checks_fail_when_provider_errors_are_observed -v
```

Commit checkpoint:

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: evaluate validation checks"
```

---

## Phase 3: Local Validation API Endpoints

Goal: expose local development endpoints that let `/realtime-test` fetch scenarios, start a run, and finish a run.

Primary files:

- Modify `voiceagents/api/app.py`
- Create `tests/test_api_realtime_validation.py`

### Task 3.1: Add Validation Scenarios Endpoint

Purpose: expose the fixed scenario catalog to the browser page.

Inputs:

- `STANDARD_VALIDATION_SCENARIOS`
- FastAPI app factory in `voiceagents/api/app.py`

Outputs:

- `GET /v1/realtime/validation-scenarios`
- Response contains exactly the five fixed scenarios
- Response uses safe synthetic data only

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_validation.py::test_get_validation_scenarios_returns_fixed_catalog -v
```

Commit checkpoint:

```bash
git add voiceagents/api/app.py tests/test_api_realtime_validation.py
git commit -m "feat: expose validation scenarios endpoint"
```

### Task 3.2: Add Validation Run Start Endpoint

Purpose: create a validation run and return server-generated paths.

Inputs:

- `ValidationRunStartRequest`
- `ValidationRunRepository`
- Scenario catalog

Outputs:

- `POST /v1/realtime/validation-runs`
- Generated `run_id`
- `summary_path`
- `report_path`
- Unknown scenario rejected with 422 or 400

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_validation.py::test_start_validation_run_returns_server_generated_run_id tests/test_api_realtime_validation.py::test_start_validation_run_rejects_unknown_scenario -v
```

Commit checkpoint:

```bash
git add voiceagents/api/app.py tests/test_api_realtime_validation.py
git commit -m "feat: start validation runs"
```

### Task 3.3: Add Validation Run Finish Endpoint

Purpose: finish a run, write the redacted files, and return check results.

Inputs:

- Existing run ID from Task 3.2
- `ValidationRunFinishRequest`
- Repository finish flow from Phase 2

Outputs:

- `POST /v1/realtime/validation-runs/{run_id}/finish`
- Written `summary.json`
- Written `report.md`
- Check results and overall status
- Invalid path-like run IDs rejected

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_validation.py::test_finish_validation_run_writes_summary_and_report tests/test_api_realtime_validation.py::test_finish_validation_run_rejects_path_like_run_id -v
```

Commit checkpoint:

```bash
git add voiceagents/api/app.py tests/test_api_realtime_validation.py
git commit -m "feat: finish validation runs"
```

---

## Phase 4: `/realtime-test` Validation UI And Browser Flow

Goal: let a developer wrap a real voice test session in a validation run without replacing the existing Start, Stop, Mute, Text, and Voice controls.

Primary files:

- Modify `voiceagents/api/static/realtime-test.html`
- Modify `tests/test_api_realtime_test_page.py`
- Create `tests/test_realtime_test_page_validation_flow.py`

### Task 4.1: Add Validation Controls To Static Page

Purpose: render the validation UI required by the spec.

Inputs:

- Source spec UX scope
- Existing `/realtime-test` static HTML

Outputs:

- Scenario selector
- `Start Validation Run` button
- `Finish Run` button
- Manual assertion controls:
  - heard voice
  - voice quality acceptable
  - business answer acceptable
  - demo ready
  - notes
- Visible current `run_id`
- Visible saved report confirmation area

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py::test_realtime_test_page_renders_validation_controls -v
```

Commit checkpoint:

```bash
git add voiceagents/api/static/realtime-test.html tests/test_api_realtime_test_page.py
git commit -m "feat: render validation controls"
```

### Task 4.2: Load Scenario Catalog In Browser JavaScript

Purpose: populate validation controls from the backend endpoint instead of hardcoding stale browser data.

Inputs:

- `GET /v1/realtime/validation-scenarios`
- Existing page initialization JavaScript

Outputs:

- Scenario selector populated from API response
- Suggested prompt displayed or stored for the selected scenario
- Provider Events panel records validation scenario load success or failure using safe messages

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_test_page_validation_flow.py::test_page_loads_validation_scenarios -v
```

Commit checkpoint:

```bash
git add voiceagents/api/static/realtime-test.html tests/test_realtime_test_page_validation_flow.py
git commit -m "feat: load validation scenarios on test page"
```

### Task 4.3: Add Start Validation Run Browser Flow

Purpose: start a validation run from current page/session metadata.

Inputs:

- Selected scenario ID
- Current session ID
- Current call ID
- Current provider
- Current response mode
- Locale

Outputs:

- Browser calls `POST /v1/realtime/validation-runs`
- Current `run_id` is visible
- Summary/report paths are stored for finish confirmation
- Existing realtime Start button behavior remains unchanged

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_test_page_validation_flow.py::test_page_starts_validation_run -v
```

Commit checkpoint:

```bash
git add voiceagents/api/static/realtime-test.html tests/test_realtime_test_page_validation_flow.py
git commit -m "feat: start validation run from test page"
```

### Task 4.4: Add Finish Validation Run Browser Flow

Purpose: collect safe panel observations and manual assertions, then save the validation artifact.

Inputs:

- Current `run_id`
- Session State panel text
- Transcript panel text
- Assistant Response panel text
- Tool Calls panel text
- Handoff panel text
- Provider Events panel text
- Latency values
- Manual assertions

Outputs:

- Browser calls `POST /v1/realtime/validation-runs/{run_id}/finish`
- Saved confirmation displays status and report path
- Browser does not send raw audio, raw SDP, API keys, client secrets, or raw tool argument payloads

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_test_page_validation_flow.py::test_page_finishes_validation_run_with_safe_observation -v
```

Commit checkpoint:

```bash
git add voiceagents/api/static/realtime-test.html tests/test_realtime_test_page_validation_flow.py
git commit -m "feat: finish validation run from test page"
```

### Task 4.5: Preserve Existing Realtime Controls

Purpose: ensure validation UI does not regress Start, Stop, Mute, Text, or Voice behavior.

Inputs:

- Existing realtime test page tests
- Existing failure-mode page tests
- Validation UI changes from Tasks 4.1 through 4.4

Outputs:

- Existing controls still present
- Existing response mode and mute event logging still tested
- Validation flow does not require a real OpenAI key for automated tests

Validation:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py tests/test_realtime_test_page_validation_flow.py -v
```

Commit checkpoint:

```bash
git add voiceagents/api/static/realtime-test.html tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py tests/test_realtime_test_page_validation_flow.py
git commit -m "test: cover validation page flow"
```

---

## Phase 5: Documentation, Verification, And Pre-Merge Review

Goal: document the local validation harness, verify the whole branch, and run the standard review flow before merge.

Primary files:

- Modify `README.md`
- Modify `OPENAI_REALTIME_VOICE_MVP_HANDOFF.md`
- Modify this task file only if implementation details intentionally change

### Task 5.1: Document Local Validation Usage

Purpose: explain how a developer runs and finds saved validation reports.

Inputs:

- Implemented API and UI behavior
- Source spec persistence section

Outputs:

- README section for local validation reports
- Commands use `./.venv/bin/python`
- Documentation states `.voiceagents/validation-runs/` is local and not committed

Validation:

```bash
rg -n "validation-runs|Start Validation Run|Finish Run|\\.venv/bin/python" README.md
```

Commit checkpoint:

```bash
git add README.md
git commit -m "docs: document validation harness usage"
```

### Task 5.2: Update Handoff And Task Status

Purpose: keep project status aligned for future sessions.

Inputs:

- Implemented feature behavior
- Verification results from Phases 1 through 4

Outputs:

- `OPENAI_REALTIME_VOICE_MVP_HANDOFF.md` updated with current status
- This tasks document status is `IMPLEMENTED` after implementation and verification pass

Validation:

```bash
rg -n "Pilot Validation Harness|validation-runs|IMPLEMENTED" OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-pilot-validation-harness-v1-tasks.md
```

Commit checkpoint:

```bash
git add OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-pilot-validation-harness-v1-tasks.md
git commit -m "docs: update validation harness handoff"
```

### Task 5.3: Run Focused Validation Harness Tests

Purpose: verify the new harness behavior before the full suite.

Inputs:

- Completed implementation from Phases 1 through 4

Outputs:

- Focused validation tests pass
- No generated validation artifacts committed

Validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py tests/test_api_realtime_validation.py tests/test_api_realtime_test_page.py tests/test_realtime_test_page_validation_flow.py -v
git status --short
```

Commit checkpoint:

```bash
git add tests/test_realtime_validation.py tests/test_api_realtime_validation.py tests/test_api_realtime_test_page.py tests/test_realtime_test_page_validation_flow.py
git commit -m "test: verify validation harness"
```

### Task 5.4: Run Full Suite And Static Checks

Purpose: confirm the branch remains healthy before review.

Inputs:

- Completed implementation and docs

Outputs:

- Full pytest suite passes
- Markdown and Python whitespace checks pass
- Working tree contains only intentional changes before review

Validation:

```bash
./.venv/bin/python -m pytest
git diff --check
git status --short
```

Also run the Superpowers no-placeholder checklist against this task tracker and the detailed implementation plan before review.

Commit checkpoint:

```bash
git add docs/specs/voiceagents-pilot-validation-harness-v1-tasks.md docs/superpowers/plans/2026-06-01-pilot-validation-harness-v1.md
git commit -m "docs: finalize validation harness task plan"
```

### Task 5.5: Run Pre-Merge Review

Purpose: complete the gstack review gate while still on the feature branch.

Inputs:

- Clean feature branch
- Passing verification from Task 5.4

Outputs:

- `$gstack-review` findings recorded
- Any accepted findings fixed in follow-up commits
- Branch ready for push and PR

Validation:

```bash
git status --short --branch
```

Review command:

```bash
env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" gstack-review
```

Commit checkpoint:

Create one follow-up commit per accepted review finding, staging only the files changed for that finding.

---

## Parallelization Guidance

Recommended default: execute serially because validation contracts flow into repository, API, and browser behavior.

Safe limited parallel work:

- After Phase 1 is complete, Task 2.1 and Task 3.1 can be prepared in parallel if the scenario catalog contract is frozen.
- After Task 3.1 is complete, Task 4.1 static UI markup can proceed while Task 2.2 redaction writing is implemented.
- Documentation Task 5.1 can start after the API and UI shapes are stable, but it should not be committed as final until focused tests pass.

Avoid parallel work:

- Do not edit `voiceagents/realtime/validation.py` from multiple agents at the same time.
- Do not edit `voiceagents/api/static/realtime-test.html` from multiple agents at the same time.
- Do not run `$gstack-review` until implementation, docs, and verification checkpoints are complete.

## Development Order

1. Phase 1 establishes contracts.
2. Phase 2 persists safe validation evidence.
3. Phase 3 exposes local API endpoints.
4. Phase 4 connects `/realtime-test`.
5. Phase 5 documents, verifies, and reviews the branch.

Implementation completed on `feat/pilot-validation-harness`. Future changes should start from a fresh task update and keep this tracker, the source spec, and the detailed Superpowers plan aligned before coding.
