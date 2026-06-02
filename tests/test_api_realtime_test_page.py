from pathlib import Path

from fastapi.testclient import TestClient

from voiceagents.api.app import create_app


STATIC_PAGE = Path("voiceagents/api/static/realtime-test.html")
ADAPTER_JS = Path("voiceagents/api/static/realtime-openai-adapter.js")
DASHSCOPE_ADAPTER_JS = Path("voiceagents/api/static/realtime-dashscope-adapter.js")
OPENAI_FIXTURE = Path("tests/fixtures/openai_realtime_events.json")
PHASE4_CHECKLIST = Path("docs/specs/openai-realtime-phase4-browser-checklist.md")


def test_realtime_test_page_static_shell_contains_required_controls_and_panels() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert 'id="start-session"' in html
    assert 'id="stop-session"' in html
    assert 'id="mute-toggle" type="button" aria-pressed="false"' in html
    assert 'id="response-mode"' in html
    assert 'id="session-state"' in html
    assert 'id="transcript"' in html
    assert 'id="assistant-response"' in html
    assert 'id="tool-calls"' in html
    assert 'id="handoff-state"' in html
    assert 'id="latency"' in html
    assert 'id="provider-events"' in html


def test_realtime_test_page_renders_validation_controls() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert 'id="validation-scenario"' in html
    assert 'id="start-validation-run"' in html
    assert 'id="finish-validation-run"' in html
    assert 'id="validation-heard-voice"' in html
    assert 'id="validation-voice-quality"' in html
    assert 'id="validation-business-answer"' in html
    assert 'id="validation-demo-ready"' in html
    assert 'id="validation-notes"' in html
    assert 'id="validation-run-id"' in html
    assert 'id="validation-result"' in html
    assert 'fetch("/v1/realtime/validation-scenarios"' in html
    assert 'fetch("/v1/realtime/validation-runs"' in html
    finish_block = html.split("async function finishValidationRun", 1)[1].split(
        "function parseProviderMessage",
        1,
    )[0]
    assert "clientSecret" not in finish_block
    assert "toolCallToken" not in finish_block
    assert "connectionUrl" not in finish_block
    assert "provider_raw_arguments" not in finish_block


def test_realtime_test_page_renders_dev_diagnostics_controls() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert 'id="run-diagnostics"' in html
    assert 'id="diagnostics-result"' in html
    assert 'fetch("/v1/realtime/dev-diagnostics"' in html
    assert "renderDiagnostics" in html
    diagnostics_block = html.split("async function runDiagnostics", 1)[1].split(
        "function parseToolNamesFromPanel",
        1,
    )[0]
    assert "clientSecret" not in diagnostics_block
    assert "toolCallToken" not in diagnostics_block
    assert "OPENAI_API_KEY" not in diagnostics_block


def test_realtime_test_page_route_serves_static_page() -> None:
    client = TestClient(create_app())

    response = client.get("/realtime-test")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="start-session"' in response.text


def test_realtime_openai_adapter_route_serves_static_js() -> None:
    client = TestClient(create_app())

    response = client.get("/static/realtime-openai-adapter.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "normalizeOpenAIRealtimeEvent" in response.text


def test_realtime_dashscope_adapter_route_serves_static_js() -> None:
    client = TestClient(create_app())

    response = client.get("/static/realtime-dashscope-adapter.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "connectDashScopeRealtime" in response.text


def test_dashscope_browser_adapter_exports_safe_proxy_helpers() -> None:
    adapter = DASHSCOPE_ADAPTER_JS.read_text(encoding="utf-8")

    assert "buildDashScopeProxyUrl" in adapter
    assert "connectDashScopeRealtime" in adapter
    assert "sendDashScopeControl" in adapter
    assert "sendDashScopeAudio" in adapter
    assert "sendDashScopeToolResult" in adapter
    assert "window.voiceAgentsDashScopeRealtimeAdapter" in adapter
    assert "DASHSCOPE_API_KEY" not in adapter
    assert "VOICEAGENTS_DASHSCOPE_API_KEY" not in adapter
    assert "Authorization" not in adapter
    assert "client_secret" not in adapter
    assert "raw_audio" not in adapter


def test_realtime_test_page_bootstrap_js_uses_client_secret_endpoint() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert 'fetch("/v1/realtime/client-secret"' in html
    assert "session_config" in html
    assert "OPENAI_API_KEY" not in html
    assert "writePanel(\"provider-events\", payload.client_secret" not in html
    assert "writePanel(\"provider-events\", payload.tool_call_token" not in html


def test_realtime_test_page_state_tracks_webrtc_resources_without_rendering_secrets() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert "peerConnection: null" in html
    assert "dataChannel: null" in html
    assert "localStream: null" in html
    assert "remoteAudio: null" in html
    assert "clientSecret: null" in html
    assert "connectionUrl: null" in html
    assert "isStarting: false" in html
    assert "activeConnectionId: 0" in html
    assert "payload.client_secret" in html
    assert "payload.tool_call_token" in html
    assert "writePanel(\"provider-events\", payload.client_secret" not in html
    assert "appendPanel(\"provider-events\", payload.client_secret" not in html
    assert "writePanel(\"provider-events\", payload.tool_call_token" not in html
    assert "appendPanel(\"provider-events\", payload.tool_call_token" not in html


def test_realtime_test_page_sets_up_microphone_and_remote_audio() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert "navigator.mediaDevices.getUserMedia({ audio: true })" in html
    assert "new RTCPeerConnection()" in html
    assert "state.localStream.getTracks().forEach((track) => {" in html
    assert "state.peerConnection.addTrack(track, state.localStream)" in html
    assert "state.remoteAudio = new Audio()" in html
    assert "state.remoteAudio.autoplay = true" in html
    assert "track.enabled = !state.isMuted" in html
    assert "track.stop()" in html


def test_realtime_test_page_creates_openai_webrtc_call_with_ephemeral_secret() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert "state.peerConnection.createOffer()" in html
    assert "state.peerConnection.setLocalDescription(offer)" in html
    assert "const peerConnection = state.peerConnection" in html
    assert "const connectionUrl = state.connectionUrl" in html
    assert "fetch(connectionUrl" in html
    assert "const clientSecret = state.clientSecret" in html
    assert "Authorization: `Bearer ${clientSecret}`" in html
    assert '"Content-Type": "application/sdp"' in html
    assert "body: offer.sdp" in html
    assert "peerConnection.setRemoteDescription" in html
    assert 'new RTCSessionDescription({ type: "answer", sdp: answerSdp })' in html


def test_realtime_test_page_wires_dashscope_proxy_mode_without_rendering_token() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert "async function connectDashScopeRealtime" in html
    assert 'payload.connection_mode === "server_websocket_proxy"' in html
    assert 'src="/static/realtime-dashscope-adapter.js"' in html
    assert "voiceAgentsDashScopeRealtimeAdapter" in html
    assert "adapter.connectDashScopeRealtime" in html
    assert "dashscope.proxy.ready" in html
    assert "connection_mode=${payload.connection_mode}" in html
    dashscope_block = html.split("async function connectDashScopeRealtime", 1)[1].split(
        "async function startSession",
        1,
    )[0]
    assert "clientSecret" not in dashscope_block
    assert "appendPanel(\"provider-events\", state.toolCallToken" not in dashscope_block


def test_openai_realtime_adapter_maps_fixture_events_to_normalized_events() -> None:
    adapter = ADAPTER_JS.read_text(encoding="utf-8")
    fixture = OPENAI_FIXTURE.read_text(encoding="utf-8")

    assert "normalizeOpenAIRealtimeEvent" in adapter
    assert "response.output_audio_transcript.delta" in adapter
    assert "response.output_audio_transcript.done" in adapter
    assert "conversation.item.input_audio_transcription.delta" in adapter
    assert "conversation.item.input_audio_transcription.completed" in adapter
    assert "conversation.item.input_audio_transcription.segment" in adapter
    assert "conversation.item.done" in adapter
    assert "response.function_call_arguments.done" in adapter
    assert "session.created" in adapter
    assert "response.output_text.delta" in adapter
    assert "response.output_text.done" in adapter
    assert "response.done" in adapter
    assert '"error"' in adapter
    error_block = adapter.split('if (event.type === "error")', 1)[1].split("return null", 1)[0]
    assert "safe_summary" not in error_block
    assert "transcript.assistant.delta" in adapter
    assert "transcript.assistant.done" in adapter
    assert "transcript.user.delta" in adapter
    assert "transcript.user.done" in adapter
    assert "session.connected" in adapter
    assert "tool_call.requested" in adapter
    assert "response.done" in fixture


def test_openai_realtime_adapter_skips_empty_transcript_text_events() -> None:
    adapter = ADAPTER_JS.read_text(encoding="utf-8")

    assert "function textOrNull(value)" in adapter
    assert "return text ? text : null" in adapter
    assert "const text = textOrNull(event.delta)" in adapter
    assert "if (text === null) {" in adapter
    assert "return null;" in adapter


def test_realtime_test_page_renders_normalized_transcript_and_assistant_text() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert "function renderNormalizedEvent(normalized)" in html
    assert 'normalized.event_type === "transcript.assistant.delta"' in html
    assert 'appendText("assistant-response", normalized.text)' in html
    assert 'normalized.event_type === "transcript.assistant.done"' in html
    assert 'finalizeTranscriptTurn("assistant", normalized)' in html
    assert 'normalized.event_type === "transcript.user.delta"' in html
    assert 'appendText("transcript", normalized.text)' in html
    assert 'normalized.event_type === "transcript.user.done"' in html
    assert 'finalizeTranscriptTurn("user", normalized)' in html


def test_realtime_test_page_loads_openai_adapter_and_relays_normalized_events() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert 'src="/static/realtime-openai-adapter.js"' in html
    assert "normalizeOpenAIRealtimeEvent" in html
    assert 'fetch("/v1/realtime/event"' in html
    assert "Authorization: `Bearer ${state.toolCallToken}`" in html
    assert "client_secret" not in html.split('fetch("/v1/realtime/event"', 1)[1]
    assert "raw_audio" not in html.split('fetch("/v1/realtime/event"', 1)[1]
    assert 'event_type: "tool_call.result"' in html
    assert "tool_status: toolResponse.tool_status" in html
    assert "safe_summary: toolResponse.safe_summary" in html
    assert "isAllowedRealtimeTool" in html
    assert "return;" in html.split("if (!isAllowedRealtimeTool", 1)[1]


def test_openai_realtime_adapter_sends_safe_tool_results_back_to_provider() -> None:
    adapter = ADAPTER_JS.read_text(encoding="utf-8")

    assert "sendOpenAIToolResult" in adapter
    assert "sendOpenAIResponseCreate" in adapter
    assert "conversation.item.create" in adapter
    assert "function_call_output" in adapter
    assert "response.create" in adapter
    assert "safe_summary" in adapter
    assert "tool_call_token" not in adapter
    assert "Authorization" not in adapter
    tool_result_body = adapter.split("function sendOpenAIToolResult", 1)[1].split(
        "function sendOpenAIResponseCreate",
        1,
    )[0]
    assert "response.create" not in tool_result_body


def test_realtime_test_page_queues_response_create_until_provider_response_done() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert "openAIResponseInProgress: false" in html
    assert "pendingOpenAIResponseCreate: false" in html
    assert "function trackOpenAIResponseState(event)" in html
    assert 'event.type === "response.done"' in html
    assert "function queueOpenAIResponseCreate()" in html
    assert "function flushOpenAIResponseCreate()" in html
    assert "state.openAIResponseInProgress" in html
    assert "state.pendingOpenAIResponseCreate = true" in html
    assert "adapter.sendOpenAIResponseCreate(state.dataChannel)" in html


def test_realtime_test_page_does_not_send_failed_tool_calls_to_provider() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert "if (!response.ok)" in html.split("async function relayToolCall", 1)[1]
    assert "throw new Error(`Tool call failed: ${response.status}`)" in html
    assert "if (!payload.ok)" in html.split("async function relayToolCall", 1)[1]
    assert "Tool call failed safely" in html


def test_realtime_test_page_handles_webrtc_error_and_cleanup_paths() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert "resetRealtimeResources()" in html
    assert "dataChannel.close()" in html
    assert "peerConnection.close()" in html
    assert "track.stop()" in html
    assert "remoteAudio.remove()" in html
    cleanup_block = html.split("function resetRealtimeResources()", 1)[1].split(
        "async function setupAudioAndPeerConnection",
        1,
    )[0]
    assert "state.clientSecret = null" in cleanup_block
    assert "state.toolCallToken = null" in cleanup_block
    assert "state.sessionConfig = null" in cleanup_block
    assert 'writePanel("session-state", "data_channel_closed")' in html
    assert 'writePanel("session-state", "data_channel_error")' in html
    assert "OpenAI SDP exchange failed" in html
    assert "catch (error)" in html
    assert "resetRealtimeResources();" in html.split("async function connectOpenAIRealtime", 1)[1]
    assert "startSession().catch" in html
    assert "setMuteState(!state.isMuted)" in html
    assert "mute_state=muted" in html
    assert "el(\"start-session\").disabled = disabled" in html
    assert "if (state.isStarting)" in html


def test_realtime_test_page_exposes_visible_mute_and_runtime_response_mode_updates() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert "function setMuteState(isMuted)" in html
    assert 'button.setAttribute("aria-pressed", state.isMuted ? "true" : "false")' in html
    assert "button.classList.toggle(\"is-muted\", state.isMuted)" in html
    assert 'el("response-mode").disabled = disabled' not in html
    assert "function updateRealtimeResponseMode()" in html
    assert 'type: "session.update"' in html
    assert 'output_modalities: [mode === "voice" ? "audio" : "text"]' in html
    assert 'response_mode_updated=${mode}' in html
    assert "function applyRealtimeResponseMode()" in html
    assert "applyRealtimeResponseMode();" in html.split('dataChannel.addEventListener("open"', 1)[1]
    assert 'el("response-mode").addEventListener("change", updateRealtimeResponseMode)' in html


def test_realtime_test_page_clears_session_panels_on_new_start() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert "function clearSessionPanels()" in html
    assert 'writePanel("transcript", "")' in html
    assert 'writePanel("assistant-response", "")' in html
    assert 'writePanel("tool-calls", "")' in html
    assert 'writePanel("handoff-state", "none")' in html
    assert 'writePanel("latency", "")' in html
    assert 'writePanel("provider-events", "")' in html
    assert "state.transcriptBuffers = { assistant: {}, user: {} }" in html
    assert "clearSessionPanels();" in html.split("async function startSession", 1)[1]


def test_realtime_test_page_uses_browser_locale_for_client_secret_request() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert 'locale: navigator.language || "en-US"' in html


def test_realtime_test_page_handles_invalid_provider_json_without_raw_error_noise() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert "function parseProviderMessage(data)" in html
    assert "provider_event_invalid_json" in html
    assert "function parseToolArguments(normalized)" in html
    assert "tool_arguments_invalid=" in html
    assert "if (args === null)" in html
    assert "provider_error=" in html


def test_phase4_browser_fake_media_checklist_is_recorded() -> None:
    checklist = PHASE4_CHECKLIST.read_text(encoding="utf-8")

    assert "microphone permission denial" in checklist
    assert "client-secret failure" in checklist
    assert "SDP exchange failure" in checklist
    assert "data channel close/error" in checklist
    assert "Stop cleanup" in checklist
    assert "Mute" in checklist
    assert "reconnect from a clean state" in checklist


def test_realtime_test_page_tool_relay_uses_header_token() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert 'fetch("/v1/realtime/tool-call"' in html
    assert "Authorization: `Bearer ${state.toolCallToken}`" in html
    assert "tool_name: toolName" in html
    assert 'id="tool-calls"' in html
    assert "window.voiceAgentsRealtimeTest" in html
