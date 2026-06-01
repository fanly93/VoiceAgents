# VoiceAgents Pilot Validation Harness v1 Spec

Status: IMPLEMENTED
Date: 2026-06-01
Branch: `feat/product-cut-discovery`
Source design: `docs/designs/voiceagents-pilot-validation-harness-v1.md`

## Goal

Build a local validation harness for the existing `/realtime-test` page so a developer can run five standard realtime voice scenarios and save a redacted validation report for each run.

The harness turns manual panel inspection into a repeatable validation artifact:

```text
.voiceagents/validation-runs/<run_id>/summary.json
.voiceagents/validation-runs/<run_id>/report.md
```

## Why Now

The project has already shipped:

- browser/local realtime plumbing,
- OpenAI Realtime WebRTC voice MVP,
- tool relay,
- event/transcript redaction,
- real-mode manual validation,
- browser failure-mode automated simulation.

The current gap is evidence management. Realtime test results are visible in browser panels and low-level JSONL logs, but a full validation run is not saved as a single summary/report.

## Users

Primary user:

- Developer/operator running real voice validation.

Secondary report readers:

- Pilot merchant stakeholder reviewing demo evidence.
- Human support reviewer checking handoff context shape.

## Standard Scenarios

The first version has exactly these fixed scenarios:

| Scenario ID | Label | Expected tool behavior | Expected handoff |
|---|---|---|---|
| `order_status` | Order status lookup | `lookup_order` | no |
| `logistics_tracking` | Logistics tracking lookup | `lookup_logistics` | no |
| `product_knowledge` | Product knowledge consultation | `query_product_knowledge` | no |
| `knowledge_low_confidence_handoff` | Knowledge miss handoff | `query_product_knowledge`, `handoff_to_human` | yes |
| `customer_requested_human` | User requested human | `handoff_to_human` | yes |

Scenario prompts must use realistic synthetic data and must not include real PII. The default order fixture is `ORD-20260601-1842`.

## UX Scope

Add a validation section to `/realtime-test` with:

- scenario selector,
- `Start Validation Run`,
- `Finish Run`,
- manual assertion controls:
  - heard voice,
  - voice quality acceptable,
  - business answer acceptable,
  - demo ready,
  - notes.
- visible current `run_id`,
- visible generated report paths or a concise saved confirmation.

The existing Start/Stop/Mute/Text/Voice controls remain responsible for the realtime session. Validation controls wrap the current testing workflow; they do not replace the realtime controls.

## API Scope

Add local development endpoints:

### `GET /v1/realtime/validation-scenarios`

Returns the five fixed scenario definitions.

Response fields per scenario:

- `scenario_id`
- `label`
- `description`
- `suggested_prompt`
- `expected_tools`
- `expected_handoff`
- `manual_checks`

### `POST /v1/realtime/validation-runs`

Starts a validation run.

Request fields:

- `scenario_id`
- `session_id`
- `call_id`
- `merchant_id`
- `provider`
- `response_mode`
- `locale`

Response fields:

- `run_id`
- `scenario`
- `started_at`
- `summary_path`
- `report_path`

The backend generates `run_id`. The client never chooses filesystem paths.

### `POST /v1/realtime/validation-runs/{run_id}/finish`

Finishes a validation run and writes `summary.json` and `report.md`.

Request fields:

- `session_state`
- `transcript_text`
- `assistant_response_text`
- `tool_names`
- `handoff_reason`
- `provider_events`
- `latency_ms_values`
- `manual_assertions`

The backend redacts text before saving. The backend computes pass/fail fields and blocked-secret scan results.

Response fields:

- `run_id`
- `status`
- `summary_path`
- `report_path`
- `checks`

## Data Model

Use provider-neutral Pydantic models in a new validation module.

Core types:

- `ValidationScenario`
- `ValidationRunStartRequest`
- `ValidationRunStartResponse`
- `ValidationManualAssertions`
- `ValidationRunObservation`
- `ValidationRunFinishRequest`
- `ValidationCheck`
- `ValidationRunSummary`
- `ValidationRunFinishResponse`

The models must reject extra fields.

## Pass/Fail Rules

The backend computes checks:

- `scenario_known`: scenario ID is one of the five fixed scenarios.
- `session_observed`: session state reached `connected`, `ended`, or another valid terminal state from the page.
- `expected_tools_observed`: all expected tools for the scenario appear in `tool_names`.
- `expected_handoff_observed`: expected handoff matches observed `handoff_reason` presence.
- `transcript_observed`: transcript text is non-empty after redaction unless a scenario is explicitly marked no-transcript.
- `assistant_response_observed`: assistant response text is non-empty after redaction unless the scenario is expected to hand off immediately.
- `provider_errors_absent`: provider events do not include known error markers such as `provider_error=`, `event_log_error=`, `data_channel_error`, or `OpenAI SDP exchange failed`.
- `manual_voice_confirmed`: manual assertions confirm heard voice and acceptable voice quality.
- `manual_business_confirmed`: manual assertions confirm business answer quality for non-handoff scenarios, or demo readiness for handoff scenarios.
- `blocked_secret_scan_passed`: saved report and summary do not include blocked tokens or field names.

Overall status:

- `pass` when all required checks pass.
- `fail` when any required automatic or manual check fails.

## Persistence

Default root:

```text
.voiceagents/validation-runs/
```

Per-run files:

```text
.voiceagents/validation-runs/<run_id>/summary.json
.voiceagents/validation-runs/<run_id>/report.md
```

`run_id` format:

```text
vrun-YYYYMMDD-HHMMSS-<8 lowercase hex chars>
```

The repository must ensure resolved paths stay under `.voiceagents/validation-runs/`.

## Safety Requirements

Saved summaries and reports must not include:

- OpenAI API key,
- client secret,
- `tool_call_token`,
- Authorization header,
- SDP,
- raw audio,
- audio bytes,
- raw tool arguments,
- real customer PII,
- unredacted transcript.

Use existing redaction helpers before writing any transcript, assistant response, notes, handoff summary, or provider event text.

## Non-Goals

- No CLI entrypoint in v1.
- No merchant-facing UI.
- No customer-service back office UI.
- No production authentication or multi-tenant permissions.
- No telephony provider.
- No phone numbers.
- No raw audio storage.
- No real merchant APIs.

## Acceptance Criteria

1. `/realtime-test` renders validation controls for the five fixed scenarios.
2. `GET /v1/realtime/validation-scenarios` returns exactly the five scenario definitions.
3. `POST /v1/realtime/validation-runs` creates a server-generated `run_id` and returns local summary/report paths.
4. `POST /v1/realtime/validation-runs/{run_id}/finish` writes `summary.json` and `report.md`.
5. Saved files contain redacted text only and no blocked secrets or raw audio fields.
6. The backend computes pass/fail checks for expected tools, handoff, transcript, assistant response, provider errors, manual assertions, and blocked-secret scan.
7. Unknown scenario IDs are rejected with 422 or 400.
8. Invalid `run_id` paths are rejected and cannot write outside `.voiceagents/validation-runs/`.
9. Automated tests cover contracts, repository writing, API happy/negative paths, static page controls, and browser JavaScript run lifecycle.
10. Full test suite passes in an isolated `.venv` or conda environment.

## Implementation Notes

Follow existing patterns:

- contracts use Pydantic models with `extra="forbid"`;
- local-only persistence mirrors `JsonlVoiceEventRepository`;
- tests use `tmp_path` for filesystem writes;
- `/realtime-test` static tests assert control and safety behavior;
- browser JS behavior can use the existing Node/vm harness style from `tests/test_realtime_test_page_failure_modes.py`.
