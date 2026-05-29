from voiceagents.agent.models import CallFlowInput, CallFlowOutput
from voiceagents.contracts.common import HandoffReason
from voiceagents.contracts.handoff import HandoffRequest


LOW_ASR_CONFIDENCE_THRESHOLD = 0.6


class CallFlowService:
    def __init__(self, handoff_adapter) -> None:
        self._handoff_adapter = handoff_adapter

    def handle(self, call: CallFlowInput) -> CallFlowOutput:
        if call.asr_confidence < LOW_ASR_CONFIDENCE_THRESHOLD:
            return self._handoff(call, HandoffReason.LOW_ASR_CONFIDENCE, "ASR confidence is too low.")

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

