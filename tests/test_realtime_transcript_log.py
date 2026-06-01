import json

from voiceagents.realtime.contracts import (
    RealtimeProviderName,
    RealtimeTranscriptEvent,
    RealtimeTranscriptEventType,
)
from voiceagents.realtime.event_log import (
    DEFAULT_TRANSCRIPT_LOG_PATH,
    InMemoryRealtimeTranscriptRepository,
    JsonlRealtimeTranscriptRepository,
)


def make_transcript_event() -> RealtimeTranscriptEvent:
    return RealtimeTranscriptEvent(
        event_id="event-123",
        timestamp="2026-05-29T09:00:00Z",
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        speaker="user",
        event_type=RealtimeTranscriptEventType.TRANSCRIPT_DONE,
        turn_id="turn-123",
        sequence=2,
        text_redacted="Email customer@example.com about ORDER-123456.",
        provider=RealtimeProviderName.MOCK,
        provider_event_type="conversation.item.input_audio_transcription.completed",
        redaction_applied=False,
    )


def test_default_transcript_log_path_targets_voiceagents_transcripts() -> None:
    assert DEFAULT_TRANSCRIPT_LOG_PATH.as_posix() == ".voiceagents/transcripts/realtime-transcripts.jsonl"


def test_in_memory_transcript_repository_appends_events() -> None:
    repository = InMemoryRealtimeTranscriptRepository()
    event = make_transcript_event()

    repository.append(event)

    assert repository.events == [event]


def test_jsonl_transcript_repository_appends_redacted_json_line(tmp_path) -> None:
    path = tmp_path / "transcripts" / "realtime-transcripts.jsonl"
    repository = JsonlRealtimeTranscriptRepository(path)

    repository.append(make_transcript_event())

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["text_redacted"] == "Email [EMAIL_REDACTED] about [ORDER_REDACTED]."
    assert payload["redaction_applied"] is True
    assert "customer@example.com" not in path.read_text(encoding="utf-8")
    assert "ORDER-123456" not in path.read_text(encoding="utf-8")
