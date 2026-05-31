from enum import StrEnum
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from voiceagents.contracts.common import HandoffReason, ToolErrorCode


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


class NormalizedRealtimeEventType(StrEnum):
    SESSION_CONNECTING = "session.connecting"
    SESSION_CONNECTED = "session.connected"
    SESSION_ENDED = "session.ended"
    SESSION_ERROR = "session.error"
    TRANSCRIPT_USER_DELTA = "transcript.user.delta"
    TRANSCRIPT_USER_DONE = "transcript.user.done"
    TRANSCRIPT_ASSISTANT_DELTA = "transcript.assistant.delta"
    TRANSCRIPT_ASSISTANT_DONE = "transcript.assistant.done"
    TOOL_CALL_REQUESTED = "tool_call.requested"
    TOOL_CALL_RESULT = "tool_call.result"
    HANDOFF_REQUESTED = "handoff.requested"
    RESPONSE_DONE = "response.done"


class RealtimeTranscriptEventType(StrEnum):
    TRANSCRIPT_DELTA = "transcript_delta"
    TRANSCRIPT_DONE = "transcript_done"


class TranscriptLoggingMode(StrEnum):
    OFF = "off"
    STRUCTURED = "structured"
    TRANSCRIPT = "transcript"


DEFAULT_TRANSCRIPT_LOGGING_MODE = TranscriptLoggingMode.STRUCTURED


ALLOWED_REALTIME_TOOL_NAMES = frozenset(
    {
        "lookup_order",
        "lookup_logistics",
        "query_product_knowledge",
        "handoff_to_human",
    }
)

DEFAULT_REALTIME_INSTRUCTIONS = (
    "You are a VoiceAgents support assistant for ecommerce merchants. "
    "Use only the provided tools for order, logistics, product knowledge, and handoff workflows. "
    "Ask one clarification question when speech, order ID, or intent is unclear. "
    "If clarification fails, call handoff_to_human with low_asr_confidence or order_id_unconfirmed. "
    "Do not approve refunds, returns, or compensation unless a backend tool result or handoff policy says so."
)


class RealtimeToolDefinition(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    parameters_schema: dict[str, object]


class RealtimeSessionConfig(BaseModel):
    instructions: str = Field(min_length=1)
    tools: list[RealtimeToolDefinition]


class RealtimeClientSecretRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    model_config = ConfigDict(extra="forbid")

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


class RealtimeEventIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    call_id: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    provider: RealtimeProviderName
    event_type: NormalizedRealtimeEventType
    state: VoiceSessionState
    speaker: Literal["user", "assistant"] | None = None
    turn_id: str | None = Field(default=None, min_length=1)
    sequence: int | None = Field(default=None, ge=0)
    text: str | None = Field(default=None, min_length=1)
    latency_ms: int | None = Field(default=None, ge=0)
    provider_event_type: str | None = Field(default=None, min_length=1)
    tool_name: str | None = Field(default=None, min_length=1)
    provider_call_id: str | None = Field(default=None, min_length=1)
    tool_status: str | None = Field(default=None, min_length=1)
    safe_summary: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_event_specific_fields(self) -> "RealtimeEventIngestRequest":
        transcript_events = {
            NormalizedRealtimeEventType.TRANSCRIPT_USER_DELTA,
            NormalizedRealtimeEventType.TRANSCRIPT_USER_DONE,
            NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DELTA,
            NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DONE,
        }
        tool_events = {
            NormalizedRealtimeEventType.TOOL_CALL_REQUESTED,
            NormalizedRealtimeEventType.TOOL_CALL_RESULT,
        }
        tool_fields = {
            "tool_name": self.tool_name,
            "provider_call_id": self.provider_call_id,
            "tool_status": self.tool_status,
            "safe_summary": self.safe_summary,
        }
        transcript_fields = {
            "speaker": self.speaker,
            "turn_id": self.turn_id,
            "sequence": self.sequence,
            "text": self.text,
        }

        if self.event_type in transcript_events:
            if self.speaker is None:
                raise ValueError("speaker is required for transcript events")
            if self.text is None:
                raise ValueError("text is required for transcript events")
            if (
                self.event_type
                in {
                    NormalizedRealtimeEventType.TRANSCRIPT_USER_DELTA,
                    NormalizedRealtimeEventType.TRANSCRIPT_USER_DONE,
                }
                and self.speaker != "user"
            ):
                raise ValueError("speaker must be user for user transcript events")
            if (
                self.event_type
                in {
                    NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DELTA,
                    NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DONE,
                }
                and self.speaker != "assistant"
            ):
                raise ValueError("speaker must be assistant for assistant transcript events")
            mixed_tool_fields = [name for name, value in tool_fields.items() if value is not None]
            if mixed_tool_fields:
                raise ValueError(
                    f"{', '.join(mixed_tool_fields)} are not allowed for transcript events"
                )
        elif any(value is not None for value in transcript_fields.values()):
            mixed_transcript_fields = [
                name for name, value in transcript_fields.items() if value is not None
            ]
            raise ValueError(
                f"{', '.join(mixed_transcript_fields)} are only allowed for transcript events"
            )

        if self.event_type in tool_events:
            missing_tool_fields = [name for name, value in tool_fields.items() if value is None]
            if missing_tool_fields:
                raise ValueError(f"{', '.join(missing_tool_fields)} are required for tool events")
        elif any(value is not None for value in tool_fields.values()):
            mixed_tool_fields = [name for name, value in tool_fields.items() if value is not None]
            raise ValueError(f"{', '.join(mixed_tool_fields)} are only allowed for tool events")

        return self


class RealtimeEventIngestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    event_id: str = Field(min_length=1)
    redaction_applied: bool


class RealtimeTranscriptEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    timestamp: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    call_id: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    speaker: Literal["user", "assistant"]
    event_type: RealtimeTranscriptEventType
    turn_id: str | None = Field(default=None, min_length=1)
    sequence: int | None = Field(default=None, ge=0)
    text_redacted: str = Field(min_length=1)
    provider: RealtimeProviderName
    provider_event_type: str | None = Field(default=None, min_length=1)
    redaction_applied: bool


class RealtimeToolCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    call_id: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    arguments: dict[str, object]


class RealtimeToolCallResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    tool_name: str
    result: dict[str, object]
    safe_summary: str
    handoff_required: bool
    handoff_reason: HandoffReason
    error_code: ToolErrorCode | None


class VoiceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    timestamp: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    call_id: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    state: VoiceSessionState
    event_type: str = Field(min_length=1)
    transcript_text_redacted: str | None
    response_text_redacted: str | None
    tool_name: str | None
    tool_arguments_redacted: dict[str, object] | None
    tool_result_summary: str | None
    handoff_reason: HandoffReason | None
    latency_ms: int | None = Field(default=None, ge=0)
    provider: RealtimeProviderName
    provider_event_type: str | None
    provider_call_id: str | None = Field(default=None, min_length=1)
    tool_status: str | None = Field(default=None, min_length=1)
    redaction_applied: bool


def build_default_realtime_session_config() -> RealtimeSessionConfig:
    return RealtimeSessionConfig(
        instructions=DEFAULT_REALTIME_INSTRUCTIONS,
        tools=[
            RealtimeToolDefinition(
                name="lookup_order",
                description="Look up safe order status fields for a confirmed order ID.",
                parameters_schema={
                    "type": "object",
                    "properties": {"order_id": {"type": "string", "minLength": 1}},
                    "required": ["order_id"],
                    "additionalProperties": False,
                },
            ),
            RealtimeToolDefinition(
                name="lookup_logistics",
                description="Look up safe logistics status fields for a confirmed order ID.",
                parameters_schema={
                    "type": "object",
                    "properties": {"order_id": {"type": "string", "minLength": 1}},
                    "required": ["order_id"],
                    "additionalProperties": False,
                },
            ),
            RealtimeToolDefinition(
                name="query_product_knowledge",
                description="Answer product usage questions using approved product knowledge.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "minLength": 1},
                        "locale": {"type": ["string", "null"]},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            ),
            RealtimeToolDefinition(
                name="handoff_to_human",
                description="Create a safe handoff request when the flow cannot be resolved automatically.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "enum": [reason.value for reason in HandoffReason],
                        },
                        "summary": {"type": "string", "minLength": 1},
                    },
                    "required": ["reason", "summary"],
                    "additionalProperties": False,
                },
            ),
        ],
    )
