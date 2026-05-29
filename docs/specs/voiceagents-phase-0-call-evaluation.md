# VoiceAgents Phase 0: Call Evaluation Corpus and MVP Contract

Status: APPROVED

## Goal

Create the evaluation baseline and contracts required before implementing the phone-channel MVP.

This phase does not implement production telephony, ASR, TTS, RAG, or order integrations. It creates the assets that make those implementation tasks testable.

## Deliverables

1. A 20-30 call evaluation corpus using real pilot merchant calls.
2. A validated annotation schema for each call.
3. Tool/API contracts for the MVP.
4. Handoff and failure-mode rules.
5. A 30-day MVP sequencing plan.

## Required Call Annotation Fields

- `call_id`
- `audio_file_ref`
- `language`
- `market`
- `customer_segment`
- `intent_primary`
- `intent_secondary`
- `requires_order_id`
- `order_id_spoken`
- `order_id_transcript`
- `order_id_confidence`
- `tool_required`
- `rag_answer_required`
- `should_handoff`
- `handoff_reason`
- `human_agent_resolution`
- `expected_voice_response_summary`
- `privacy_notes`

## Acceptance Criteria

- 20-30 real call samples are annotated.
- Calls cover order/logistics, product usage, pre-sales consultation, return/refund, and complaint cases where possible.
- Each handoff case has a clear handoff reason and context summary.
- Order-number cases separately track recognition confidence and confirmation outcome.
- No raw audio, PII, customer names, phone numbers, or real order IDs are committed to the repository.
- `python3 -m pytest` passes.
- `python3 scripts/validate_call_evaluations.py data/call-evaluations/sample.json` validates the sample corpus.
