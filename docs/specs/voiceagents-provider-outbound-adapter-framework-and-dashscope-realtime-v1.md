# VoiceAgents Provider Outbound Adapter Framework And DashScope Realtime V1 Spec

Status: PLANNED / NO CODE STARTED
Date: 2026-06-02
Branch: `feat/dashscope-realtime-outbound`
Source design: `docs/designs/voiceagents-provider-outbound-adapter-framework.md`

## Goal

Build a provider-neutral outbound realtime adapter framework and use DashScope Qwen-Omni-Realtime as the first real server WebSocket provider.

This phase must let a local developer test a real DashScope voice model with a server-only API key while preserving the future extension path for Volc, GLM, and other providers.

## Users

Primary users:

- backend developer adding or testing realtime voice providers;
- developer/tester running a local real DashScope smoke test;
- future developer adding a provider-specific adapter for GLM, Volc, or another provider.

Secondary users:

- operator reading diagnostics and validation reports;
- frontend developer consuming provider-neutral local connection metadata.

## Problem

The current provider-neutral foundation can create DashScope proxy metadata and fake-test a browser-safe proxy route, but it cannot connect to real DashScope yet.

Current implementation:

- exposes `VOICEAGENTS_REALTIME_PROVIDER=dashscope_realtime`;
- returns `server_websocket_proxy` metadata for DashScope;
- has `WS /v1/realtime/dashscope/proxy/{session_id}`;
- validates browser-to-proxy envelopes;
- can relay a fake upstream response;
- keeps `/v1/realtime/tool-call` session-provider-bound.

Missing implementation:

- provider-neutral outbound transport contract;
- provider-neutral proxy coordinator;
- real DashScope WebSocket outbound client;
- DashScope-native session/tool/audio event mapping based on official realtime docs;
- browser adapter behavior for real DashScope audio/control/tool-result flow;
- manual checklist for one real provider smoke run.

## Why Now

The next development objective is to verify whether non-OpenAI voice providers can run through VoiceAgents. If DashScope is hardwired directly into `app.py`, later Volc/GLM integrations will repeat protocol, token, event, and tool-routing risks. The framework must be introduced before the first real non-OpenAI outbound provider is implemented.

## Official Protocol Evidence

DashScope Qwen-Omni-Realtime official docs show:

- WebSocket and WebRTC are both supported.
- WebSocket is suitable for server-side integration.
- WebSocket endpoint is `wss://dashscope.aliyuncs.com/api-ws/v1/realtime` for Beijing region, with `?model=<model>`.
- WebSocket uses `Authorization: Bearer DASHSCOPE_API_KEY`.
- WebRTC is whitelist-gated and also uses `Authorization: Bearer DASHSCOPE_API_KEY`.
- WebSocket audio input is sent through `input_audio_buffer.append` and committed depending on VAD mode.
- text/audio responses are emitted through provider events such as transcript and audio deltas.
- Function Calling is supported, with provider-native function-call request and function-call output events.
- DashScope Realtime docs note some tool controls, including `tool_choice` and `parallel_tool_calls`, are not supported for this model family.

Sources:

- https://help.aliyun.com/zh/model-studio/realtime
- https://help.aliyun.com/zh/model-studio/qwen-function-calling

Volc and GLM evidence:

- Volc realtime audio/video Function Calling uses a different task/RTC/message shape, so it should be a separate adapter later.
- GLM-Realtime is WebSocket based and uses Authorization headers, which supports the same server-proxy principle but should not be implemented in this branch.

Sources:

- https://www.volcengine.com/docs/6348/1554654
- https://docs.bigmodel.cn/cn/guide/models/sound-and-video/glm-realtime
- https://docs.bigmodel.cn/cn/asyncapi/realtime

## Scope

### Provider-Neutral Outbound Contracts

Introduce provider-neutral contracts under `voiceagents/realtime/` for outbound realtime behavior.

Required contract concepts:

- transport event kind: JSON, audio, close, error;
- browser proxy message kind: audio, control, tool result;
- provider outbound transport protocol with async connect/send/receive/close behavior;
- provider adapter protocol with provider URL/header/session/tool/audio/result mapping;
- proxy coordinator that binds browser WebSocket, session store, provider adapter, outbound transport, event ingestion, and tool routing.

The contracts must be fake-testable without real provider credentials.

### DashScope Adapter

Extend `voiceagents/realtime/dashscope.py` or split focused DashScope modules if the file becomes too large.

DashScope adapter must support:

- building WebSocket URL from `VOICEAGENTS_DASHSCOPE_BASE_URL` and `VOICEAGENTS_DASHSCOPE_REALTIME_MODEL`;
- building provider headers from `VOICEAGENTS_DASHSCOPE_API_KEY` without exposing the key in return values, logs, errors, test fixtures, screenshots, or committed files;
- building `session.update` from `RealtimeSessionConfig`;
- mapping VoiceAgents tool definitions into DashScope-native tool declarations;
- mapping browser control `start` into a provider session setup message;
- mapping browser audio input into provider `input_audio_buffer.append` events;
- mapping browser control commit/end into provider commit/response events when required;
- normalizing DashScope transcript, tool-call, response, session, and error events into VoiceAgents contracts;
- building DashScope function-call output and response continuation events from `RealtimeToolCallResponse`.

### DashScope Outbound Transport

Implement a real DashScope outbound WebSocket transport behind the provider-neutral transport protocol.

Rules:

- automated tests must use fake transport only;
- no automated test may require network, real DashScope credentials, or a real model;
- dependency choice must be a separate pre-implementation decision before real transport code is written;
- if a new dependency is required for outbound WebSocket, it must be isolated behind the transport interface and documented in README or the manual checklist;
- transport errors must become safe session/proxy errors and must not include Authorization headers, API keys, raw audio, raw provider payloads, or raw tool arguments.

### Proxy Coordinator

Replace the current inline DashScope fake relay in `voiceagents/api/app.py` with a provider-neutral coordinator or a thin DashScope wrapper around it.

The coordinator must:

- authenticate the browser WebSocket with session-bound `tool_call_token`;
- reject missing token, wrong session, wrong provider, and expired token;
- accept only browser-safe proxy envelopes;
- reject secret-bearing keys recursively;
- connect to the provider only after browser auth succeeds;
- close provider and browser sides deterministically;
- relay safe normalized provider events to the browser;
- own DashScope loggable provider event ingestion on the server side so DashScope events are not also persisted by browser relay;
- send only loggable normalized DashScope events to existing event ingestion/repositories, with raw audio classified as transport-only and never persisted;
- route provider tool calls through existing `RealtimeToolRouter`;
- send provider-specific tool results back through the adapter.

### Browser Developer Surface

`/realtime-test` remains a local developer test page, not a production provider selection UI.

Minimum changes:

- keep OpenAI WebRTC behavior working;
- add or route through a DashScope browser adapter module such as `voiceagents/api/static/realtime-dashscope-adapter.js`;
- do not render `tool_call_token`, `client_secret`, provider API keys, Authorization headers, raw audio, SDP, or raw tool arguments;
- render DashScope proxy events received from the server, but do not submit DashScope provider events to `/v1/realtime/event`; the server proxy owns DashScope event persistence;
- display provider, model, connection mode, safe proxy status, transcript, assistant response, tool calls, handoff, latency, and provider-safe errors;
- support a local smoke path for one voice response and one tool call.

### Manual Real Provider Checklist

Update `docs/specs/voiceagents-dashscope-realtime-manual-checklist.md` after implementation.

Checklist must cover:

- required env vars;
- dev gate;
- focused fake tests;
- starting local API server;
- browser `/realtime-test` flow;
- one real voice interaction;
- one real tool call and safe tool result;
- validation report capture;
- failure modes: missing key, bad token, wrong provider session, invalid proxy envelope, provider disconnect.

## Out Of Scope

- Volc implementation.
- GLM implementation.
- MiniMax, iFlytek, Tencent, Baidu, Azure, Gemini, or AWS implementation.
- production provider selection UI.
- provider fallback or load balancing.
- telephony.
- cascaded ASR -> LLM/tools -> TTS implementation.
- raw audio persistence.
- unredacted transcript persistence.
- storing or committing real API keys, tokens, raw audio, SDP, Authorization headers, or raw provider payload samples.

## Security Requirements

Never expose or persist:

- `VOICEAGENTS_DASHSCOPE_API_KEY`;
- `DASHSCOPE_API_KEY`;
- any provider API key;
- Authorization headers;
- `tool_call_token`;
- browser-safe ephemeral credentials after initial local response handling;
- SDP;
- raw audio bytes;
- raw tool arguments;
- raw provider error bodies;
- real customer PII.

Provider-specific raw payloads may be inspected in memory for routing, but only redacted normalized events or safe summaries may enter logs, reports, screenshots, or committed fixtures.

## Test Requirements

Automated tests must be fake-only and local.

Required focused suites:

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py tests/test_realtime_dashscope_adapter.py tests/test_api_realtime_dashscope_proxy.py -v
```

Required broader realtime suite:

```bash
./.venv/bin/python -m pytest tests/test_realtime_providers.py tests/test_realtime_dashscope_provider.py tests/test_realtime_diagnostics.py tests/test_api_realtime_client_secret.py tests/test_api_realtime_tool_call.py tests/test_api_realtime_event.py tests/test_api_realtime_dashscope_proxy.py tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py -v
```

Before branch completion:

```bash
./.venv/bin/python -m pytest
git diff --check
```

Manual real-provider testing is required for DashScope but must not be committed as raw artifacts.

## Acceptance Criteria

1. DashScope real outbound WebSocket transport can be enabled locally with server-only env vars.
2. `/v1/realtime/client-secret` remains gated by `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true` for real providers.
3. DashScope client-secret response returns local proxy metadata and never returns provider credentials.
4. Browser proxy token remains session-bound and provider-bound.
5. Fake transport tests cover browser-to-proxy, proxy-to-provider, provider-to-browser, provider tool call, provider tool result, and provider disconnect paths.
6. DashScope adapter maps session, transcript, assistant response, audio, tool-call, tool-result, response done, and safe error events.
7. `/realtime-test` can start a local DashScope proxy session and display safe provider/model/connection status.
8. Manual checklist proves one real DashScope voice run and one real tool-call run.
9. OpenAI realtime tests continue to pass.
10. No automated test calls DashScope or requires real credentials.
11. No new logs, docs, fixtures, screenshots, or reports contain API keys, Authorization headers, tokens, raw audio, SDP, raw tool arguments, or real PII.
12. Adding GLM or Volc later requires provider enum/capability/config/adapter/transport/tests, not changes to business tool adapters.
13. DashScope provider events are persisted exactly once by the server proxy path; the browser renders safe events but does not relay DashScope provider events to `/v1/realtime/event`.

## Files Expected To Change

Likely new files:

- `voiceagents/realtime/outbound.py`
- `voiceagents/realtime/proxy.py`
- `voiceagents/realtime/dashscope_transport.py`
- `voiceagents/api/static/realtime-dashscope-adapter.js`
- `tests/test_realtime_outbound_contracts.py`
- `tests/test_realtime_dashscope_transport.py`

Likely modified files:

- `voiceagents/realtime/contracts.py`
- `voiceagents/realtime/dashscope.py`
- `voiceagents/realtime/providers.py`
- `voiceagents/api/app.py`
- `voiceagents/api/static/realtime-test.html`
- `tests/test_realtime_dashscope_adapter.py`
- `tests/test_api_realtime_dashscope_proxy.py`
- `tests/test_api_realtime_test_page.py`
- `tests/test_realtime_test_page_failure_modes.py`
- `docs/specs/voiceagents-dashscope-realtime-manual-checklist.md`
- `README.md`
- `OPENAI_REALTIME_VOICE_MVP_HANDOFF.md`

## Follow-Up Provider Guidance

GLM should be planned as a follow-up `server_websocket_proxy` adapter after DashScope proves the framework. Volc should be planned as a follow-up platform/RTC adapter because its official realtime function-calling flow differs from DashScope's plain WebSocket shape.
