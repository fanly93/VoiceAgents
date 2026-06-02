import json
import pytest

from voiceagents.contracts.common import HandoffReason, ToolErrorCode
from voiceagents.realtime.contracts import (
    NormalizedRealtimeEventType,
    RealtimeProviderName,
    RealtimeToolCallResponse,
    RealtimeToolStatus,
    VoiceSessionState,
)
from voiceagents.realtime.dashscope import (
    DashScopeEventError,
    build_dashscope_tool_result_event,
    normalize_dashscope_event,
    normalize_dashscope_tool_call,
)


def normalize(payload: dict[str, object]):
    return normalize_dashscope_event(
        payload,
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
    )


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
