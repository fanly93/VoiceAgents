# VoiceAgents Pilot Demo Report Viewer

Status: REVIEWED / READY FOR IMPLEMENTATION
Date: 2026-06-02
Branch: `feat/pilot-demo-report-viewer`

## Problem Statement

The current realtime validation workflow can produce local `summary.json` and `report.md` artifacts, but those artifacts are still hard to consume quickly. After a voice demo, the operator currently screenshots the demo page and manually summarizes the result into WeChat or Feishu. That takes about 30 minutes and makes the demo evidence hard for non-engineering readers to understand.

The next product cut is a local Pilot Demo Report Viewer: a simple, readable page that turns one saved validation run into a decision-friendly report, with a recent-run list for navigation.

## Demand Evidence

Observed demand is internal but concrete:

- The current `/realtime-test` and raw report output are hard for the team itself to understand quickly.
- Demo results need to be forwarded to a boss, customer-service lead, or technical teammate.
- Today that forwarding requires screenshots plus manual written explanation.
- The manual summary step takes about 30 minutes per demo.

This is not a request for a polished marketing frontend. The immediate demand is reducing manual report preparation time and making the evidence readable enough for decision-makers.

## Status Quo

Current workflow:

1. Run realtime validation on `/realtime-test`.
2. Finish a validation run and save `.voiceagents/validation-runs/<run_id>/summary.json` and `report.md`.
3. Manually inspect the test page, report, and panels.
4. Take screenshots.
5. Rewrite the outcome into WeChat, Feishu, or another message.
6. Explain the context again for readers who do not know the technical fields.

The costly step is not running the validation. The costly step is translating validation evidence into a short, readable decision artifact.

## Target User And Narrowest Wedge

Primary reader:

- Boss / decision-maker deciding whether the voice demo is ready to continue toward pilot validation.

Secondary readers:

- Customer-service lead checking whether handoff and customer experience look acceptable.
- Technical teammate checking whether tools, provider events, and redaction boundaries behaved correctly.

Narrowest wedge:

- A local report viewer page that reads existing validation summaries, auto-selects the newest run when present, and presents one selected run with:
  - overall readiness,
  - scenario coverage,
  - business proof,
  - role-specific sections,
  - copyable Chinese-first WeChat/Feishu summary text.

The first version should reduce post-demo report preparation from about 30 minutes to 1-3 minutes.

## Constraints

- Do not build a flashy or brand-polished frontend.
- Do not build merchant auth, merchant accounts, public sharing, or customer-service back office.
- Do not expose `.voiceagents/validation-runs/` publicly.
- Do not save or render raw audio, SDP, OpenAI API keys, client secrets, tool tokens, Authorization headers, raw tool arguments, real PII, or unredacted transcripts.
- Do not add new validation data collection unless the current summaries are insufficient.
- Prefer simple, testable HTML and backend endpoints that match the existing FastAPI/static-page pattern.

## Premises

1. The real problem is not visual polish; it is turning validation evidence into something non-engineers can understand and forward.
2. The boss / decision-maker is the first reader, so the first screen must answer whether this demo is ready to continue.
3. Existing validation `summary.json` files are the right data source for v1.
4. A local-only viewer is enough for this stage; public share links and auth are later product work.
5. The report must preserve the same safety boundary as the validation harness.

## Approaches Considered

### Approach A: Minimal Local Report Viewer

Add a local page, for example `/realtime-validation-reports`, backed by local endpoints that list validation runs and return a safe report-view model for one run. The page shows decision readiness first, then evidence sections and copyable summary text.

Effort: M
Risk: Low

Pros:

- Fastest way to replace screenshots plus manual summaries.
- Reuses existing `summary.json` files.
- Keeps scope local and safe.
- Creates a natural foundation for future report viewer and handoff viewer work.

Cons:

- Still a local tool, not a merchant-accessible system.
- Requires some backend read/list support for existing validation runs.

### Approach B: Static HTML Report Per Run

Generate a `report.html` file when a validation run finishes.

Effort: S/M
Risk: Low

Pros:

- Simple artifact model.
- Easy to open and screenshot.
- Avoids a run-list endpoint.

Cons:

- Weak browsing experience across multiple runs.
- Harder to add filtering, copy templates, or compare runs.
- Couples report-view changes to validation finish behavior.

### Approach C: Local Report Workspace

Build a larger local workspace with run history, role views, run comparison, copy templates, and future handoff-context viewer hooks.

Effort: L
Risk: Medium

Pros:

- Best long-term trajectory.
- Could become the local operations hub for validation and handoff evidence.

Cons:

- Too much for the current need.
- Risks drifting into a dashboard product before the report shape is proven.

## Recommended Approach

Use Approach A: Minimal Local Report Viewer.

This matches the actual pain: after a demo, the operator needs a clear, local, copyable report quickly. It avoids premature UI polish and avoids building merchant-facing infrastructure before the report content is proven.

## Success Criteria

- A user can open a local viewer page and see recent validation runs.
- A user can open one run and understand in 30 seconds:
  - overall readiness: `Ready for pilot`, `Needs another validation`, or `Blocked`;
  - scenario coverage: which standard scenario ran and whether it passed;
  - business proof: whether voice, business answer, tool use, handoff, and secret scan evidence passed.
- A user can copy a short WeChat/Feishu-ready summary.
- A user can see boss, customer-service, and technical sections without reading raw logs.
- No secret-bearing or raw data fields are rendered.
- Report preparation time drops from about 30 minutes to 1-3 minutes.

## Dependencies

- Existing validation artifacts under `.voiceagents/validation-runs/<run_id>/summary.json`.
- Existing `ValidationRunSummary` and `ValidationCheck` models.
- Existing local FastAPI/static page patterns.
- Existing redaction and blocked-field boundaries.

## Resolved Scope Decisions

- Default state: show the run list and auto-select the newest run when one exists.
- Run scope: v1 shows one selected run at a time. Multi-run packets are explicitly deferred.
- Copy language: v1 summary is Chinese-first for WeChat/Feishu forwarding; optional English labels can appear only if they do not add complexity.
- Readiness authority: readiness is derived from validation checks and safety state. Manual `demo_ready` participates through existing validation checks but cannot override failed safety, provider-error, or expected-tool checks.

## The Assignment

Before implementation, define the exact copyable summary format for a boss / decision-maker. If that message is not clear in WeChat or Feishu, the viewer is solving the wrong problem.

## What I Noticed

- You pushed back on visual polish: "不是要做炫酷美观的前端" is the right constraint at this stage.
- You named the real bottleneck: screenshots plus manual summary take about half an hour.
- You chose the boss / decision-maker as the first reader, which correctly forces the first screen to lead with readiness, not logs.
