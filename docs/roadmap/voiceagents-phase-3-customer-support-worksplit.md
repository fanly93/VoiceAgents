# VoiceAgents Phase 3 Customer Support Worksplit

Status: DECIDED / DEFERRED
Date: 2026-06-02
Branch: `docs/phase-two-three-worksplit`
Related completed phase: local developer/test validation and report viewer

## Purpose

Phase 3 is the customer support team stage.

The purpose is to help a customer service team take over from the voice agent when the agent cannot or should not complete the conversation alone.

This is different from Phase 2. Phase 2 is about pilot decision evidence. Phase 3 is about operational handoff and support workflow.

The current completed Phase 1 can validate that handoff happens in demo scenarios, but it does not yet provide a production customer support workspace or complete handoff operations.

## Current Boundary

Existing backend already has early handoff concepts:

- `handoff_to_human` tool path,
- handoff reason in validation summaries,
- event and transcript safety boundaries,
- local report viewer sections for customer-service lead review.

These are validation and evidence features. They are not a customer support product.

Phase 3 should begin only when the team needs real support operators to receive, understand, and act on live handoff context.

## Backend Responsibilities

Backend tasks that belong to Phase 3 if this stage is approved:

- Define handoff context schema:
  - session id,
  - call id,
  - merchant id,
  - handoff reason,
  - latest safe customer intent,
  - safe tool result summaries,
  - relevant order / logistics / product knowledge references,
  - confidence / failure reason,
  - timestamps and status.
- Define handoff lifecycle:
  - created,
  - queued,
  - assigned,
  - accepted,
  - resolved,
  - abandoned / expired.
- Define backend APIs for support handoff:
  - list pending handoffs,
  - get handoff detail,
  - assign / accept handoff,
  - update status,
  - append safe internal note if needed.
- Enforce merchant / tenant isolation.
- Enforce agent / support-user permissions.
- Enforce transcript and PII redaction boundaries.
- Store auditable support events.
- Define retention and deletion behavior.
- Add backend tests for lifecycle, permissions, redaction, and malformed session handling.

## Frontend Responsibilities

Frontend tasks that should be handled by the frontend / support product team:

- Customer support workbench.
- Pending handoff queue UI.
- Handoff detail page.
- Conversation / transcript display.
- Customer intent summary layout.
- Accept / resolve / assign controls.
- Support agent notes UI.
- Supervisor view for customer-service lead.
- Real-time notification / refresh UX.
- Keyboard shortcuts and operational workflow polish.

Backend should not build these UI surfaces beyond minimal test harnesses required to prove API behavior.

## Not Our Main Task

The backend team should not take ownership of:

- full customer service console,
- support agent productivity UI,
- supervisor dashboards,
- front-office workflow design,
- visual layout for transcript / conversation review,
- real-time frontend notification experience.

Those are important, but they are frontend/product tasks after the backend contract is known.

## Decision Needed In Office Hours

The core question is whether Phase 3 backend should start now.

### Option A: Do Phase 3 backend now

Choose this only if live or pilot support handoff is the next blocking risk.

Evidence that would justify this:

- a pilot scenario requires a human support agent to receive handoff context,
- the team needs to prove customer support can safely take over,
- current validation reports are insufficient because operators need operational context, not just demo evidence,
- frontend needs a backend handoff API contract to begin support UI work.

Backend scope would be narrow:

- handoff context model,
- lifecycle/status model,
- read-only/list/detail APIs first,
- permission and merchant isolation contract,
- redaction tests,
- no customer support frontend.

### Option B: Defer Phase 3 backend

Choose this if the next milestone is still demo validation or pilot decision-making, not operational support.

This is the conservative default if:

- no support operator will use the system soon,
- no real handoff queue is needed,
- pilot demos only need to show that handoff intent is detected,
- merchant/auth/report sharing is a more immediate dependency.

Deferred backend work should stay documented here, not implemented.

### Current Recommendation

Decision on 2026-06-02: choose Option B. Defer Phase 3 backend work for now.

Reason:

- Phase 3 is primarily customer support operations and support-team product workflow.
- The backend team should not spend the current iteration building support-workbench frontend surfaces.
- No real support operator / support lead is currently blocked on a live handoff queue.
- The current priority should return to backend developer/test tooling gaps from Phase 1.

Revisit Phase 3 backend only when at least one trigger is true:

- A named support operator or support lead needs to receive real handoff context in the next pilot.
- A pilot scenario requires live human takeover rather than demo handoff detection.
- The frontend / support product team is ready to consume handoff lifecycle APIs.
- Validation reports are no longer enough because operators need operational context.

If we do proceed now, do only the backend handoff context contract and lifecycle API. Do not build a customer support workbench in this backend branch.

## Open Questions

- Who is the first support operator or support lead for this workflow?
- Is the next pilot expected to include real human takeover, or only demo handoff detection?
- What handoff context must be visible for a support agent to act without asking the customer to repeat themselves?
- Does handoff need assignment, or is a read-only queue enough for v1?
- What retention rules apply to handoff context?
- Which PII fields are allowed after redaction?
- Does customer support access use merchant-level permissions or internal-only permissions in the first pilot?
