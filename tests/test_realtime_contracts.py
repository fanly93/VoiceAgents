from voiceagents.realtime.contracts import (
    RealtimeProviderName,
    ResponseMode,
    VoiceSessionState,
)


def test_voice_session_states_match_spec() -> None:
    assert VoiceSessionState.IDLE == "idle"
    assert VoiceSessionState.LISTENING == "listening"
    assert VoiceSessionState.TRANSCRIBING == "transcribing"
    assert VoiceSessionState.THINKING == "thinking"
    assert VoiceSessionState.TOOL_CALLING == "tool_calling"
    assert VoiceSessionState.SPEAKING == "speaking"
    assert VoiceSessionState.HANDOFF_PENDING == "handoff_pending"
    assert VoiceSessionState.ENDED == "ended"
    assert VoiceSessionState.ERROR == "error"


def test_response_modes_match_spec() -> None:
    assert ResponseMode.TEXT == "text"
    assert ResponseMode.VOICE == "voice"


def test_realtime_provider_names_match_spec() -> None:
    assert RealtimeProviderName.MOCK == "mock"
    assert RealtimeProviderName.OPENAI_REALTIME == "openai_realtime"
