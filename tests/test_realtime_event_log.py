from voiceagents.realtime.contracts import (
    RealtimeProviderName,
    VoiceEvent,
    VoiceSessionState,
)
from voiceagents.realtime.event_log import InMemoryVoiceEventRepository


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
