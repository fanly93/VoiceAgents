# VoiceAgents Other Provider Integration Spec

Status: PLANNED / NO CODE STARTED
Date: 2026-06-02
Branch: `feat/other-provider-integration-planning`
Source design: `docs/designs/voiceagents-other-provider-integration.md`

## Goal

Add a provider-neutral voice model integration foundation and use DashScope Qwen-Omni Realtime as the first non-OpenAI provider target.

The goal is to make future providers faster and safer to add without changing VoiceAgents business tool adapters, event logs, transcript logs, validation reports, or handoff logic.

## Users

Primary users:

- backend developer adding a new voice model provider;
- developer/tester running local realtime voice validation against a non-OpenAI provider.

Secondary users:

- operator comparing whether a provider is configured correctly;
- future frontend engineer consuming provider-neutral connection metadata.

## Problem

OpenAI Realtime voice is now implemented and locally diagnosable, but the next providers should not be added by copying OpenAI-specific code. The current provider layer has useful abstractions, but several surfaces still encode OpenAI assumptions:

- provider enum only includes `mock` and `openai_realtime`;
- client-secret response shape is OpenAI-oriented;
- browser connection path is OpenAI WebRTC-specific;
- tool-call execution derives provider from process env instead of session provider binding;
- diagnostics are OpenAI-specific;
- no explicit capability model exists for native realtime versus cascaded ASR/TTS providers.

## Scope

### Provider-Neutral Contracts

Introduce explicit provider capability and connection concepts.

Required provider capability fields:

- provider name;
- supported modes: native realtime, ASR, TTS, or cascaded;
- supported connection modes:
  - `browser_webrtc_ephemeral`,
  - `server_websocket_proxy`,
  - `server_sdk_proxy`,
  - `cascaded_pipeline`;
- supported response modes: text, voice;
- supports native function/tool calling;
- supports server-side credential only;
- default model and voice names;
- provider-specific diagnostics checks.

Required provider connection response concepts:

- provider;
- session id;
- call id;
- connection mode;
- browser-safe connection URL or local proxy URL;
- optional browser-safe ephemeral credential;
- expires at;
- model;
- voice;
- session config;
- session-bound `tool_call_token`.

The response must never expose long-lived provider API keys.

### Provider Registry And Factory

Add a provider registry/factory so provider construction is data-driven and testable.

The factory must support:

- mock provider;
- OpenAI realtime provider;
- DashScope realtime provider;
- unsupported provider diagnostics without crashing the app.

### Multi-Provider Session Binding

Tool-call and event ingestion must use the session's stored provider binding, not only the current process env.

Acceptance requirement:

- a tool call for a DashScope session cannot be accepted as an OpenAI session;
- a tool call for an OpenAI session cannot be accepted as a DashScope session;
- a changed `VOICEAGENTS_REALTIME_PROVIDER` after session creation must not silently rebind an existing session.

### DashScope First Provider

First target:

```text
VOICEAGENTS_REALTIME_PROVIDER=dashscope_realtime
VOICEAGENTS_DASHSCOPE_API_KEY=<server-only>
VOICEAGENTS_DASHSCOPE_REALTIME_MODEL=qwen3.5-omni-flash-realtime
VOICEAGENTS_DASHSCOPE_REALTIME_VOICE=<provider default or configured voice>
VOICEAGENTS_DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com
```

`qwen3.5-omni-plus-realtime` should be supported by configuration, not hardcoded into the first implementation.

DashScope v1 connection mode:

```text
server_websocket_proxy
```

The browser must connect to a VoiceAgents local proxy endpoint. VoiceAgents then connects to DashScope using the server-side API key.

DashScope v1 must map:

- session lifecycle events;
- user transcript partial/final;
- assistant text/audio transcript partial/final where available;
- native function/tool-call requests;
- tool result events back to DashScope;
- provider errors to safe `session.error` events.

### Cascaded Provider Design

Do not implement cascaded ASR/TTS in v1 unless DashScope Omni access is blocked.

The design must still reserve a clean path for:

```text
ASR provider -> VoiceAgents LLM/tools -> TTS provider
```

Recommended future DashScope cascaded models:

- ASR: `qwen3-asr-flash-realtime` or `fun-asr-realtime`;
- TTS: `qwen3-tts-flash-realtime` or `qwen3-tts-instruct-flash-realtime`;
- TTS quality fallback: `cosyvoice-v3-flash`.

### Diagnostics

Extend realtime dev diagnostics to support provider-specific checks.

DashScope checks:

- provider is supported;
- dev endpoint gate is enabled when required;
- `DASHSCOPE_API_KEY` is present server-side;
- DashScope model is configured;
- base URL/region is configured;
- connection mode is supported;
- transcript logging mode remains valid;
- client-secret/session creation rate limit remains valid.

Diagnostics must not call DashScope or print key values.

### Test Page / Developer Surface

The first DashScope developer surface can remain utilitarian. It does not need frontend polish.

Minimum requirement:

- `/realtime-test` can show provider, model, connection mode, and diagnostics;
- OpenAI WebRTC path remains working;
- DashScope uses a distinct adapter/proxy path instead of pretending to be OpenAI WebRTC;
- failed provider events are shown as safe summaries.

### Safety Requirements

Never expose or persist:

- `DASHSCOPE_API_KEY`;
- provider API keys from any provider;
- AK/SK, SecretId/SecretKey, APISecret, access tokens, OAuth tokens;
- client secret or long-lived provider credential;
- `tool_call_token`;
- Authorization headers;
- SDP;
- raw audio;
- audio bytes;
- raw tool arguments;
- real customer PII;
- unredacted transcripts.

All provider errors returned to the browser or logs must be safe summaries.

## Non-Goals

- No provider selection UI for production users.
- No multi-provider fallback.
- No provider cost comparison.
- No telephony integration.
- No support workbench UI.
- No merchant-facing UI.
- No production authentication redesign.
- No raw audio persistence.
- No direct provider access to business systems.

## Acceptance Criteria

1. Provider-neutral capability and connection contracts exist and reject extra fields.
2. Provider factory/registry can construct mock, OpenAI realtime, and DashScope realtime providers.
3. Unsupported provider values are diagnosed safely.
4. Existing OpenAI realtime tests still pass.
5. Tool-call execution validates against the session provider binding, not only process env.
6. DashScope realtime provider config and diagnostics exist without exposing secrets.
7. DashScope provider uses a server-side connection/proxy path; browser never receives `DASHSCOPE_API_KEY`.
8. DashScope raw events are normalized into existing loggable event types.
9. DashScope native tool-call events are routed through `RealtimeToolRouter`.
10. Failed DashScope tool calls use existing safe `tool_status` / `error_message` semantics.
11. No raw provider audio, raw tool arguments, or provider secrets are written to logs or validation artifacts.
12. Focused tests pass; full Python test suite passes before review.

## Provider Priority

Implementation priority after DashScope:

1. Volc/Doubao native realtime voice.
2. MiniMax TTS adapter.
3. iFlytek ASR adapter.
4. Azure OpenAI Realtime provider.
5. Gemini Live provider.
6. AWS Nova Sonic provider.
7. Tencent/Baidu ASR/TTS adapters.

This priority can change if account access, model availability, cost, or pilot customer requirements change.
