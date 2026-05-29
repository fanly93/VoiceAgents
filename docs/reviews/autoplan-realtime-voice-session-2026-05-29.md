# Autoplan Review: Realtime Voice Session MVP

Status: COMPLETE
Branch: `feat/voice-phase-design`
Input design: `docs/designs/voiceagents-realtime-voice-session-mvp.md`
Input spec: `docs/specs/voiceagents-realtime-voice-session-mvp.md`
Task plan: `docs/specs/voiceagents-realtime-voice-session-mvp-tasks.md`
Date: 2026-05-29
Merged PR: https://github.com/fanly93/VoiceAgents/pull/1
Merge commit: `ab79475`

## Summary

The plan was approved, implemented, reviewed, and merged. The shipped phase is browser/local realtime plumbing rather than real OpenAI Realtime WebRTC audio: mock-mode sessions, backend-generated tool definitions, tool-call relay, JSONL event logging, and safe handoff states are implemented; live voice model behavior is deferred.

The review found one important design gap: browser-relayed tool calls need a session-bound relay token, not only `session_id` and `call_id`. The spec and task plan were updated to return a `tool_call_token`, require it through an HTTP authorization header, reject invalid tokens, and prevent credential/token logging.

## CEO Review

Verdict: proceed with the browser-direct Realtime approach.

Why:

- It matches the business goal: prove voice can drive order, logistics, product knowledge, and handoff flows.
- It avoids premature telephony complexity.
- It produces a demoable browser workflow without building a production call center stack.
- It preserves future options: backend Realtime proxy, telephony adapter, and chained ASR/CallFlow/TTS remain possible.

Scope that must stay out:

- real phone numbers
- real inbound/outbound calls
- real human call transfer
- raw audio storage
- real PII
- merchant sales demo polish

Decision: keep Approach A as the next real voice integration direction, with Approach C as a future fallback if speech-to-speech Realtime is too hard to control for deterministic support flows.

## Engineering Review

Verdict: acceptable with explicit security and persistence boundaries.

Required boundaries:

- `RealtimeProvider` only creates provider connection data; it must not execute business tools.
- `/v1/realtime/tool-call` must be the only backend execution path for Realtime function calls.
- tool execution must use allowlisted tool names and Pydantic argument schemas.
- `tool_call_token` must be session-bound, short-lived, hash-stored, sent through an HTTP authorization header, and required for tool-call relay.
- Realtime tool definitions and instructions must be generated from backend schemas and allowlists.
- `client_secret` and `tool_call_token` must never be written to JSONL logs.
- event logging must run redaction before persistence.
- business logic must depend on session/event repository interfaces, not JSONL or in-memory details.

Engineering risk table:

| Risk | Impact | Required mitigation |
| --- | --- | --- |
| Browser forges tool calls | Unauthorized tool execution | session-bound header `tool_call_token`, tool allowlist, schema validation |
| Provider credential leaks | OpenAI account exposure | standard API key server-only, never log client secret |
| Logs capture PII or credentials | Compliance and customer trust risk | redaction hook, no audio, no credentials/tokens, synthetic/redacted fixtures only, gitignored local logs |
| Realtime provider coupling | hard to switch architecture later | provider/session interfaces before OpenAI-specific code |
| Voice UX hides business bugs | hard debugging | text response mode and visible event/tool panels |

## Design Review

Verdict: minimal browser test page is the right UI for this phase.

The page should be an engineering tool, not a sales demo. It should surface the state machine and tool calls clearly:

- session state
- transcript
- response text
- tool calls
- handoff banner
- latency
- provider events

Do not add marketing layout, merchant branding, or visual polish until the voice workflow itself is reliable.

## DX Review

Verdict: task breakdown is implementation-ready.

Good:

- Tests can run in mock mode without OpenAI credentials.
- Real OpenAI verification is manual and optional.
- The task plan keeps contract, persistence, router, API, UI, and docs work separate.
- Existing `/health`, `/v1/calls/simulate`, Phase 7 examples, and smoke patterns remain intact.

Required before implementation is considered complete:

- `python3 -m pytest`
- `python3 scripts/validate_call_evaluations.py data/call-evaluations/sample.json`
- mock Realtime smoke test over local HTTP
- manual OpenAI Realtime browser verification only when credentials are available

## Plan Adjustments Applied

1. Added `tool_call_token` to `RealtimeClientSecretResponse`.
2. Required `/v1/realtime/tool-call` to receive `tool_call_token` through an HTTP authorization header, not the JSON body.
3. Required `/v1/realtime/tool-call` to reject missing, invalid, and expired tokens with HTTP 401 or 403.
4. Required credential and token values to be excluded from JSONL event logs.
5. Added backend-generated Realtime session instructions and tool definitions.
6. Updated task plan to cover token creation, storage, validation, logging protection, and tool-definition generation.

## Deferred To Next Phase

These items remain open for the real voice integration design/spec phase:

1. Which exact default OpenAI Realtime model and voice should be set in config defaults?
2. Should the OpenAI provider use ephemeral client secrets first, or the newer unified WebRTC session initialization first?
3. Should `VOICEAGENTS_EVENT_LOG_PATH` default to enabled local JSONL, or require an explicit env var?

Recommended defaults:

- use mock provider for automated tests
- default real provider model/voice should be selected from current OpenAI docs in the next voice integration phase
- enable JSONL only in local/dev unless explicitly configured

## Completion

Completed and merged in PR #1. Implementation stopped before telephony work, real OpenAI Realtime WebRTC audio, browser microphone capture, real audio storage, real PII handling, and merchant demo UI work. Those require separate design and spec phases.
