from voiceagents.agent.models import CallFlowInput, CallFlowOutput
from voiceagents.contracts.common import HandoffReason
from voiceagents.contracts.handoff import HandoffRequest
from voiceagents.contracts.knowledge import ProductKnowledgeRequest
from voiceagents.contracts.logistics import LookupLogisticsRequest
from voiceagents.contracts.order import LookupOrderRequest


LOW_ASR_CONFIDENCE_THRESHOLD = 0.6


class CallFlowService:
    def __init__(self, handoff_adapter, order_adapter=None, logistics_adapter=None, knowledge_adapter=None) -> None:
        self._handoff_adapter = handoff_adapter
        self._order_adapter = order_adapter
        self._logistics_adapter = logistics_adapter
        self._knowledge_adapter = knowledge_adapter

    def handle(self, call: CallFlowInput) -> CallFlowOutput:
        if call.asr_confidence < LOW_ASR_CONFIDENCE_THRESHOLD:
            return self._handoff(call, HandoffReason.LOW_ASR_CONFIDENCE, "ASR confidence is too low.")

        if call.customer_requested_human:
            return self._handoff(call, HandoffReason.CUSTOMER_REQUESTS_HUMAN, "Customer requested a human agent.")

        if call.intent == "complaint":
            return self._handoff(call, HandoffReason.COMPLAINT_OR_ANGRY_CUSTOMER, "Customer has a complaint.")

        if call.intent == "return_exchange_refund":
            return self._handoff(
                call,
                HandoffReason.REFUND_OR_RETURN_EXCEPTION,
                "Return, exchange, and refund requests require human review in the MVP.",
            )

        if call.intent == "order_status":
            if not call.order_id_confirmed or not call.order_id_candidate:
                return self._handoff(call, HandoffReason.ORDER_ID_UNCONFIRMED, "Order ID is not confirmed.")
            response = self._order_adapter.lookup_order(
                LookupOrderRequest(merchant_id=call.merchant_id, order_id=call.order_id_candidate)
            )
            if response.ok:
                return CallFlowOutput(
                    resolved=True,
                    response_text=response.user_summary,
                    tools_called=["lookup_order"],
                    handoff_required=False,
                    handoff_reason=HandoffReason.NONE,
                    handoff_id=None,
                )
            return self._handoff(call, HandoffReason.TOOL_ERROR, response.user_summary)

        if call.intent == "logistics_tracking":
            if not call.order_id_confirmed or not call.order_id_candidate:
                return self._handoff(call, HandoffReason.ORDER_ID_UNCONFIRMED, "Order ID is not confirmed.")
            response = self._logistics_adapter.lookup_logistics(
                LookupLogisticsRequest(merchant_id=call.merchant_id, order_id=call.order_id_candidate)
            )
            if response.ok:
                return CallFlowOutput(
                    resolved=True,
                    response_text=response.user_summary,
                    tools_called=["lookup_logistics"],
                    handoff_required=False,
                    handoff_reason=HandoffReason.NONE,
                    handoff_id=None,
                )
            return self._handoff(call, HandoffReason.TOOL_ERROR, response.user_summary)

        if call.intent == "product_usage":
            response = self._knowledge_adapter.query(
                ProductKnowledgeRequest(merchant_id=call.merchant_id, locale=call.locale, query=call.utterance)
            )
            if response.ok and not response.handoff_recommended:
                return CallFlowOutput(
                    resolved=True,
                    response_text=response.short_answer,
                    tools_called=["query_product_knowledge"],
                    handoff_required=False,
                    handoff_reason=HandoffReason.NONE,
                    handoff_id=None,
                )
            return self._handoff(call, HandoffReason.RAG_LOW_CONFIDENCE, response.short_answer)

        return self._handoff(call, HandoffReason.UNSUPPORTED_INTENT, "Intent is not supported yet.")

    def _handoff(self, call: CallFlowInput, reason: HandoffReason, summary: str) -> CallFlowOutput:
        response = self._handoff_adapter.handoff(
            HandoffRequest(
                call_id=call.call_id,
                merchant_id=call.merchant_id,
                intent_primary=call.intent,
                order_id_candidate=call.order_id_candidate,
                summary=summary,
                tools_called=[],
                handoff_reason=reason,
                recommended_next_step="Review the call context and continue with the customer.",
            )
        )
        return CallFlowOutput(
            resolved=False,
            response_text="I will transfer you to a human agent.",
            tools_called=["handoff_to_human"],
            handoff_required=True,
            handoff_reason=reason,
            handoff_id=response.handoff_id,
        )
