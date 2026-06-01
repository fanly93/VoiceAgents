from voiceagents.adapters.handoff import MockHandoffAdapter
from voiceagents.adapters.order import MockOrderAdapter
from voiceagents.agent.models import CallFlowInput
from voiceagents.agent.service import CallFlowService
from voiceagents.contracts.common import HandoffReason


def test_confirmed_order_status_call_is_resolved() -> None:
    service = CallFlowService(
        handoff_adapter=MockHandoffAdapter(),
        order_adapter=MockOrderAdapter(),
    )

    output = service.handle(
        CallFlowInput(
            call_id="CALL-REDACTED",
            merchant_id="merchant_demo",
            locale="en-GB",
            intent="order_status",
            utterance="Where is my order?",
            order_id_candidate="ORD-20260601-1842",
            order_id_confirmed=True,
            asr_confidence=0.91,
            customer_requested_human=False,
        )
    )

    assert output.resolved is True
    assert output.handoff_required is False
    assert output.handoff_reason == HandoffReason.NONE
    assert output.tools_called == ["lookup_order"]
    assert "paid" in output.response_text
