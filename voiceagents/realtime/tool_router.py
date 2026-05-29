from pydantic import BaseModel, ConfigDict, Field, ValidationError

from voiceagents.contracts.common import HandoffReason
from voiceagents.contracts.handoff import HandoffRequest
from voiceagents.contracts.knowledge import ProductKnowledgeRequest
from voiceagents.contracts.logistics import LookupLogisticsRequest
from voiceagents.contracts.order import LookupOrderRequest
from voiceagents.realtime.contracts import (
    ALLOWED_REALTIME_TOOL_NAMES,
    RealtimeToolCallRequest,
    RealtimeToolCallResponse,
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
    def __init__(
        self,
        *,
        session_store: InMemoryVoiceSessionStore,
        order_adapter: object | None = None,
        logistics_adapter: object | None = None,
        knowledge_adapter: object | None = None,
        handoff_adapter: object | None = None,
    ) -> None:
        self._session_store = session_store
        self._order_adapter = order_adapter
        self._logistics_adapter = logistics_adapter
        self._knowledge_adapter = knowledge_adapter
        self._handoff_adapter = handoff_adapter

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

    def execute(
        self,
        request: RealtimeToolCallRequest,
        *,
        tool_call_token: str,
    ) -> RealtimeToolCallResponse:
        self.validate_request(request, tool_call_token)
        arguments = self.validate_arguments(request)

        if isinstance(arguments, LookupOrderArguments):
            return self._lookup_order(request, arguments)
        if isinstance(arguments, LookupLogisticsArguments):
            return self._lookup_logistics(request, arguments)
        if isinstance(arguments, QueryProductKnowledgeArguments):
            return self._query_product_knowledge(request, arguments)
        if isinstance(arguments, HandoffToHumanArguments):
            return self._handoff_to_human(request, arguments)

        raise UnknownRealtimeToolError(f"Realtime tool is not routed yet: {request.tool_name}")

    def _lookup_order(
        self,
        request: RealtimeToolCallRequest,
        arguments: LookupOrderArguments,
    ) -> RealtimeToolCallResponse:
        if self._order_adapter is None:
            raise UnknownRealtimeToolError("Order adapter is not configured")

        response = self._order_adapter.lookup_order(
            LookupOrderRequest(merchant_id=request.merchant_id, order_id=arguments.order_id)
        )
        handoff_required = not response.ok
        return RealtimeToolCallResponse(
            ok=response.ok,
            tool_name=request.tool_name,
            result=response.safe_fields,
            safe_summary=response.user_summary,
            handoff_required=handoff_required,
            handoff_reason=HandoffReason.TOOL_ERROR if handoff_required else HandoffReason.NONE,
            error_code=response.error_code,
        )

    def _query_product_knowledge(
        self,
        request: RealtimeToolCallRequest,
        arguments: QueryProductKnowledgeArguments,
    ) -> RealtimeToolCallResponse:
        if self._knowledge_adapter is None:
            raise UnknownRealtimeToolError("Knowledge adapter is not configured")

        response = self._knowledge_adapter.query(
            ProductKnowledgeRequest(
                merchant_id=request.merchant_id,
                locale=arguments.locale or "en-US",
                query=arguments.query,
            )
        )
        handoff_required = response.handoff_recommended or not response.ok
        return RealtimeToolCallResponse(
            ok=response.ok,
            tool_name=request.tool_name,
            result={
                "short_answer": response.short_answer,
                "citations": response.citations,
                "confidence": response.confidence,
            },
            safe_summary=response.short_answer,
            handoff_required=handoff_required,
            handoff_reason=(
                HandoffReason.RAG_LOW_CONFIDENCE if handoff_required else HandoffReason.NONE
            ),
            error_code=response.error_code,
        )

    def _handoff_to_human(
        self,
        request: RealtimeToolCallRequest,
        arguments: HandoffToHumanArguments,
    ) -> RealtimeToolCallResponse:
        if self._handoff_adapter is None:
            raise UnknownRealtimeToolError("Handoff adapter is not configured")

        response = self._handoff_adapter.handoff(
            HandoffRequest(
                call_id=request.call_id,
                merchant_id=request.merchant_id,
                intent_primary="realtime_voice",
                order_id_candidate=None,
                summary=arguments.summary,
                tools_called=["handoff_to_human"],
                handoff_reason=arguments.reason,
                recommended_next_step="Human agent should review the realtime voice session.",
            )
        )
        if response.ok:
            self._session_store.mark_handoff(
                request.session_id,
                arguments.reason,
                response.handoff_id,
            )

        return RealtimeToolCallResponse(
            ok=response.ok,
            tool_name=request.tool_name,
            result={"handoff_id": response.handoff_id, "mode": response.mode.value},
            safe_summary=arguments.summary,
            handoff_required=True,
            handoff_reason=arguments.reason,
            error_code=None,
        )

    def _lookup_logistics(
        self,
        request: RealtimeToolCallRequest,
        arguments: LookupLogisticsArguments,
    ) -> RealtimeToolCallResponse:
        if self._logistics_adapter is None:
            raise UnknownRealtimeToolError("Logistics adapter is not configured")

        response = self._logistics_adapter.lookup_logistics(
            LookupLogisticsRequest(merchant_id=request.merchant_id, order_id=arguments.order_id)
        )
        handoff_required = not response.ok
        return RealtimeToolCallResponse(
            ok=response.ok,
            tool_name=request.tool_name,
            result={
                "status": response.status,
                "latest_event": response.latest_event,
                "estimated_delivery": response.estimated_delivery,
                "carrier": response.carrier,
            },
            safe_summary=response.user_summary,
            handoff_required=handoff_required,
            handoff_reason=HandoffReason.TOOL_ERROR if handoff_required else HandoffReason.NONE,
            error_code=response.error_code,
        )
