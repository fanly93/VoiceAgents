# VoiceAgents Pilot Validation Harness v1

Status: APPROVED FOR SPEC
Date: 2026-06-01
Branch: `feat/product-cut-discovery`

## Office-Hours Decision

The next product cut is a local pilot validation harness for the existing `/realtime-test` surface.

The goal is not to build merchant admin, customer-service back office, production authentication, telephony, or a public demo site. The goal is to make real voice validation repeatable enough that engineering can run five standard scenarios and produce a redacted report that later supports merchant demo review and human handoff context review.

## User And Job

Primary user: the developer/operator validating VoiceAgents real voice behavior.

Secondary readers of the output:

- Pilot merchant stakeholders who need a readable demo evidence report.
- Human support operators who need to understand what context would be available at handoff.

The job is:

```text
Choose a standard scenario -> run a realtime voice session -> finish the validation run -> save a redacted result report.
```

## Standard Scenarios

Version 1 includes exactly five fixed scenarios:

1. Order status lookup.
2. Logistics tracking lookup.
3. Product knowledge consultation.
4. Low-confidence or knowledge-miss handoff.
5. User-requested human handoff.

## Product Boundary

In scope:

- Add validation-run controls to `/realtime-test`.
- Generate a server-side `run_id`.
- Capture scenario, session identifiers, provider, model, response mode, observed tools, handoff reason, transcript/assistant summaries, latency samples, provider errors, and manual assertions.
- Persist local, gitignored validation outputs:
  - `.voiceagents/validation-runs/<run_id>/summary.json`
  - `.voiceagents/validation-runs/<run_id>/report.md`
- Keep all saved text redacted and safe for local development review.

Out of scope:

- CLI entrypoint.
- Merchant-facing account UI.
- Customer-service back office workflow.
- Production auth or multi-tenant permissions.
- Telephony, phone numbers, inbound or outbound calls.
- Raw audio storage.
- Persisting OpenAI client secrets, tool tokens, authorization headers, SDP, raw tool arguments, or unredacted transcript.

## Decision Rationale

The project already proves that browser OpenAI Realtime voice works and that failure modes are covered by automated simulation. The next missing capability is repeatable evidence. Without a validation harness, each test relies on the operator reading panels and remembering whether the run passed.

The smallest useful product increment is therefore a validation-run report, not a new provider, not telephony, and not a polished merchant UI.

## Recommended Approach

Use the existing `/realtime-test` page as the entrypoint.

- The browser starts and finishes validation runs through new local development API endpoints.
- The browser submits only safe observed values and manual assertions.
- The backend owns `run_id` generation, validation, redaction, pass/fail rule evaluation, and local file writing.
- Reports are local-only under `.voiceagents/validation-runs/`.

This keeps the feature close to the real validation workflow while avoiding production assumptions.

## Success Definition

The feature succeeds when a developer can run each of the five standard scenarios and finish with a local `summary.json` and `report.md` that answer:

- Which scenario was run?
- Was the session established and completed?
- Which expected tools appeared?
- Was the expected handoff observed?
- Were transcript and assistant response present?
- Were provider errors observed?
- Did the operator manually confirm voice/demo/business quality?
- Did the saved report pass the blocked-secret scan?

