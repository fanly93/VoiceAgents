# VoiceAgents

VoiceAgents is the phone-channel MVP track for an existing text-based intelligent customer service SaaS product.

The approved first phase is not a full production phone system. It is Phase 0: build the real-call evaluation corpus, MVP tool contracts, and handoff rules needed before implementing the phone agent.

## Current Scope

- Create a 20-30 call evaluation corpus from real pilot merchant calls.
- Define tool contracts for order lookup, logistics lookup, product knowledge retrieval, and human handoff.
- Define handoff and failure rules for the MVP.
- Validate call evaluation data before it is used as an acceptance baseline.

## Quick Start

```bash
python3 -m pytest
python3 scripts/validate_call_evaluations.py data/call-evaluations/sample.json
```

Real call audio, customer names, phone numbers, order numbers, and other PII must not be committed to this repository. Store only safe references and redacted annotations.

## Key Documents

- `docs/designs/voiceagents-phone-channel-mvp.md`
- `docs/specs/voiceagents-phase-0-call-evaluation.md`
- `docs/contracts/mvp-tool-contracts.md`
- `docs/contracts/handoff-rules.md`
