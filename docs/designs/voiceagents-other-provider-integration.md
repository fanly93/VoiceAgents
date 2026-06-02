# VoiceAgents Other Provider Integration Design

Status: OFFICE-HOURS DESIGN / NO CODE STARTED
Date: 2026-06-02
Branch: `feat/other-provider-integration-planning`

## Goal

Design a provider-neutral voice model integration layer so VoiceAgents can add DashScope first, then Volc/Doubao, MiniMax, iFlytek, Tencent Cloud, Baidu Cloud, Azure, Gemini, AWS, and other voice providers without rewriting business tools or validation/reporting code.

The first concrete provider target is DashScope/Alibaba Model Studio voice models.

## Current Architecture Assessment

The project is not completely locked to OpenAI:

- `voiceagents/realtime/providers.py` already has a `RealtimeProvider` protocol.
- `voiceagents/realtime/contracts.py` already has provider metadata, normalized realtime event types, session config, tool definitions, and provider-bound session/token verification.
- `/v1/realtime/event`, event logs, transcript logs, validation reports, and tool routing are mostly provider-neutral.

However, the current implementation is still OpenAI-centric:

- `RealtimeProviderName` only supports `mock` and `openai_realtime`.
- `RealtimeClientSecretResponse` assumes an OpenAI-like client secret flow.
- `/realtime-test` loads `realtime-openai-adapter.js` and only connects when `provider === "openai_realtime"`.
- The browser adapter is OpenAI WebRTC/data-channel specific.
- `/v1/realtime/tool-call` currently derives provider from `VOICEAGENTS_REALTIME_PROVIDER` instead of the session binding, which is unsafe once multiple providers or mixed sessions exist.
- Diagnostics currently check OpenAI-specific env only.

So the right next step is not to bolt DashScope into the OpenAI path. The next implementation should first harden a provider-neutral boundary, then add DashScope as the first real non-OpenAI provider.

## Provider Research

The user-provided DashScope model marketplace link is a logged-in Alibaba Cloud console SPA. It cannot be reliably scraped without the user's browser login state. The model list and capabilities should therefore be based on official Alibaba Cloud help documentation, with the screenshot used as a supporting clue only.

DashScope official documentation shows these relevant voice model families:

| Use case | Candidate models | Fit for VoiceAgents |
|---|---|---|
| Native realtime speech-to-speech | `qwen3.5-omni-flash-realtime`, `qwen3.5-omni-plus-realtime` | Best first DashScope target. It can handle realtime audio input/output and tool calling through a single realtime session. |
| Realtime ASR | `qwen3-asr-flash-realtime`, `fun-asr-realtime`, `fun-asr-flash-8k-realtime` | Good for a cascaded pipeline when we want VoiceAgents to own LLM/tool orchestration separately. |
| Realtime TTS | `qwen3-tts-flash-realtime`, `qwen3-tts-instruct-flash-realtime` | Good paired with ASR or existing text LLM. |
| TTS quality/voice design | `cosyvoice-v3-flash`, `cosyvoice-v3-plus`, `cosyvoice-v3.5-*` | Useful later; `v3.5` is less suitable for v1 because it requires voice clone/design voices and does not support system voices. |
| Non-realtime fallback | `qwen3-asr-flash`, `qwen3-asr-flash-filetrans`, `qwen3.5-omni-flash` | Useful for offline testing or fallback, not the first realtime voice path. |

Other provider research:

| Priority | Provider | Best fit |
|---|---|---|
| P0 | Volc/Doubao realtime voice | Domestic native realtime voice alternative with Function Calling support in its realtime conversation stack. |
| P1 | MiniMax Speech | Strong TTS provider; not enough for full voice-agent loop by itself. |
| P1 | iFlytek | Strong Chinese ASR and TTS; should be modeled as ASR/TTS adapters. |
| P1 | Tencent Cloud | Enterprise ASR/TTS and TRTC integration; better as standard ASR/TTS or platform-specific realtime adapter. |
| P1/P2 | Baidu Cloud | ASR/TTS and emerging speech-language model options; validate openness before native realtime priority. |
| P0 global | Azure OpenAI Realtime | Global enterprise realtime provider, close to current OpenAI model but with Azure auth/deployment differences. |
| P0/P1 global | Gemini Live | Native realtime multimodal and function calling; useful for multi-modal future. |
| P0/P1 global | AWS Nova Sonic | Native speech-to-speech and tool use; likely higher implementation complexity because of AWS auth/streaming. |

Official references used during office-hours:

- Alibaba Cloud ASR model selection: https://help.aliyun.com/zh/model-studio/asr-model/
- Alibaba Cloud realtime TTS: https://help.aliyun.com/zh/model-studio/realtime-tts-user-guide
- Alibaba Cloud Qwen-Omni realtime: https://help.aliyun.com/zh/model-studio/realtime
- Volc Function Calling for realtime audio/video: https://www.volcengine.com/docs/6348/1554654
- MiniMax T2A WebSocket: https://platform.minimax.io/docs/api-reference/speech-t2a-websocket
- Azure OpenAI Realtime WebRTC: https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/realtime-audio-webrtc
- Google Gemini Live API: https://ai.google.dev/api/live
- AWS Nova Sonic: https://docs.aws.amazon.com/nova/latest/userguide/speech-bidirection.html

## Design Decision

Use two provider families:

1. `NativeRealtimeVoiceProvider`

   For providers that offer an end-to-end realtime model: speech in, model reasoning, tool-call request, speech out. Examples: OpenAI Realtime, DashScope Qwen-Omni Realtime, Volc/Doubao realtime, Azure OpenAI Realtime, Gemini Live, AWS Nova Sonic.

2. `CascadedVoiceProvider`

   For providers that expose separate speech capabilities: ASR -> VoiceAgents LLM/tool runtime -> TTS. Examples: DashScope Qwen-ASR + Qwen-TTS, MiniMax TTS, iFlytek ASR/TTS, Tencent Cloud ASR/TTS, Baidu ASR/TTS.

The first implementation should focus on `NativeRealtimeVoiceProvider` plus DashScope Qwen-Omni Realtime. Cascaded ASR/TTS should be designed now but implemented later unless DashScope Omni access is blocked.

## Connection Model

Do not expose provider API keys to the browser.

The provider abstraction should support these connection modes:

- `browser_webrtc_ephemeral`: browser connects to provider using a short-lived credential or SDP exchange; OpenAI currently uses this.
- `server_websocket_proxy`: browser connects to VoiceAgents; VoiceAgents connects to provider WebSocket with server-side credentials; DashScope should start here.
- `server_sdk_proxy`: VoiceAgents uses provider SDK/gRPC and relays normalized messages.
- `cascaded_pipeline`: VoiceAgents coordinates separate ASR, LLM/tool, and TTS adapters.

DashScope should not be browser-direct in v1 because WebSocket authentication requires a server-side `DASHSCOPE_API_KEY` and custom handshake headers. Qwen-Omni WebRTC may be useful later, but official access/whitelist and credential handling need validation first.

## Tool Boundary

All business tools stay in VoiceAgents:

- `lookup_order`
- `lookup_logistics`
- `query_product_knowledge`
- `handoff_to_human`

Provider-native tool/function-call events must be treated as tool requests only. The provider never receives direct access to order, logistics, knowledge, or handoff adapters. VoiceAgents executes the tool, redacts/summarizes the result, and sends a provider-specific tool result event back through the provider adapter.

This preserves the current security boundary and lets provider swaps remain low-risk.

## Event Boundary

Provider adapters should map raw provider events into two layers:

- loggable normalized events already used by `/v1/realtime/event`, validation reports, transcripts, and tool logs;
- transport-only events for audio chunks, interrupts, provider session updates, and connection lifecycle that should not be persisted as raw audio.

Existing loggable events remain useful:

- `session.connecting`
- `session.connected`
- `session.ended`
- `session.error`
- `transcript.user.delta`
- `transcript.user.done`
- `transcript.assistant.delta`
- `transcript.assistant.done`
- `tool_call.requested`
- `tool_call.result`
- `handoff.requested`
- `response.done`

DashScope may require additional transport events for audio deltas and interruption. Those should not cause raw audio to be written into event logs.

## Out Of Scope For First Implementation

- Provider selection UI for production users.
- Multi-provider fallback or load balancing.
- Cost comparison.
- Telephony provider integration.
- Frontend polishing beyond a developer/tester connection path.
- Saving raw audio.
- Saving unredacted transcripts.
- Giving providers direct access to business tools.

## Office-Hours Recommendation

Proceed with a specs-first task:

1. Define provider-neutral contracts and registry.
2. Fix multi-provider session/tool binding risks.
3. Add DashScope provider configuration and diagnostics.
4. Implement DashScope Qwen-Omni Realtime through a server WebSocket proxy.
5. Keep cascaded ASR/TTS as the fallback design, not the default first implementation.
