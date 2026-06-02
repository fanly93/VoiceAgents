import pytest

from voiceagents.realtime.contracts import (
    NormalizedRealtimeEventType,
    RealtimeProviderName,
    VoiceSessionState,
)
from voiceagents.realtime.dashscope import (
    DashScopeEventError,
    normalize_dashscope_event,
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
