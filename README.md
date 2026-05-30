# VoiceAgents

VoiceAgents is the phone-channel MVP track for an existing text-based intelligent customer service SaaS product.

The approved first phase is not a full production phone system. It is Phase 0: build the evaluation schema, synthetic sample corpus, MVP tool contracts, and handoff rules needed before implementing the phone agent.

Real pilot call recordings are not available yet, so real-call evaluation is deferred. Current validation uses synthetic redacted samples only.

## Current Scope

- Create and validate the call evaluation schema with synthetic redacted samples.
- Define tool contracts for order lookup, logistics lookup, product knowledge retrieval, and human handoff.
- Define handoff and failure rules for the MVP.
- Validate call evaluation data before it is used as an acceptance baseline.
- Run local HTTP end-to-end examples against the backend skeleton.
- Validate browser/local realtime voice session plumbing with mock-safe provider behavior.
- Prepare the next OpenAI Realtime browser voice MVP behind a local development gate.

## Out of Scope for the Current Phase

- Production voice-model integration or production realtime provider exposure.
- Publicly exposed OpenAI, ASR, TTS, or realtime voice provider endpoints.
- Telephony provider integration.
- Phone-number provisioning or inbound/outbound calling.
- Audio file input, audio file output, recording processing, or raw audio storage.
- Production merchant API integration.
- Real customer data, raw recordings, or PII.

## Quick Start

Use an isolated project environment. Do not install dependencies into the system Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run tests and sample evaluation validation:

```bash
python -m pytest
python scripts/validate_call_evaluations.py data/call-evaluations/sample.json
```

Run the local backend skeleton:

```bash
python -m uvicorn voiceagents.api.main:app --reload
```

Check health:

```bash
curl http://127.0.0.1:8000/health
```

Simulate a product-support call:

```bash
curl -X POST http://127.0.0.1:8000/v1/calls/simulate \
  -H 'Content-Type: application/json' \
  -d '{
    "call_id": "CALL-REDACTED",
    "merchant_id": "merchant_demo",
    "locale": "en-GB",
    "intent": "product_usage",
    "utterance": "How should I wash my wig?",
    "order_id_candidate": null,
    "order_id_confirmed": false,
    "asr_confidence": 0.91,
    "customer_requested_human": false
  }'
```

Run the local HTTP smoke test against a running server:

```bash
python scripts/smoke_api.py --base-url http://127.0.0.1:8000
```

The smoke script calls `/health`, then submits every JSON payload in `examples/call-simulations/` to `/v1/calls/simulate`.

## Realtime Browser Test

Start the API in mock realtime provider mode. This is the default, but the explicit environment variable keeps local runs clear:

```bash
VOICEAGENTS_REALTIME_PROVIDER=mock python -m uvicorn voiceagents.api.main:app --reload
```

Open the browser test page:

```text
http://127.0.0.1:8000/realtime-test
```

Realtime API endpoints:

- `POST /v1/realtime/client-secret` creates a local realtime session and returns provider credentials plus a session-bound `tool_call_token`.
- `POST /v1/realtime/tool-call` relays approved realtime tool calls to the backend. Send the relay token as `Authorization: Bearer <tool_call_token>`.

OpenAI realtime provider mode is selected with:

```bash
VOICEAGENTS_REALTIME_PROVIDER=openai_realtime
OPENAI_API_KEY=...
VOICEAGENTS_OPENAI_REALTIME_MODEL=gpt-realtime-2
VOICEAGENTS_OPENAI_REALTIME_VOICE=marin
VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true
VOICEAGENTS_TRANSCRIPT_LOGGING=structured
```

`OPENAI_API_KEY` is server-only and must never be exposed to the browser, logs, tickets, screenshots, or committed files. `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true` is a local development gate for the real provider MVP; it is not production authentication and must not be exposed on a public endpoint. If `OPENAI_API_KEY` is missing, the API fails safely with a 503 response instead of exposing provider credentials. Until the OpenAI Realtime MVP implementation lands, mock mode remains the runnable default.

Current realtime scope is browser/local validation only. This phase does not implement telephony, phone-number provisioning, inbound/outbound calling, or raw audio storage.

Local realtime event logs under `.voiceagents/` are gitignored. Treat the tool-call relay token as a short-lived session credential; do not write it to logs, screenshots, tickets, or committed files.

Run the realtime smoke test against a running mock-mode server:

```bash
python scripts/smoke_realtime_api.py --base-url http://127.0.0.1:8000
```

Validate example payload compatibility without starting a server:

```bash
python -m pytest tests/test_example_call_payloads.py
```

## Local Call Simulation Examples

Reusable request payloads live in `examples/call-simulations/`:

- `product-usage.json`
- `order-status.json`
- `logistics-tracking.json`
- `customer-requests-human.json`
- `low-asr-confidence.json`

Real call audio, customer names, phone numbers, order numbers, and other PII must not be committed to this repository. When real recordings become available, store only safe references and redacted annotations.

## Key Documents

- `docs/designs/voiceagents-phone-channel-mvp.md`
- `docs/specs/voiceagents-phase-0-call-evaluation.md`
- `docs/contracts/mvp-tool-contracts.md`
- `docs/contracts/handoff-rules.md`
