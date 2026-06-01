# Plan Eng Review: Pilot Validation Harness v1

Date: 2026-06-01
Branch: `feat/product-cut-discovery`
Reviewed docs:

- `docs/designs/voiceagents-pilot-validation-harness-v1.md`
- `docs/specs/voiceagents-pilot-validation-harness-v1.md`
- `docs/superpowers/plans/2026-06-01-pilot-validation-harness-v1.md`

## Scope Challenge

Verdict: CLEAR.

The plan is scoped to a local validation harness on the existing `/realtime-test` surface. It does not introduce telephony, production auth, merchant admin, customer-service workflow, or raw audio storage.

The implementation touches multiple layers, but each layer has a narrow reason:

- contracts/repository for local validation artifacts,
- API endpoints for start/finish,
- static page controls for the operator workflow,
- tests for model/API/page/browser-JS behavior,
- docs for usage and handoff.

This is the smallest coherent unit that can produce a real validation report.

## Architecture Review

Verdict: CLEAR WITH GUIDANCE.

The strongest architectural decision is that the backend owns run ID generation, path safety, redaction, pass/fail rule evaluation, and file writing. The browser only submits safe observations and manual assertions.

Recommended implementation guardrails:

1. Keep validation models in `voiceagents/realtime/validation.py` rather than mixing them into `contracts.py`. This prevents the realtime provider contract file from becoming a catch-all.
2. Keep `.voiceagents/validation-runs/` local-only and gitignored, matching existing event/transcript log posture.
3. Do not let the browser submit filesystem paths. It should only receive server-generated `summary_path` and `report_path`.
4. Keep scenario definitions fixed in v1. Dynamic scenario authoring would turn this into a configuration product before the validation loop is proven.

## Data Flow

```text
/realtime-test
  -> GET /v1/realtime/validation-scenarios
  -> POST /v1/realtime/validation-runs
  -> normal realtime Start / tool relay / event relay
  -> operator fills manual assertions
  -> POST /v1/realtime/validation-runs/{run_id}/finish
  -> LocalValidationRunRepository
  -> .voiceagents/validation-runs/<run_id>/summary.json
  -> .voiceagents/validation-runs/<run_id>/report.md
```

The data flow is acceptable because no production credential, raw audio, SDP, or tool token needs to enter the validation report request.

## Code Quality Review

Verdict: CLEAR.

The plan uses existing project patterns:

- Pydantic contracts with `extra="forbid"`,
- `tmp_path` filesystem tests,
- static HTML assertions for page surface,
- Node/vm harness for browser JavaScript behavior,
- small checkpoint commits per task.

No premature abstraction is required beyond one repository class and one validation module.

## Test Review

Verdict: CLEAR.

Test coverage shape:

```text
tests/test_realtime_validation.py
  -> scenario catalog
  -> model validation
  -> report redaction
  -> path safety

tests/test_api_realtime_validation.py
  -> scenario endpoint
  -> start endpoint
  -> finish endpoint
  -> unknown scenario / invalid run id

tests/test_api_realtime_test_page.py
  -> validation controls exist
  -> no secret rendering

tests/test_realtime_test_page_validation_flow.py
  -> page loads scenarios
  -> starts a run
  -> finishes a run
  -> renders report path

full pytest
  -> regression coverage
```

The plan should add one negative API test during implementation even though the task text only names it generally:

- unknown `scenario_id` returns 400 or 422,
- invalid `run_id` returns 400 and writes no file.

This is not blocking because Task 3 and acceptance criteria already require those cases.

## Performance Review

Verdict: CLEAR.

Validation reports are local filesystem writes with small JSON/Markdown payloads. The report is written only at `Finish Run`, not during every realtime event, so it should not affect realtime latency.

Avoid scanning large historical JSONL logs on every finish. The v1 blocked-secret scan should inspect the generated `summary.json` and `report.md`; scanning `.voiceagents/events/realtime-events.jsonl` can remain a separate manual/log-safety check unless a later spec adds bounded per-session log indexing.

## Risks

- Browser observations can be incomplete if the operator finishes too early. Mitigation: visible manual assertions and failed automatic checks.
- Manual assertions can be inaccurate. Mitigation: report distinguishes automatic checks from manual confirmations.
- Saved report could accidentally include unsafe text. Mitigation: backend redaction plus blocked-token scan before final response.

## Recommendation

Proceed to user review of the spec and plan. After approval, implement with TDD and checkpoint after each task.

Do not start implementation until the user confirms the spec/plan direction.

