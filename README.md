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
- Operate and validate the merged OpenAI Realtime browser voice MVP behind a local development gate.
- Save local redacted realtime validation reports from `/realtime-test` for standard pilot scenarios.
- Review saved local validation reports in the local-only viewer at `/realtime-validation-reports`.

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
./.venv/bin/python -m pip install -e ".[dev]"
```

Run tests and sample evaluation validation:

```bash
./.venv/bin/python -m pytest
./.venv/bin/python scripts/validate_call_evaluations.py data/call-evaluations/sample.json
```

Run the local backend skeleton:

```bash
./.venv/bin/python -m uvicorn voiceagents.api.main:app --reload
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
    "call_id": "CALL-20260601-0901",
    "merchant_id": "merchant_demo",
    "locale": "zh-CN",
    "intent": "product_usage",
    "utterance": "LunaCare 假发护理套装应该怎么清洗假发？",
    "order_id_candidate": null,
    "order_id_confirmed": false,
    "asr_confidence": 0.91,
    "customer_requested_human": false
  }'
```

Run the local HTTP smoke test against a running server:

```bash
./.venv/bin/python scripts/smoke_api.py --base-url http://127.0.0.1:8000
```

The smoke script calls `/health`, then submits every JSON payload in `examples/call-simulations/` to `/v1/calls/simulate`.

## Realtime Browser Test

Start the API in mock realtime provider mode. This is the default, but the explicit environment variable keeps local runs clear:

```bash
VOICEAGENTS_REALTIME_PROVIDER=mock ./.venv/bin/python -m uvicorn voiceagents.api.main:app --reload
```

Open the browser test page:

```text
http://127.0.0.1:8000/realtime-test
```

Realtime API endpoints:

- `POST /v1/realtime/client-secret` creates a local realtime session and returns provider credentials plus a session-bound `tool_call_token`.
- `POST /v1/realtime/tool-call` relays approved realtime tool calls to the backend. Send the relay token as `Authorization: Bearer <tool_call_token>`.

Realtime provider environment variables:

- `VOICEAGENTS_REALTIME_PROVIDER=mock|openai_realtime` selects the mock-safe local provider or the OpenAI Realtime provider. Mock mode is the default for development and automated tests.
- `OPENAI_API_KEY` is required only for `openai_realtime`. It is server-only and must never be exposed to the browser, DOM, logs, tickets, screenshots, or committed files.
- `VOICEAGENTS_OPENAI_REALTIME_MODEL` defaults to `gpt-realtime-2`.
- `VOICEAGENTS_OPENAI_REALTIME_VOICE` defaults to `marin`.
- `VOICEAGENTS_TRANSCRIPT_LOGGING=off|structured|transcript` controls transcript text logging. When unset, it defaults to `structured`; use `transcript` only when local development explicitly needs verbatim transcript text.
- `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=false|true` gates the real provider client-secret endpoint. It defaults to `false`; set it to `true` only for local OpenAI Realtime development.

OpenAI realtime provider mode can be run locally with:

```bash
VOICEAGENTS_REALTIME_PROVIDER=openai_realtime
OPENAI_API_KEY=...
VOICEAGENTS_OPENAI_REALTIME_MODEL=gpt-realtime-2
VOICEAGENTS_OPENAI_REALTIME_VOICE=marin
VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true
VOICEAGENTS_TRANSCRIPT_LOGGING=structured
```

`VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true` is a local development gate for the real provider MVP; it is not production authentication and must not be exposed on a public endpoint. If `OPENAI_API_KEY` is missing, the API fails safely with a 503 response instead of exposing provider credentials. Development and tests must run inside an isolated `.venv` or conda environment, not the system Python environment.

Current realtime scope is browser/local validation only. This phase does not implement telephony, phone-number provisioning, inbound/outbound calling, or raw audio storage.

Local realtime event logs under `.voiceagents/` are gitignored. Treat the tool-call relay token as a short-lived session credential; do not write it to logs, screenshots, tickets, or committed files.

Run the realtime smoke test against a running mock-mode server:

```bash
./.venv/bin/python scripts/smoke_realtime_api.py --base-url http://127.0.0.1:8000
```

The realtime smoke script is intentionally mock-mode only. It validates `/health`, client-secret minting, the four approved tool calls, unknown tool rejection, and missing authorization rejection without requiring `OPENAI_API_KEY`. Real OpenAI voice verification is manual; use `docs/specs/voiceagents-openai-realtime-voice-mvp-manual-checklist.md` for the 3 minute `/realtime-test` run and browser failure-mode checks.

### Local Realtime Validation Reports

The `/realtime-test` page includes a local validation harness for five standard scenarios:

- order status lookup
- logistics tracking lookup
- product knowledge consultation
- knowledge miss handoff
- customer requested human

Use `Start` to create or connect a realtime session, then use `Start Validation Run` before the scenario you want to capture. After the conversation finishes, set the manual assertions and click `Finish Run`.

Use the local validation report viewer to review saved runs:

```text
http://127.0.0.1:8000/realtime-validation-reports
```

The viewer reads redacted summaries from `.voiceagents/validation-runs/<run_id>/summary.json` through:

- `GET /v1/realtime/validation-report-runs`
- `GET /v1/realtime/validation-report-runs/{run_id}`

The v1 viewer is local-only. It does not provide public sharing, authentication, upload, export hosting, or a production report portal. Plan report prep for a pilot/demo review as a 1-3 minute local workflow after the validation run is finished.

The API writes redacted local artifacts:

```text
.voiceagents/validation-runs/<run_id>/summary.json
.voiceagents/validation-runs/<run_id>/report.md
```

The `.voiceagents/validation-runs/` artifact boundary is local-only and remains gitignored. Saved validation artifacts must not be committed and must not contain raw audio, SDP, API keys, client secrets, tool tokens, Authorization headers, raw tool arguments, real PII, or unredacted transcripts.

Focused validation harness tests:

```bash
./.venv/bin/python -m pytest tests/test_realtime_validation.py tests/test_api_realtime_validation.py tests/test_realtime_test_page_validation_flow.py -v
```

Validate example payload compatibility without starting a server:

```bash
./.venv/bin/python -m pytest tests/test_example_call_payloads.py
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
