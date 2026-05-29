# VoiceAgents Phone Channel MVP

Status: APPROVED
Source: `.gstack/projects/VoiceAgents/2026-05-29-voiceagents-phone-channel-mvp-design.md`

## Problem

Existing merchants already use the company's text-based intelligent customer service SaaS to replace most human text support. The missing capability is phone support: merchants still keep human phone agents, and some prospects treat phone support as a required buying condition.

The first VoiceAgents product should upgrade existing text-support customers to a phone channel, rather than start as a generic voice bot platform.

## First Wedge

- Pilot merchant: European wig seller.
- Current volume: about 1200 phone calls per month.
- Current staffing: 3 English phone agents.
- Current phone support cost: about RMB 30000 per month.
- Buyer: owner/founder or overseas ecommerce lead.
- Key buying concerns: effect, voice quality, and reliable human handoff.

## MVP Must Prove

1. English phone answering.
2. Spoken order number capture with repeat-back confirmation.
3. Order lookup.
4. Logistics lookup.
5. Product consultation through existing RAG knowledge.
6. Reliable human handoff with context.

## Explicitly Later

- Full merchant configuration backend.
- Multi-language support.
- Outbound calling.
- QA dashboards and reports.
- Automated return/refund decisions.
- Complex complaint handling.

## Success Criteria

- Automatic resolution target: 60%.
- Handoff target: 30%.
- Order/logistics query success target: 60%.
- Remaining 10% must be classified, not left as unknown.
- Product consultation should show no obvious customer dissatisfaction in review.

