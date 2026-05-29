import json

from voiceagents.realtime.contracts import (
    RealtimeProviderName,
    VoiceEvent,
    VoiceSessionState,
)
from voiceagents.realtime.event_log import InMemoryVoiceEventRepository, JsonlVoiceEventRepository


def make_voice_event() -> VoiceEvent:
    return VoiceEvent(
        event_id="event-123",
        timestamp="2026-05-29T09:00:00Z",
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        state=VoiceSessionState.IDLE,
        event_type="session_created",
        transcript_text_redacted=None,
        response_text_redacted=None,
        tool_name=None,
        tool_arguments_redacted=None,
        tool_result_summary=None,
        handoff_reason=None,
        latency_ms=None,
        provider=RealtimeProviderName.MOCK,
        provider_event_type=None,
        redaction_applied=False,
    )


def test_in_memory_voice_event_repository_appends_events() -> None:
    repository = InMemoryVoiceEventRepository()
    event = make_voice_event()

    repository.append(event)

    assert repository.events == [event]


def test_jsonl_voice_event_repository_appends_redacted_json_line(tmp_path) -> None:
    path = tmp_path / "events" / "realtime-events.jsonl"
    repository = JsonlVoiceEventRepository(path)
    event = make_voice_event().model_copy(
        update={
            "transcript_text_redacted": "Email customer@example.com about ORDER-123456.",
            "tool_arguments_redacted": {"phone": "+1 (555) 123-4567"},
        }
    )

    repository.append(event)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["transcript_text_redacted"] == "Email [EMAIL_REDACTED] about [ORDER_REDACTED]."
    assert payload["tool_arguments_redacted"] == {"phone": "[PHONE_REDACTED]"}
    assert payload["redaction_applied"] is True


def test_jsonl_voice_event_repository_omits_blocked_secret_keys(tmp_path) -> None:
    path = tmp_path / "realtime-events.jsonl"
    repository = JsonlVoiceEventRepository(path)
    event = make_voice_event().model_copy(
        update={
            "tool_arguments_redacted": {
                "client_secret": "secret-should-not-log",
                "tool_call_token": "token-should-not-log",
                "raw_audio": "audio-should-not-log",
                "order_id": "ORDER-123456",
            }
        }
    )

    repository.append(event)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["tool_arguments_redacted"] == {"order_id": "[ORDER_REDACTED]"}
    assert "secret-should-not-log" not in path.read_text(encoding="utf-8")
    assert "token-should-not-log" not in path.read_text(encoding="utf-8")
    assert "audio-should-not-log" not in path.read_text(encoding="utf-8")
