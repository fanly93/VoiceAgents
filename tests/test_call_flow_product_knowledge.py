from voiceagents.adapters.handoff import MockHandoffAdapter
from voiceagents.adapters.knowledge import MockKnowledgeAdapter
from voiceagents.agent.models import CallFlowInput
from voiceagents.agent.service import CallFlowService
from voiceagents.contracts.common import HandoffReason
from voiceagents.contracts.handoff import HandoffRequest


class RecordingHandoffAdapter(MockHandoffAdapter):
    def __init__(self) -> None:
        self.last_request: HandoffRequest | None = None

    def handoff(self, request: HandoffRequest):
        self.last_request = request
        return super().handoff(request)


def test_known_product_question_is_resolved() -> None:
    service = CallFlowService(
        handoff_adapter=MockHandoffAdapter(),
        knowledge_adapter=MockKnowledgeAdapter(),
    )

    output = service.handle(
        CallFlowInput(
            call_id="CALL-REDACTED",
            merchant_id="merchant_demo",
            locale="en-GB",
            intent="product_usage",
            utterance="LunaCare 假发护理套装应该怎么清洗假发？",
            order_id_candidate=None,
            order_id_confirmed=False,
            asr_confidence=0.91,
            customer_requested_human=False,
        )
    )

    assert output.resolved is True
    assert output.handoff_required is False
    assert output.handoff_reason == HandoffReason.NONE
    assert output.tools_called == ["query_product_knowledge"]
    assert "cool water" in output.response_text


def test_unknown_product_question_hands_off() -> None:
    handoff_adapter = RecordingHandoffAdapter()
    service = CallFlowService(
        handoff_adapter=handoff_adapter,
        knowledge_adapter=MockKnowledgeAdapter(),
    )

    output = service.handle(
        CallFlowInput(
            call_id="CALL-REDACTED",
            merchant_id="merchant_demo",
            locale="en-GB",
            intent="product_usage",
            utterance="Can this wig survive a space flight?",
            order_id_candidate=None,
            order_id_confirmed=False,
            asr_confidence=0.91,
            customer_requested_human=False,
        )
    )

    assert output.resolved is False
    assert output.handoff_required is True
    assert output.handoff_reason == HandoffReason.RAG_LOW_CONFIDENCE
    assert output.handoff_id == "HND-20260601-0007"
    assert output.tools_called == ["query_product_knowledge", "handoff_to_human"]
    assert handoff_adapter.last_request is not None
    assert handoff_adapter.last_request.tools_called == ["query_product_knowledge"]
