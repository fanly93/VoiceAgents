from enum import StrEnum
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
