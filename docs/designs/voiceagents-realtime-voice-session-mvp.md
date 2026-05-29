# Realtime Voice Session MVP

Status: DRAFT
Source: `.gstack/projects/fanly93-VoiceAgents/feat-voice-phase-design-design-20260529-162816.md`

## Summary

This phase designs a browser/local realtime voice MVP for VoiceAgents. It proves that live speech can drive existing business tools and enter safe handoff states without implementing production telephony.

Chosen approach: browser connects directly to OpenAI Realtime over WebRTC using backend-minted ephemeral credentials. The browser relays Realtime function calls to the VoiceAgents backend through `POST /v1/realtime/tool-call`; the backend validates and executes approved tools.

## In Scope

- Minimal browser realtime voice test page.
- OpenAI Realtime as first provider behind a provider abstraction.
- Backend endpoint for ephemeral Realtime client credentials.
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

## Confirmed Product Goals

- Core success is business workflow proof: voice triggers correct tools and safe handoff.
- Supported paths: order status, logistics tracking, product consultation, refund/return/complaint/customer-requested-human handoff, and low confidence handoff.
- Text and voice response modes are both needed: text for debugging and tests, voice for demo.
- Voice quality, latency, and interruption behavior should be measured, but are not the only hard gate.

## Architecture

```text
Browser test page
  -> requests ephemeral Realtime credentials from VoiceAgents backend
  -> connects to OpenAI Realtime over WebRTC
  -> receives Realtime function call events
  -> POSTs tool call to VoiceAgents backend
  -> sends function_call_output back to Realtime

VoiceAgents backend
  -> validates session, merchant, tool_name, and arguments
  -> executes existing CallFlowService/adapters
  -> writes redacted structured events
  -> returns safe tool result or handoff event
```

## Initial Backend Surface

### `POST /v1/realtime/client-secret`

Creates a provider-specific ephemeral credential for browser Realtime sessions. Standard OpenAI API keys stay server-side.

The response also returns a session-bound `tool_call_token` for `/v1/realtime/tool-call`. This token is not an OpenAI credential; it only authorizes tool-call relay for the created VoiceAgents session.

### `POST /v1/realtime/tool-call`

Executes an approved Realtime function call.

Required protections:

- tool allowlist
- session-bound `tool_call_token`
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

Never save raw audio. Never commit real phone numbers, names, addresses, real order IDs, or unredacted PII.

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
- Order/logistics/product consultation paths call the correct backend tool.
- Refund, complaint, low confidence, and user-requested-human paths enter `handoff_pending`.
- Unknown tools are rejected.
- Tool arguments are schema-validated.
- JSONL logs do not contain audio.
- Basic redaction runs before transcript/event persistence.

Measured but not first-phase blockers:

- first response latency
- full response latency
- interruption quality
- voice naturalness
- transcript accuracy under realistic accents/noise

## Next Step

Create an implementation spec and task breakdown for this design. Do not start coding until the spec defines phases, out-of-scope items, interfaces, tests, and verification commands.
