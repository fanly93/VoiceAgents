# Realtime Voice Session MVP

Status: IMPLEMENTED
Source: `.gstack/projects/fanly93-VoiceAgents/feat-voice-phase-design-design-20260529-162816.md`
Merged PR: https://github.com/fanly93/VoiceAgents/pull/1
Merge commit: `ab79475`

## Summary

This phase designed and shipped a browser/local realtime plumbing MVP for VoiceAgents. It proves that the browser test surface can create a realtime-like session, receive backend-generated tool definitions, relay tool calls to existing business tools, and enter safe handoff states without implementing production telephony.

Shipped approach: the browser receives mock-safe provider credentials plus backend-generated Realtime session instructions and tool definitions, then relays tool calls to the VoiceAgents backend through `POST /v1/realtime/tool-call`; the backend validates and executes approved tools. Real OpenAI Realtime WebRTC, microphone capture, and live speech-to-speech behavior are deferred to the next voice integration phase.

## In Scope

- Minimal browser realtime voice test page.
- Mock Realtime provider as the automated-test provider.
- OpenAI Realtime provider boundary with missing-key safe failure.
- Backend endpoint for ephemeral Realtime client credentials.
- Backend-generated Realtime session instructions and tool definitions.
- Unified backend tool-call endpoint: `POST /v1/realtime/tool-call`.
- Tool paths for order lookup, logistics lookup, product knowledge, and handoff.
- In-memory session store.
- JSONL event log for structured events and redacted transcript text.
- Repository interfaces reserved for future database persistence.
- Redaction hook with basic order-like ID, phone number, and email redaction.

## Out of Scope

- Production telephony.
- Real phone numbers.
- Inbound or outbound calling.
- Twilio or other telephony provider integration.
- Real human call transfer.
- Audio recording storage.
- Real customer PII in repo, fixtures, or local logs.
- Merchant-facing sales demo UI.
- Real OpenAI Realtime WebRTC session wiring.
- Browser microphone capture and playback.
- Live speech-to-speech voice model verification.

## Confirmed Product Goals

- Core success is business workflow proof: voice triggers correct tools and safe handoff.
- Supported paths: order status, logistics tracking, product consultation, refund/return/complaint/customer-requested-human handoff, and low confidence handoff.
- Text and voice response modes are both needed: text for debugging and tests, voice for demo.
- Voice quality, latency, and interruption behavior should be measured, but are not the only hard gate.

## Architecture

```text
Browser test page
  -> requests mock-safe Realtime connection data from VoiceAgents backend
  -> receives backend-generated session instructions and tool definitions
  -> can relay simulated Realtime function calls
  -> POSTs tool call to VoiceAgents backend
  -> displays safe tool result or handoff state

VoiceAgents backend
  -> validates session, merchant, tool_name, and arguments
  -> executes existing CallFlowService/adapters
  -> writes redacted structured events
  -> returns safe tool result or handoff event
```

## Initial Backend Surface

### `POST /v1/realtime/client-secret`

Creates a provider-specific ephemeral credential for browser Realtime sessions. Standard OpenAI API keys stay server-side.

The response also returns backend-generated Realtime session instructions, tool definitions, and a session-bound `tool_call_token` for `/v1/realtime/tool-call`. This token is not an OpenAI credential; it only authorizes tool-call relay for the created VoiceAgents session.

The browser must send `tool_call_token` as an HTTP authorization header when relaying tool calls. It must not include the token inside the JSON request body.

### `POST /v1/realtime/tool-call`

Executes an approved Realtime function call.

Required protections:

- tool allowlist
- session-bound `tool_call_token` from HTTP authorization header
- per-tool Pydantic argument schema
- merchant/session/call validation
- safe result fields only
- consistent tool error mapping
- handoff output for unsupported or unsafe flows

## Session State

Initial states:

- `idle`
- `listening`
- `transcribing`
- `thinking`
- `tool_calling`
- `speaking`
- `handoff_pending`
- `ended`
- `error`

## Persistence Direction

First implementation:

- `InMemoryVoiceSessionStore`
- `JsonlVoiceEventRepository`

Future implementation:

- `VoiceSessionRepository`
- `VoiceEventRepository`
- database-backed persistence

Business logic must depend on repository interfaces, not JSONL or in-memory details.

## Event Logging Rules

Save structured events and redacted text transcript only.

Never save raw audio. Never commit real phone numbers, names, addresses, real order IDs, unredacted PII, provider credentials, or tool-call relay tokens. The default local event-log directory must be gitignored.

Event fields should include session/call identifiers, state, event type, redacted transcript, redacted response, tool name, safe tool summary, handoff reason, latency, provider metadata, and whether redaction was applied.

## OpenAI Docs Basis

- Realtime sessions are intended for low-latency live audio.
- Browser/mobile clients that capture or play audio directly should use WebRTC.
- Browser clients must not receive standard OpenAI API keys; the backend must mint ephemeral credentials or initialize sessions server-side.
- Realtime function tools allow application-owned business logic to execute a tool and return `function_call_output`.

References:

- https://developers.openai.com/api/docs/guides/realtime
- https://developers.openai.com/api/docs/guides/voice-agents
- https://developers.openai.com/api/docs/guides/realtime-webrtc
- https://developers.openai.com/api/docs/guides/realtime-mcp

## Success Criteria

Hard gates:

- Browser never exposes standard OpenAI API key.
- Realtime credentials are minted by backend.
- Realtime tool definitions and instructions come from the backend allowlist, not browser hardcoding.
- Order/logistics/product consultation paths call the correct backend tool.
- Refund, complaint, low confidence, and user-requested-human paths enter `handoff_pending`.
- Unclear speech or unconfirmed order identifiers trigger one clarification attempt before handoff.
- Unknown tools are rejected.
- Tool arguments are schema-validated.
- JSONL logs do not contain audio.
- JSONL logs do not contain provider credentials, relay tokens, or unredacted PII.
- Basic redaction runs before transcript/event persistence.

Measured but not first-phase blockers:

- first response latency
- full response latency
- interruption quality
- voice naturalness
- transcript accuracy under realistic accents/noise

## Implementation Result

Implemented and merged in PR #1. The shipped scope is browser/local realtime plumbing with mock-mode HTTP verification, not real OpenAI Realtime WebRTC audio.

Shipped artifacts:

- `voiceagents/realtime/` contracts, providers, session store, event log, redaction, and tool router.
- `POST /v1/realtime/client-secret`
- `POST /v1/realtime/tool-call`
- `GET /realtime-test`
- `scripts/smoke_realtime_api.py`
- README setup instructions.

Next phase: design real OpenAI Realtime WebRTC voice integration, including microphone capture, audio playback, provider session creation, turn-taking behavior, interruption behavior, and manual voice quality verification.
