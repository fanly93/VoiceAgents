from voiceagents.adapters.handoff import MockHandoffAdapter
from voiceagents.agent.models import CallFlowInput
from voiceagents.agent.service import CallFlowService
from voiceagents.contracts.common import HandoffReason


def test_low_asr_confidence_hands_off() -> None:
    service = CallFlowService(handoff_adapter=MockHandoffAdapter())

    output = service.handle(
        CallFlowInput(
            call_id="CALL-REDACTED",
            merchant_id="merchant_demo",
            locale="en-GB",
            intent="order_status",
            utterance="Where is my order?",
            order_id_candidate="ORD-20260601-1842",
            order_id_confirmed=True,
            asr_confidence=0.42,
            customer_requested_human=False,
        )
    )

    assert output.resolved is False
    assert output.handoff_required is True
    assert output.handoff_reason == HandoffReason.LOW_ASR_CONFIDENCE
    assert output.handoff_id == "HND-20260601-0007"
