from enum import StrEnum


class VoiceSessionState(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    SPEAKING = "speaking"
    HANDOFF_PENDING = "handoff_pending"
    ENDED = "ended"
    ERROR = "error"


class ResponseMode(StrEnum):
    TEXT = "text"
    VOICE = "voice"


class RealtimeProviderName(StrEnum):
    MOCK = "mock"
    OPENAI_REALTIME = "openai_realtime"
