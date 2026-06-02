import json
import pytest

from voiceagents.contracts.common import HandoffReason, ToolErrorCode
from voiceagents.realtime.contracts import (
    NormalizedRealtimeEventType,
    RealtimeProviderName,
    RealtimeToolCallResponse,
    RealtimeToolStatus,
    ResponseMode,
    VoiceSessionState,
    build_default_realtime_session_config,
)
from voiceagents.realtime.dashscope import (
    DEFAULT_DASHSCOPE_REALTIME_MODEL,
    DashScopeRealtimeAdapter,
    DashScopeRealtimeConfig,
    DashScopeEventError,
    build_dashscope_tool_result_event,
    normalize_dashscope_event,
    normalize_dashscope_tool_call,
)
from voiceagents.realtime.outbound import RealtimeOutboundEvent, RealtimeOutboundEventKind


def normalize(payload: dict[str, object]):
    return normalize_dashscope_event(
        payload,
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
    )


def test_dashscope_adapter_builds_default_realtime_websocket_url() -> None:
    adapter = DashScopeRealtimeAdapter(
        DashScopeRealtimeConfig(
            api_key="dashscope-secret",
            model=DEFAULT_DASHSCOPE_REALTIME_MODEL,
            voice=None,
            base_url="https://dashscope.aliyuncs.com",
        )
    )

    assert (
        adapter.build_connection_url()
        == "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
        f"?model={DEFAULT_DASHSCOPE_REALTIME_MODEL}"
    )


def test_dashscope_adapter_uses_configured_base_url_and_model_query() -> None:
    adapter = DashScopeRealtimeAdapter(
        DashScopeRealtimeConfig(
            api_key="dashscope-secret",
            model="qwen-test-realtime",
            voice=None,
            base_url="https://dashscope-intl.aliyuncs.com/",
        )
    )

    assert (
        adapter.build_connection_url()
        == "wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime?model=qwen-test-realtime"
    )


def test_dashscope_adapter_builds_authorization_headers_without_safe_leakage() -> None:
    adapter = DashScopeRealtimeAdapter(
        DashScopeRealtimeConfig(
            api_key="dashscope-secret",
            model=DEFAULT_DASHSCOPE_REALTIME_MODEL,
            voice="Chelsie",
            base_url="https://dashscope.aliyuncs.com",
        )
    )

    assert adapter.build_headers() == {"Authorization": "Bearer dashscope-secret"}
    assert adapter.safe_connection_summary() == {
        "provider": "dashscope_realtime",
        "model": DEFAULT_DASHSCOPE_REALTIME_MODEL,
        "voice": "Chelsie",
        "connection_mode": "server_websocket_proxy",
        "base_url": "https://dashscope.aliyuncs.com",
        "api_key": "present",
    }
    assert "dashscope-secret" not in json.dumps(adapter.safe_connection_summary())


def test_dashscope_adapter_rejects_missing_api_key_for_headers() -> None:
    adapter = DashScopeRealtimeAdapter(
        DashScopeRealtimeConfig(
            api_key=None,
            model=DEFAULT_DASHSCOPE_REALTIME_MODEL,
            voice=None,
            base_url="https://dashscope.aliyuncs.com",
        )
    )

    with pytest.raises(DashScopeEventError, match="api key"):
        adapter.build_headers()


def test_dashscope_adapter_builds_session_update_for_voice_mode() -> None:
    adapter = DashScopeRealtimeAdapter(
        DashScopeRealtimeConfig(
            api_key="dashscope-secret",
            model=DEFAULT_DASHSCOPE_REALTIME_MODEL,
            voice="Chelsie",
            base_url="https://dashscope.aliyuncs.com",
        )
    )

    message = adapter.build_session_update_message(
        build_default_realtime_session_config(),
        response_mode=ResponseMode.VOICE,
    )

    session = message["session"]
    assert message["type"] == "session.update"
    assert session["modalities"] == ["audio", "text"]
    assert session["voice"] == "Chelsie"
    assert session["instructions"].startswith("You are a VoiceAgents support assistant")
    assert session["input_audio_format"] == "pcm16"
    assert session["output_audio_format"] == "pcm16"
    assert session["turn_detection"] == {"type": "server_vad"}
    assert "tool_choice" not in session
    assert "parallel_tool_calls" not in session


def test_dashscope_adapter_builds_session_update_for_text_mode() -> None:
    adapter = DashScopeRealtimeAdapter(
        DashScopeRealtimeConfig(
            api_key="dashscope-secret",
            model=DEFAULT_DASHSCOPE_REALTIME_MODEL,
            voice=None,
            base_url="https://dashscope.aliyuncs.com",
        )
    )

    message = adapter.build_session_update_message(
        build_default_realtime_session_config(),
        response_mode=ResponseMode.TEXT,
    )

    session = message["session"]
    assert session["modalities"] == ["text"]
    assert "voice" not in session
    assert session["output_audio_format"] is None


def test_dashscope_adapter_maps_allowed_tools_to_function_declarations() -> None:
    adapter = DashScopeRealtimeAdapter(
        DashScopeRealtimeConfig(
            api_key="dashscope-secret",
            model=DEFAULT_DASHSCOPE_REALTIME_MODEL,
            voice=None,
            base_url="https://dashscope.aliyuncs.com",
        )
    )

    message = adapter.build_session_update_message(
        build_default_realtime_session_config(),
        response_mode=ResponseMode.VOICE,
    )
    tools = message["session"]["tools"]

    assert [tool["name"] for tool in tools] == [
        "lookup_order",
        "lookup_logistics",
        "query_product_knowledge",
        "handoff_to_human",
    ]
    assert all(tool["type"] == "function" for tool in tools)
    assert tools[0]["description"] == "Look up safe order status fields for a confirmed order ID."
    assert tools[0]["parameters"]["properties"]["order_id"]["type"] == "string"


def test_dashscope_official_session_and_response_events_normalize() -> None:
    connected = normalize({"type": "session.created", "request_id": "provider-call-1"})
    done = normalize({"type": "response.done", "response": {"status": "completed"}})

    assert connected.event_type is NormalizedRealtimeEventType.SESSION_CONNECTED
    assert connected.provider_event_type == "session.created"
    assert connected.provider_call_id is None
    assert done.event_type is NormalizedRealtimeEventType.RESPONSE_DONE
    assert done.state is VoiceSessionState.LISTENING


def test_dashscope_official_transcript_events_normalize() -> None:
    user_done = normalize(
        {
            "type": "conversation.item.input_audio_transcription.completed",
            "transcript": "Where is order 123?",
        }
    )
    assistant_delta = normalize(
        {
            "type": "response.output_audio_transcript.delta",
            "delta": "I can check that.",
        }
    )
    assistant_done = normalize(
        {
            "type": "response.output_audio_transcript.done",
            "transcript": "Order is paid.",
        }
    )

    assert user_done.event_type is NormalizedRealtimeEventType.TRANSCRIPT_USER_DONE
    assert user_done.speaker == "user"
    assert user_done.text == "Where is order 123?"
    assert assistant_delta.event_type is NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DELTA
    assert assistant_delta.speaker == "assistant"
    assert assistant_delta.text == "I can check that."
    assert assistant_done.event_type is NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DONE
    assert assistant_done.speaker == "assistant"


def test_dashscope_official_audio_delta_is_transport_only() -> None:
    adapter = DashScopeRealtimeAdapter(
        DashScopeRealtimeConfig(
            api_key="dashscope-secret",
            model=DEFAULT_DASHSCOPE_REALTIME_MODEL,
            voice=None,
            base_url="https://dashscope.aliyuncs.com",
        )
    )

    event = adapter.normalize_provider_event(
        {"type": "response.audio.delta", "delta": "cGNtMTY="},
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
    )

    assert isinstance(event, RealtimeOutboundEvent)
    assert event.kind is RealtimeOutboundEventKind.AUDIO
    assert event.audio == b"pcm16"


def test_dashscope_official_function_call_event_normalizes_to_tool_request() -> None:
    request = normalize_dashscope_tool_call(
        {
            "type": "response.function_call_arguments.done",
            "call_id": "provider-tool-call-1",
            "name": "lookup_order",
            "arguments": json.dumps({"order_id": "ORD-20260601-1842"}),
        },
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
    )

    assert request.tool_name == "lookup_order"
    assert request.arguments == {"order_id": "ORD-20260601-1842"}


def test_dashscope_official_error_event_normalizes_without_raw_payload() -> None:
    event = normalize(
        {
            "type": "error",
            "error": {
                "message": "Authorization: Bearer dashscope-secret failed",
                "code": "Unauthorized",
            },
        }
    )

    assert event.event_type is NormalizedRealtimeEventType.SESSION_ERROR
    assert event.state is VoiceSessionState.ERROR
    assert event.provider_event_type == "error"
    assert "dashscope-secret" not in event.model_dump_json()


def test_dashscope_lifecycle_events_normalize_to_safe_events() -> None:
    connected = normalize({"type": "dashscope.session.started", "request_id": "provider-call-1"})
    ended = normalize({"type": "dashscope.session.finished", "request_id": "provider-call-1"})

    assert connected.event_type is NormalizedRealtimeEventType.SESSION_CONNECTED
    assert connected.state is VoiceSessionState.LISTENING
    assert connected.provider is RealtimeProviderName.DASHSCOPE_REALTIME
    assert connected.provider_event_type == "dashscope.session.started"
    assert connected.provider_call_id is None
    assert ended.event_type is NormalizedRealtimeEventType.SESSION_ENDED
    assert ended.state is VoiceSessionState.ENDED


def test_dashscope_error_event_normalizes_without_raw_provider_payload() -> None:
    event = normalize(
        {
            "type": "dashscope.session.error",
            "request_id": "provider-call-1",
            "error": {
                "message": "Authorization: Bearer dashscope-secret failed",
                "api_key": "dashscope-secret",
            },
        }
    )

    assert event.event_type is NormalizedRealtimeEventType.SESSION_ERROR
    assert event.state is VoiceSessionState.ERROR
    assert event.safe_summary is None
    assert "dashscope-secret" not in event.model_dump_json()


def test_dashscope_unknown_event_type_fails_closed() -> None:
    with pytest.raises(DashScopeEventError, match="Unsupported DashScope event"):
        normalize({"type": "dashscope.unknown"})


def test_dashscope_transcript_events_normalize_to_transcript_payloads() -> None:
    user_delta = normalize(
        {
            "type": "dashscope.transcript.user.delta",
            "text": "Where",
            "raw_audio": "base64-raw-audio",
        }
    )
    user_done = normalize({"type": "dashscope.transcript.user.done", "text": "Where is order 123?"})
    assistant_delta = normalize(
        {"type": "dashscope.transcript.assistant.delta", "text": "I can check that."}
    )
    assistant_done = normalize(
        {"type": "dashscope.transcript.assistant.done", "text": "Order is paid."}
    )

    assert user_delta.event_type is NormalizedRealtimeEventType.TRANSCRIPT_USER_DELTA
    assert user_delta.state is VoiceSessionState.TRANSCRIBING
    assert user_delta.speaker == "user"
    assert user_delta.text == "Where"
    assert user_done.event_type is NormalizedRealtimeEventType.TRANSCRIPT_USER_DONE
    assert user_done.speaker == "user"
    assert assistant_delta.event_type is NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DELTA
    assert assistant_delta.speaker == "assistant"
    assert assistant_done.event_type is NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DONE
    assert assistant_done.speaker == "assistant"
    assert "base64-raw-audio" not in user_delta.model_dump_json()


def test_dashscope_tool_call_event_normalizes_to_tool_request() -> None:
    request = normalize_dashscope_tool_call(
        {
            "type": "dashscope.tool_call.requested",
            "tool_name": "lookup_order",
            "arguments": {"order_id": "ORD-20260601-1842"},
        },
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
    )

    assert request.session_id == "session-123"
    assert request.call_id == "call-123"
    assert request.merchant_id == "merchant-123"
    assert request.tool_name == "lookup_order"
    assert request.arguments == {"order_id": "ORD-20260601-1842"}


def test_dashscope_tool_call_event_rejects_unknown_tool() -> None:
    with pytest.raises(DashScopeEventError, match="Unsupported DashScope tool"):
        normalize_dashscope_tool_call(
            {
                "type": "dashscope.tool_call.requested",
                "tool_name": "run_shell",
                "arguments": {},
            },
            session_id="session-123",
            call_id="call-123",
            merchant_id="merchant-123",
        )


def test_dashscope_tool_result_event_uses_safe_error_semantics() -> None:
    provider_event = build_dashscope_tool_result_event(
        RealtimeToolCallResponse(
            ok=False,
            tool_name="lookup_order",
            result={},
            safe_summary="I could not find that order.",
            handoff_required=True,
            handoff_reason=HandoffReason.TOOL_ERROR,
            error_code=ToolErrorCode.NOT_FOUND,
            tool_status=RealtimeToolStatus.FAILED,
            error_message="I could not find that order.",
        ),
        provider_call_id="provider-tool-call-1",
    )

    assert provider_event == {
        "type": "dashscope.tool_result",
        "tool_call_id": "provider-tool-call-1",
        "tool_name": "lookup_order",
        "tool_status": "failed",
        "output": {
            "ok": False,
            "safe_summary": "I could not find that order.",
            "error_message": "I could not find that order.",
            "error_code": "not_found",
            "handoff_required": True,
        },
    }
    assert "ORD-404" not in json.dumps(provider_event)
    assert "arguments" not in provider_event
