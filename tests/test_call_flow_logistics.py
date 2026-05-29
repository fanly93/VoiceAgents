from voiceagents.adapters.handoff import MockHandoffAdapter
from voiceagents.adapters.logistics import MockLogisticsAdapter
from voiceagents.agent.models import CallFlowInput
from voiceagents.agent.service import CallFlowService
from voiceagents.contracts.common import HandoffReason


def test_confirmed_logistics_call_is_resolved() -> None:
    service = CallFlowService(
        handoff_adapter=MockHandoffAdapter(),
        logistics_adapter=MockLogisticsAdapter(),
    )

    output = service.handle(
        CallFlowInput(
            call_id="CALL-REDACTED",
            merchant_id="merchant_demo",
            locale="en-GB",
            intent="logistics_tracking",
            utterance="Where is my package?",
            order_id_candidate="ORDER-REDACTED-001",
            order_id_confirmed=True,
            asr_confidence=0.91,
            customer_requested_human=False,
        )
    )

    assert output.resolved is True
    assert output.handoff_required is False
    assert output.handoff_reason == HandoffReason.NONE
    assert output.tools_called == ["lookup_logistics"]
    assert "2026-06-02" in output.response_text
