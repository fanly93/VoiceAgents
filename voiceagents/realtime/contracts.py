from enum import StrEnum
import re

from pydantic import BaseModel, Field, field_validator


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


class RealtimeToolDefinition(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    parameters_schema: dict[str, object]


class RealtimeSessionConfig(BaseModel):
    instructions: str = Field(min_length=1)
    tools: list[RealtimeToolDefinition]


class RealtimeClientSecretRequest(BaseModel):
    session_id: str = Field(min_length=1)
    call_id: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    response_mode: ResponseMode
    locale: str = Field(min_length=1)
    safety_subject_id: str | None = None

    @field_validator("safety_subject_id")
    @classmethod
    def reject_raw_subject_identifiers(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if "@" in value or re.search(r"\+?\d[\d\s().-]{6,}\d", value):
            raise ValueError("safety_subject_id must not contain raw contact information")
        if " " in value.strip():
            raise ValueError("safety_subject_id must not contain a raw customer name")
        return value


class RealtimeClientSecretResponse(BaseModel):
    provider: RealtimeProviderName
    session_id: str = Field(min_length=1)
    call_id: str = Field(min_length=1)
    client_secret: str | None
    tool_call_token: str = Field(min_length=1)
    connection_url: str | None
    expires_at: str | None
    model: str = Field(min_length=1)
    voice: str | None
    session_config: RealtimeSessionConfig
