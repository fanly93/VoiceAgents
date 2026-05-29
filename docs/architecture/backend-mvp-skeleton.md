# Backend MVP Skeleton Architecture

Status: IMPLEMENTED

## Scope

This backend skeleton supports local simulation of the VoiceAgents phone-channel MVP without real recordings, real telephony, or production merchant APIs.

## Module Map

- `voiceagents/contracts/`
  Pydantic request/response models and shared enums for tool boundaries.
- `voiceagents/adapters/`
  Deterministic mock implementations for order lookup, logistics lookup, product knowledge, and human handoff.
- `voiceagents/agent/`
  Call-flow input/output models and deterministic orchestration service.
- `voiceagents/api/`
  FastAPI app factory, health endpoint, simulation endpoint, and uvicorn import target.
- `voiceagents/call_evaluation.py`
  Phase 0 call-evaluation dataset validator.

## Request Flow

```text
POST /v1/calls/simulate
  -> CallFlowInput
  -> CallFlowService.handle()
  -> Mock adapter(s)
  -> CallFlowOutput
```

The service uses explicit handoff rules before attempting unsupported automation. Low ASR confidence, customer-requested human, complaints, and return/refund requests all hand off.

## Supported Simulation Paths

- Low ASR confidence -> handoff.
- Customer requests human -> handoff.
- Complaint -> handoff.
- Return/refund -> handoff.
- Confirmed order status -> mock order lookup.
- Confirmed logistics tracking -> mock logistics lookup.
- Known product usage question -> mock product knowledge response.
- Unknown product usage question -> handoff.
- Unsupported intent -> handoff.

## Non-Goals

- No production telephony.
- No real ASR or TTS.
- No real merchant order, logistics, or RAG API calls.
- No raw recordings or PII.
- No dashboard UI.
- No automatic return/refund approval.

## Verification

```bash
python3 -m pytest
python3 scripts/validate_call_evaluations.py data/call-evaluations/sample.json
```

