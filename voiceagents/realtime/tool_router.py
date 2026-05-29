from pydantic import BaseModel, ConfigDict, Field, ValidationError

from voiceagents.contracts.common import HandoffReason
from voiceagents.realtime.contracts import (
    ALLOWED_REALTIME_TOOL_NAMES,
    RealtimeToolCallRequest,
)
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore, VoiceSessionNotFound


class RealtimeToolRouterError(ValueError):
    status_code = 400


class UnknownRealtimeToolError(RealtimeToolRouterError):
    status_code = 400


class InvalidToolCallTokenError(RealtimeToolRouterError):
    status_code = 403


class InvalidToolArgumentsError(RealtimeToolRouterError):
    status_code = 422


class LookupOrderArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(min_length=1)


class LookupLogisticsArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(min_length=1)


class QueryProductKnowledgeArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    locale: str | None = None


class HandoffToHumanArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: HandoffReason
    summary: str = Field(min_length=1)


TOOL_ARGUMENT_SCHEMAS: dict[str, type[BaseModel]] = {
    "lookup_order": LookupOrderArguments,
    "lookup_logistics": LookupLogisticsArguments,
    "query_product_knowledge": QueryProductKnowledgeArguments,
    "handoff_to_human": HandoffToHumanArguments,
}


class RealtimeToolRouter:
    def __init__(self, *, session_store: InMemoryVoiceSessionStore) -> None:
        self._session_store = session_store

    def validate_request(self, request: RealtimeToolCallRequest, tool_call_token: str) -> None:
        if request.tool_name not in ALLOWED_REALTIME_TOOL_NAMES:
            raise UnknownRealtimeToolError(f"Unknown realtime tool: {request.tool_name}")

        try:
            token_is_valid = self._session_store.verify_tool_call_token(
                request.session_id,
                tool_call_token,
            )
        except VoiceSessionNotFound as error:
            raise InvalidToolCallTokenError("Invalid realtime tool-call session") from error

        if not token_is_valid:
            raise InvalidToolCallTokenError("Invalid realtime tool-call token")

    def validate_arguments(self, request: RealtimeToolCallRequest) -> BaseModel:
        schema = TOOL_ARGUMENT_SCHEMAS[request.tool_name]
        try:
            return schema.model_validate(request.arguments)
        except ValidationError as error:
            raise InvalidToolArgumentsError("Invalid realtime tool arguments") from error
