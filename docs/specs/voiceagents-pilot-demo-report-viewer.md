# VoiceAgents Pilot Demo Report Viewer Spec

Status: REVIEWED / READY FOR IMPLEMENTATION
Date: 2026-06-02
Branch: `feat/pilot-demo-report-viewer`
Source design: `docs/designs/voiceagents-pilot-demo-report-viewer.md`

## Goal

Build a local Pilot Demo Report Viewer that turns existing realtime validation run summaries into a simple, readable, copyable report for boss / decision-maker review.

The viewer should reduce post-demo reporting from about 30 minutes of screenshots and manual writing to 1-3 minutes of local review plus copy.

## Users

Primary reader:

- Boss / decision-maker deciding whether a voice demo is ready to continue toward pilot validation.

Secondary readers:

- Customer-service lead checking handoff and customer experience.
- Technical teammate checking tools, provider events, and safety boundaries.

Primary operator:

- Developer/operator who runs realtime validation and needs to forward the result.

## Non-Goals

- No flashy or brand-polished frontend.
- No public share links.
- No login, auth, merchant account, or multi-tenant permission model.
- No merchant-facing SaaS dashboard.
- No customer-service back office workflow.
- No PDF export in v1.
- No multi-run report packet in v1.
- No new realtime validation capture workflow.
- No raw audio, SDP, API key, client secret, tool token, Authorization header, raw tool arguments, real PII, or unredacted transcript rendering.

## Data Source

Use existing validation run summaries:

```text
.voiceagents/validation-runs/<run_id>/summary.json
```

The viewer must treat these files as local-only artifacts. It should not require `.voiceagents/validation-runs/` to be committed.

Expected current summary fields include:

- `run_id`
- `scenario_id`
- `status`
- `started_at`
- `finished_at`
- `checks`
- `manual_assertions`
- `transcript_text`
- `assistant_response_text`
- `tool_names`
- `handoff_reason`
- `provider_events`
- `latency_ms_values`

## Readiness Model

Add a report-view readiness layer derived from validation summary fields.

Readiness values:

- `ready_for_pilot`
- `needs_another_validation`
- `blocked`

Suggested derivation:

- `ready_for_pilot`: validation `status` is `pass`.
- `blocked`: any safety check fails, especially `blocked_secret_scan_passed`, or provider errors are observed.
- `needs_another_validation`: validation is not pass, but failure is non-secret and non-provider-critical, such as missing manual assertion or missing expected tool.

The readiness model should be explicit and tested. Do not hide failing checks.

## Report View Model

Add provider-neutral report view models, likely in `voiceagents/realtime/validation.py` or a new nearby module if the file becomes too large.

Suggested models:

- `ValidationRunListItem`
- `ValidationRunReport`
- `ValidationRunDecisionSummary`
- `ValidationRunAudienceSection`
- `ValidationRunCopySummary`

The report view should expose:

- run metadata,
- scenario label,
- readiness value and human label,
- one-sentence decision summary,
- scenario coverage summary,
- business proof bullets,
- boss / decision-maker section,
- customer-service section,
- technical section,
- copyable WeChat/Feishu summary text,
- visible warning list for failed checks.

All models must reject extra fields where they accept external data.

## API Scope

Add local development endpoints:

### `GET /v1/realtime/validation-report-runs`

Lists locally saved validation runs.

Response fields per item:

- `run_id`
- `scenario_id`
- `scenario_label`
- `status`
- `readiness`
- `started_at`
- `finished_at`

Sort order:

- newest first by `finished_at` when available;
- fallback to run directory name if timestamps are missing.

### `GET /v1/realtime/validation-report-runs/{run_id}`

Returns a report-view model for one saved run.

Response fields:

- `run_id`
- `scenario`
- `status`
- `readiness`
- `decision_summary`
- `scenario_coverage`
- `business_proof`
- `audience_sections`
- `copy_summary`
- `checks`
- `warnings`

Invalid or path-like `run_id` values must not escape `.voiceagents/validation-runs/`.

The API must not expose absolute local filesystem paths. If a path label is needed for local debugging, it must be repository-relative, for example `.voiceagents/validation-runs/<run_id>/summary.json`.

## UI Scope

Add a local static page:

```text
/realtime-validation-reports
```

The page should be restrained and operational, not a marketing page.

Required UI:

- recent run list,
- selected run detail,
- newest run auto-selected when runs exist,
- top readiness banner,
- three conclusion cards or sections:
  - Overall readiness,
  - Scenario coverage,
  - Business proof,
- copyable WeChat/Feishu summary,
- audience sections:
  - Boss / decision-maker,
  - Customer-service lead,
  - Technical teammate,
- failed-check warning area,
- empty state when no validation runs exist,
- error state when a run cannot be loaded.

The first screen should answer:

```text
Should we continue this pilot demo?
What passed?
What blocks the next step?
What can I copy and send?
```

## Copy Summary Requirements

The copy summary is part of the product, not decoration. It is Chinese-first because the current forwarding workflow is WeChat/Feishu.

It must be short enough for WeChat/Feishu and include:

- demo scenario,
- readiness result,
- key pass/fail evidence,
- handoff result when relevant,
- one next action.

Example shape:

```text
VoiceAgents 语音 Demo 验证：可以继续推进试点。
场景：订单状态查询。
证据：已确认有语音输出，业务回答可接受，命中 lookup_order 工具，无 provider 错误，脱敏安全扫描通过。
下一步：可以发给试点决策人收集反馈。
```

English helper labels may be added if implementation scope allows, but v1 must lock one clear Chinese template in tests.

## Safety Requirements

The viewer must not render:

- raw audio,
- audio bytes,
- SDP,
- OpenAI API key,
- client secret,
- tool call token,
- Authorization header,
- raw tool arguments,
- real customer PII,
- unredacted transcript.

The backend should construct the report view from already redacted summaries and still scan serialized output for blocked fields/tokens before returning.

If blocked content is detected, the report endpoint should return an error or a `blocked` readiness with a visible warning. It must not render the blocked value.

## Acceptance Criteria

1. `/realtime-validation-reports` serves a local report viewer page.
2. `GET /v1/realtime/validation-report-runs` lists saved validation summaries newest first.
3. `GET /v1/realtime/validation-report-runs/{run_id}` returns a report-view model for a run.
4. Unknown or path-like run IDs are rejected and cannot read outside `.voiceagents/validation-runs/`.
5. The report model derives `ready_for_pilot`, `needs_another_validation`, and `blocked` correctly.
6. The page renders top-level readiness, scenario coverage, business proof, audience sections, and copy summary.
7. Empty and error states are visible and understandable.
8. The copy summary can be selected/copied and contains scenario, readiness, evidence, and next action.
9. The viewer does not expose raw audio, SDP, API keys, client secrets, tool tokens, Authorization headers, raw tool arguments, real PII, or unredacted transcripts.
10. Automated tests cover report model derivation, API list/detail/path safety, static page controls, and browser JavaScript loading/copy behavior.
11. Full test suite passes in the isolated project `.venv`.

## Implementation Notes

- Reuse the existing validation repository root `.voiceagents/validation-runs/`.
- Prefer small read-only repository methods for listing and loading summaries.
- Keep implementation local-only and consistent with the existing `/realtime-test` static page pattern.
- Avoid adding a frontend framework.
- Do not make the report viewer depend on OpenAI credentials or a running realtime session.
