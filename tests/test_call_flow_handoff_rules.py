import pytest

from voiceagents.adapters.handoff import MockHandoffAdapter
from voiceagents.agent.models import CallFlowInput
from voiceagents.agent.service import CallFlowService
from voiceagents.contracts.common import HandoffReason


def make_call(intent: str, *, customer_requested_human: bool = False) -> CallFlowInput:
    return CallFlowInput(
        call_id="CALL-REDACTED",
        merchant_id="merchant_demo",
        locale="en-GB",
        intent=intent,
        utterance="Please help me.",
        order_id_candidate=None,
        order_id_confirmed=False,
        asr_confidence=0.91,
        customer_requested_human=customer_requested_human,
    )


@pytest.mark.parametrize(
    ("call", "expected_reason"),
    [
        (make_call("order_status", customer_requested_human=True), HandoffReason.CUSTOMER_REQUESTS_HUMAN),
        (make_call("complaint"), HandoffReason.COMPLAINT_OR_ANGRY_CUSTOMER),
        (make_call("return_exchange_refund"), HandoffReason.REFUND_OR_RETURN_EXCEPTION),
        (make_call("unsupported_intent"), HandoffReason.UNSUPPORTED_INTENT),
    ],
)
def test_mandatory_handoff_rules(call: CallFlowInput, expected_reason: HandoffReason) -> None:
    service = CallFlowService(handoff_adapter=MockHandoffAdapter())

    output = service.handle(call)

    assert output.resolved is False
    assert output.handoff_required is True
    assert output.handoff_reason == expected_reason
    assert output.handoff_id == "HND-20260601-0007"

