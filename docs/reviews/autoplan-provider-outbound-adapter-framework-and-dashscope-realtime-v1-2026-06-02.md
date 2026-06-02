# Autoplan Review: Provider Outbound Adapter Framework And DashScope Realtime V1

Date: 2026-06-02
Branch: `feat/dashscope-realtime-outbound`
Reviewed docs:

- `docs/specs/voiceagents-provider-outbound-adapter-framework-and-dashscope-realtime-v1.md`
- `docs/specs/voiceagents-provider-outbound-adapter-framework-and-dashscope-realtime-v1-tasks.md`
- `docs/superpowers/plans/2026-06-02-provider-outbound-adapter-framework-and-dashscope-realtime-v1.md`

## Autoplan Scope

This review followed the project-level `$gstack-autoplan` workflow locally:

1. CEO review: scope, product value, sequencing, and future-provider boundary.
2. Design review: `/realtime-test` user-facing changes and local developer UI state coverage.
3. Engineering review: architecture, security, tests, failure modes, and dependency risk.
4. DX review: developer execution path, manual verification, and review readiness.

No code implementation was started.

## Context Examined

- Existing provider-neutral code under `voiceagents/realtime/`.
- Existing DashScope config/adapter/proxy tests.
- Current `/realtime-test` static page and OpenAI adapter.
- `pyproject.toml` dependency surface.
- README and handoff documentation around realtime provider safety.

## Findings And Decisions

### P1: No Blocking Findings After Prior Consistency Fix

The plan now preserves the key architecture decision: DashScope is the first implementation of a provider outbound adapter framework, not a hardcoded one-off path. It explicitly keeps Volc and GLM out of scope while preserving their extension path.

Decision: no P1 fix required.

### P2: Spec Test Matrix Omitted New Transport/Page Tests

The spec acceptance criteria required DashScope outbound transport and browser smoke behavior, but the spec's focused and broader test command examples did not include `tests/test_realtime_dashscope_transport.py` and did not fully mirror the final focused suite in the tasks/plan.

Fix applied:

- Added `tests/test_realtime_dashscope_transport.py`, `tests/test_api_realtime_test_page.py`, and `tests/test_realtime_test_page_failure_modes.py` to the spec focused suite.
- Added `tests/test_realtime_dashscope_transport.py` to the broader realtime suite.

### P2: Dependency Decision Could Modify `pyproject.toml`

The plan correctly added `Task 4.0` for outbound WebSocket dependency choice, but the spec's "Files Expected To Change" section did not mention `pyproject.toml` if a package is added.

Fix applied:

- Added `pyproject.toml`, conditional on the dependency decision adding a package.

### P2: Proxy Coordinator Implementation Task Was Too Broad

The original implementation task combined event relay, persistence, tool routing, tool-result relay, and disconnect cleanup. That violated the preferred small-task rhythm and made a single checkpoint too large.

Fix applied:

- Split the old Task 3.4 into:
  - Task 3.4: event relay and server-side persistence;
  - Task 3.5: provider tool-call routing and result relay;
  - Task 3.6: provider disconnect cleanup.
- Mirrored the same task split in the Superpowers implementation plan.

### P3: Design Scope Is Intentionally Minimal

`/realtime-test` has UI scope, but this branch is a local developer smoke surface rather than a production UX redesign. The plan keeps the UI utilitarian and focuses on safe status, transcript, tool, latency, and provider event visibility.

Decision: no separate `plan-design-review` mockup pass is required before implementation. Run post-implementation browser/QA checks if frontend behavior changes materially.

### P3: DX Scope Is Adequate For Internal Developers

The plan gives the developer a clear path:

- run fake tests first;
- decide outbound dependency before code;
- use local server-only env vars;
- complete manual DashScope smoke verification without committing raw artifacts;
- run `$gstack-review` before PR/merge.

Decision: no additional DX spec work required before implementation.

## Review Outcome

Status: PASS WITH DOCS-ONLY FIXES APPLIED

Remaining implementation guardrails:

- automated tests must remain fake-only;
- real DashScope credentials must only be used during manual verification;
- DashScope provider events must be persisted exactly once by the server proxy path;
- browser code must not relay DashScope provider events to `/v1/realtime/event`;
- no code implementation should begin until the user explicitly starts the execution phase.
