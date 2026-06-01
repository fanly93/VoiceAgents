# Autoplan Review: Pilot Demo Report Viewer

Date: 2026-06-02
Branch: `feat/pilot-demo-report-viewer`
Status: CLEAN AFTER DOC FIXES

Reviewed docs:

- `docs/designs/voiceagents-pilot-demo-report-viewer.md`
- `docs/specs/voiceagents-pilot-demo-report-viewer.md`
- `docs/specs/voiceagents-pilot-demo-report-viewer-tasks.md`

## Scope Check

Verdict: CLEAN.

The plan is scoped to a local, restrained report viewer for existing validation summaries. It does not introduce public sharing, merchant accounts, auth, customer-service back office, PDF export, telephony, new realtime validation capture, or polished marketing UI.

The primary reader remains the boss / decision-maker. Secondary customer-service and technical sections are supporting evidence, not the top-level product.

## Consistency Fixes Applied

### 1. Single-run v1 scope

Issue: the design said the viewer could turn "one or more validation runs" into a report, while the spec and tasks described a single selected run.

Fix: v1 now explicitly shows a recent-run list and one selected run at a time. Multi-run packets are deferred.

### 2. Default run behavior

Issue: the design left open whether the viewer should default to the latest run or show the run list first.

Fix: the viewer should show the run list and auto-select the newest run when one exists.

### 3. Copy language

Issue: the spec allowed English-only copy even though the actual forwarding workflow is WeChat/Feishu and the user explicitly described Chinese operational use.

Fix: the copy summary is now Chinese-first. English helper labels are optional only if they do not add implementation complexity.

### 4. Readiness authority

Issue: the design left open whether manual `demo_ready` could override failed checks.

Fix: readiness is derived from validation checks and safety state. Manual `demo_ready` participates through existing validation checks but cannot override failed safety, provider-error, or expected-tool checks.

### 5. Local path exposure

Issue: the list endpoint included `summary_path`, which could encourage rendering local filesystem paths that are not useful to the boss / decision-maker and could leak machine details if an implementation used absolute roots.

Fix: the list endpoint no longer requires `summary_path`. If a path label is needed for local debugging, it must be repository-relative.

### 6. Test file naming

Issue: the static page task referenced `tests/test_api_realtime_test_page.py`, which belongs to `/realtime-test`, not the new report viewer.

Fix: the task tracker now calls for `tests/test_api_realtime_validation_report_page.py` plus `tests/test_realtime_validation_report_page.py`.

## CEO Review

The plan addresses the real demand evidence: cutting a 30-minute screenshot and manual summary workflow down to a 1-3 minute local review and copy workflow.

No scope expansion is recommended before implementation. A bigger dashboard or public report flow would be premature.

## Design Review

The information hierarchy is now clear:

1. Overall readiness.
2. Scenario coverage.
3. Business proof.
4. Copyable Chinese summary.
5. Role-specific evidence sections.
6. Technical warnings and failed checks.

The design should stay operational and restrained. No design-system or visual polish task is required for v1.

## Engineering Review

The implementation plan should start with report semantics before API or UI:

1. Readiness derivation.
2. Report view models.
3. Safe local summary listing/loading.
4. Read-only local endpoints.
5. Static viewer page.

Key engineering constraints:

- Do not read outside `.voiceagents/validation-runs/`.
- Do not expose absolute local filesystem paths.
- Scan report responses for blocked fields/tokens before rendering.
- Keep the viewer independent of OpenAI credentials and active realtime sessions.

## DX Review

The operator workflow is explicit enough:

1. Run validation from `/realtime-test`.
2. Open `/realtime-validation-reports`.
3. Newest run is auto-selected.
4. Review readiness and warnings.
5. Copy the Chinese WeChat/Feishu summary.

Documentation must explain the local-only boundary and the target report-prep time reduction.

## Remaining Risks

- The copy summary is now specified as Chinese-first, but the exact final template should still be treated as product-critical during implementation.
- Empty, malformed, and blocked-content states must be tested because this viewer reads local artifacts that may be stale or hand-edited.

## Recommendation

Proceed to implementation Phase 1 only after this docs checkpoint is committed.

Start with `Task 1.1: Add Readiness Derivation` from `docs/specs/voiceagents-pilot-demo-report-viewer-tasks.md`.
