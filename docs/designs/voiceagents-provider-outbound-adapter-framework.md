# VoiceAgents Provider Outbound Adapter Framework Clarification

Status: SPEC CLARIFICATION / NO CODE STARTED
Date: 2026-06-02
Branch: `feat/dashscope-realtime-outbound`

## Question

VoiceAgents is about to test real non-OpenAI voice models. The immediate provider is DashScope, but the product requirement is broader: future providers such as DashScope, Volc/Doubao, GLM, MiniMax, iFlytek, Tencent, Baidu, Azure, Gemini, and AWS should be addable without rewriting the business voice-agent runtime.

The architecture question is:

- Can we make this easy to extend across providers?
- Or does each model provider require a separate integration?

## Short Answer

Both are true:

- The VoiceAgents business layer can and should be provider-neutral.
- Each provider still needs a provider-specific protocol adapter.

The correct next requirement is therefore not "implement DashScope only". It should be:

> Build a provider outbound adapter framework, then implement DashScope Qwen-Omni Realtime as the first real server WebSocket provider.

This gives DashScope real-model testing now while forcing the extension boundary that Volc, GLM, and later providers will reuse.

## Current Foundation

The merged provider-neutral foundation already gives the next phase a good base:

- `RealtimeProviderName` includes `mock`, `openai_realtime`, and `dashscope_realtime`.
- `RealtimeConnectionMode` already distinguishes `browser_webrtc_ephemeral`, `server_websocket_proxy`, `server_sdk_proxy`, and `cascaded_pipeline`.
- Provider capability metadata captures response modes, connection modes, native tool-call support, server credential requirements, defaults, and diagnostics checks.
- `/v1/realtime/tool-call` is session-provider-bound instead of reading a mutable runtime env provider.
- DashScope has provider config, metadata, event/tool adapters, fake-tested proxy validation, and a browser-safe proxy route:
  `WS /v1/realtime/dashscope/proxy/{session_id}`.
- Real DashScope outbound WebSocket transport is intentionally not implemented yet.

This means the next phase should not reopen order/logistics/knowledge/handoff tool logic. It should add the missing outbound transport and adapter lifecycle layer.

## Official Protocol Evidence

The provider abstraction cannot be a single generic WebSocket pass-through because official provider docs expose different connection and tool-call semantics.

### DashScope / Alibaba Model Studio

DashScope Qwen-Omni-Realtime supports native realtime voice/video via WebSocket and WebRTC. The documented native WebSocket endpoint uses a `model` query parameter and `Authorization: Bearer DASHSCOPE_API_KEY`, which means server-side credentials are required for a browser-safe implementation.

DashScope WebRTC exists, but official docs state it is whitelist-gated. For v1, DashScope should stay in `server_websocket_proxy`.

DashScope Qwen-Omni-Realtime function calling is provider-native: the provider emits `response.function_call_arguments.done`; the client sends a `conversation.item.create` item of type `function_call_output`, then sends `response.create` to let the provider produce the final voice/text response. DashScope Realtime also documents that `tool_choice` and `parallel_tool_calls` are not supported for this series.

Sources:

- https://help.aliyun.com/zh/model-studio/realtime
- https://help.aliyun.com/zh/model-studio/qwen-function-calling

### Volc / Doubao

Volc's realtime audio/video function calling path is not shaped like DashScope's plain WebSocket API. Official docs describe a realtime audio/video stack around `StartVoiceChat`, model/RTC task state, callbacks/messages such as `function_calling` and `tool_calls`, and result delivery through platform-specific update or RTC message mechanisms.

Volc can still fit the same VoiceAgents provider-neutral business boundary, but it should not be implemented by copying the DashScope WebSocket transport. It likely needs its own `server_sdk_proxy` or RTC/platform adapter after a focused protocol spike.

Source:

- https://www.volcengine.com/docs/6348/1554654

### GLM / Zhipu

GLM-Realtime is a native realtime audio/video model built on WebSocket. Official docs list the request address as `wss://open.bigmodel.cn/api/paas/v4/realtime`, require `Authorization` with JWT or API key, and document realtime audio/video, multimodal interaction, VAD modes, and Function Call support.

The async API reference explicitly notes that browser security prevents adding WebSocket auth headers directly in the browser demo path. This strongly supports the same server-side proxy principle used for DashScope.

Sources:

- https://docs.bigmodel.cn/cn/guide/models/sound-and-video/glm-realtime
- https://docs.bigmodel.cn/cn/asyncapi/realtime

## Decision

Use a two-layer provider model.

1. Provider-neutral VoiceAgents layer

   This layer owns:

   - session identity and token binding;
   - allowed business tools;
   - tool argument validation and safe tool execution;
   - transcript/event ingestion;
   - redaction;
   - validation reports;
   - manual real-provider checklists;
   - "no provider gets direct access to business adapters" security boundary.

2. Provider-specific adapter layer

   This layer owns:

   - provider auth and handshake;
   - transport lifecycle;
   - session/update event construction;
   - audio/control envelope mapping;
   - provider event normalization;
   - provider-native tool-call request parsing;
   - provider-specific tool-result event construction;
   - connection cleanup and provider error normalization.

Each new provider should require a new adapter module and tests, but should not require changes to order, logistics, knowledge, handoff, transcript persistence, or validation/reporting logic.

## Proposed Interfaces For Next Spec

The next spec should introduce contracts shaped like these. Names can change during implementation, but the responsibilities should stay separate.

### `RealtimeOutboundTransport`

Purpose: async provider connection lifecycle and raw send/receive boundary.

Responsibilities:

- connect with server-side credentials;
- send provider-safe JSON or binary/audio frames;
- receive provider events or audio frames;
- close on browser disconnect, provider disconnect, or validation failure;
- expose only safe errors to the browser and logs.

### `NativeRealtimeProviderAdapter`

Purpose: provider protocol mapping.

Responsibilities:

- build provider WebSocket URL and headers;
- build initial `session.update` or equivalent provider session message;
- map VoiceAgents session config/tools into provider-native tool declarations;
- normalize provider transcript/tool/error/done events into VoiceAgents contracts;
- build provider-native tool result messages from `RealtimeToolCallResponse`;
- classify transport-only events such as audio chunks and interrupts so raw audio is not persisted.

### `RealtimeProxyCoordinator`

Purpose: bind browser proxy, provider transport, adapter, and `RealtimeToolRouter`.

Responsibilities:

- authenticate browser WebSocket with session-bound `tool_call_token`;
- reject mismatched provider/session/token requests;
- relay browser audio/control events to provider through the adapter;
- route provider tool requests through `/v1/realtime/tool-call` or the same backend tool router;
- return provider-safe events/audio to the browser;
- close both sides deterministically.

## First Implementation Scope

Recommended first implementation:

1. Add provider-neutral outbound contracts and fake transport tests.
2. Refactor the current DashScope fake proxy boundary to use the provider-neutral coordinator.
3. Implement DashScope Qwen-Omni Realtime outbound WebSocket transport.
4. Add DashScope provider-native session/tool/result mapping based on official docs.
5. Extend `/realtime-test` only enough to perform local DashScope real-model smoke testing.
6. Update the DashScope manual checklist to cover real provider connection, one transcript, one tool call, one tool result, and failure-mode checks.

This should stay DashScope-first, not DashScope-only.

## Explicit Non-Goals

- Do not implement Volc, GLM, MiniMax, iFlytek, Tencent, Baidu, Azure, Gemini, or AWS in the same first code phase.
- Do not build production provider selection UI.
- Do not build multi-provider fallback or load balancing.
- Do not add telephony.
- Do not persist raw audio, SDP, Authorization headers, API keys, tool-call tokens, or unredacted transcripts.
- Do not let a provider call VoiceAgents business tools directly.
- Do not treat provider SDK examples as final protocol truth unless the official API docs and fakeable tests agree.

## Acceptance Shape

The next executable spec should require:

- DashScope real outbound WebSocket can be enabled locally with server-only API key env vars.
- Automated tests use fake transports only and never call real providers.
- `/v1/realtime/client-secret` remains dev-gated for real providers.
- Browser receives only local proxy metadata and session-bound tokens, never provider API keys.
- Provider-specific raw events are normalized before event/transcript persistence.
- Raw audio can pass through memory for realtime transport but is never written to logs, reports, screenshots, or committed artifacts.
- Tool calls remain allowlisted and executed by VoiceAgents.
- Adding a future provider requires provider enum/capability/config/adapter/tests, not business tool rewrites.

## Open Questions Before Full Spec

1. Should the next spec include only native realtime providers, or also define the cascaded ASR -> LLM/tools -> TTS interface now?

   Recommendation: define the cascaded shape at a high level, but implement only native realtime outbound in this phase.

2. Should GLM be a second implementation target in this branch?

   Recommendation: no. Treat GLM as a follow-up provider spike. Its official docs support the server-proxy principle, but first proving DashScope on the shared framework gives a safer template.

3. Should Volc be considered equivalent to DashScope for v1?

   Recommendation: no. Volc appears to use a different platform/RTC task model, so it should be planned as a separate adapter after a protocol spike.

4. Should `/realtime-test` become a provider-selection UI?

   Recommendation: no. Keep this branch focused on local developer testing. Provider selection can remain env/config based until real-provider smoke tests are stable.

## Recommended Next GStack Step

Generate the executable spec and tasks for:

`voiceagents-provider-outbound-adapter-framework-and-dashscope-realtime-v1`

Then run `$gstack-autoplan` against that spec before code changes. The autoplan review should especially challenge:

- secret handling;
- provider proxy lifecycle;
- fake transport testability;
- raw audio non-persistence;
- DashScope tool-call result mapping;
- future-provider extension boundary for GLM and Volc.
