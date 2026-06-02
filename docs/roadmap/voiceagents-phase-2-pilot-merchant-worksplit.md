# VoiceAgents Phase 2 Pilot Merchant Worksplit

Status: DECIDED / DEFERRED
Date: 2026-06-02
Branch: `feat/pilot-demo-report-sharing-auth`
Related completed phase: local developer/test validation and report viewer

## Purpose

Phase 2 is the pilot merchant stage.

The purpose is not to make the local validation tool prettier. The purpose is to let a real pilot merchant or pilot decision-maker safely review enough evidence to decide whether VoiceAgents should proceed toward a merchant pilot.

The current completed Phase 1 already lets developers and testers:

- run voice validation scenarios,
- generate redacted local validation artifacts,
- review results locally,
- copy a Chinese-first summary for WeChat / Feishu.

Phase 2 begins only when the report needs to leave the developer/tester's local machine or be consumed by a real merchant stakeholder under controlled access.

## Current Boundary

The local report viewer remains a Phase 1 tool:

```text
/realtime-validation-reports
.voiceagents/validation-runs/<run_id>/summary.json
```

It is local-only, gitignored, and has no public sharing, auth, upload, hosted export, merchant account, or production report portal.

Phase 2 should not turn into a frontend polish project. Frontend owns merchant-facing experience. Backend owns the data, security, tenancy, and API contract that make merchant-facing experience safe.

## Backend Responsibilities

Backend tasks that belong to Phase 2 if this stage is approved:

- Define merchant / tenant identity boundary for pilot report access.
- Define whether a report can be shared outside local development at all.
- Create a report sharing contract if needed:
  - share token shape,
  - expiry,
  - revoke / disable,
  - read-only access,
  - audit event for access,
  - no write actions from shared report links.
- Define report data whitelist:
  - allowed readiness fields,
  - allowed scenario labels,
  - allowed checks,
  - allowed business proof,
  - allowed handoff summary,
  - fields explicitly forbidden from public or merchant-visible responses.
- Enforce safety boundary:
  - no raw audio,
  - no SDP,
  - no provider API key,
  - no client secret,
  - no tool token,
  - no Authorization header,
  - no raw tool arguments,
  - no real PII,
  - no unredacted transcript.
- Decide persistence model:
  - continue local-only,
  - upload sanitized report snapshot,
  - or store report records in a backend database.
- Add API endpoints only if the product decision requires them.
- Add backend tests for auth, expiry, revocation, field whitelist, and redaction.

## Frontend Responsibilities

Frontend tasks that should be handled by the frontend team:

- Merchant-facing report page.
- Visual hierarchy for merchant / boss / decision-maker readers.
- Mobile screenshot and WeChat / Feishu forwarding layout.
- Branding, typography, spacing, responsive design, and copy polish.
- Share link UI and expired-link UI.
- Merchant-facing empty / error states.
- Any public report portal or merchant dashboard experience.
- Any PDF / image export UI if product later approves it.

Backend should not build these beyond minimal API/static smoke surfaces needed for backend validation.

## Not Our Main Task

The backend team should not take ownership of:

- polished merchant-facing frontend,
- marketing-style report design,
- visual report templates,
- merchant dashboard navigation,
- frontend routing structure beyond API contract compatibility,
- screenshot-ready design quality.

Those tasks can be planned here for clarity, but should be executed by the frontend team later.

## Decision Needed In Office Hours

The core question is whether Phase 2 backend should start now.

### Option A: Do Phase 2 backend now

Choose this only if there is concrete demand for controlled report access outside the developer/tester's machine.

Evidence that would justify this:

- a named boss / merchant / decision-maker needs to open a report link,
- screenshots/manual forwarding are blocking a pilot decision,
- sharing without auth is unsafe,
- the team needs a backend contract so frontend can begin merchant-facing work.

Backend scope would be narrow:

- report share API contract,
- token / expiry / revoke model,
- sanitized report snapshot or read-only retrieval,
- auth and redaction tests,
- no polished frontend.

### Option B: Defer Phase 2 backend

Choose this if the next pilot can still be handled by local report viewer plus manual copy.

This is the conservative default if:

- no external merchant has asked for link access,
- no pilot decision is blocked by report sharing,
- frontend is not ready to consume a backend contract,
- production tenancy/auth decisions are still unclear.

Deferred backend work should stay documented here, not implemented.

### Current Recommendation

Decision on 2026-06-02: choose Option B. Defer Phase 2 backend work for now.

Reason:

- Phase 2 is primarily pilot merchant productization and frontend/report experience.
- The backend team should not spend the current iteration building merchant-facing frontend surfaces.
- There is not yet a concrete pilot merchant stakeholder or blocked decision that requires controlled report link access.
- The current priority should return to backend developer/test tooling gaps from Phase 1.

Revisit Phase 2 backend only when at least one trigger is true:

- A named boss / merchant / decision-maker needs controlled access to a report outside the developer/tester's local machine.
- Manual screenshot / WeChat / Feishu forwarding blocks a pilot decision.
- The frontend team is ready to consume a report-sharing backend contract.
- Security review decides local/manual sharing is unsafe for the next pilot.

If we do proceed now, do only the backend contract and safety model. Do not build a merchant-facing frontend in this backend branch.

## Open Questions

- Who is the first non-developer reader of a report?
- Is that reader internal boss/decision-maker or an actual pilot merchant contact?
- Does the reader need a link, or is WeChat / Feishu copy enough for the next pilot?
- Should shared reports expire?
- Who can revoke a shared report?
- Is report access merchant-scoped or only token-scoped for v1?
- Do we need persistent sanitized report snapshots, or can links read from existing validation run records?
