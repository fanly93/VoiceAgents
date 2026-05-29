import pytest
from pydantic import ValidationError

from voiceagents.agent.models import CallFlowInput, CallFlowOutput
from voiceagents.contracts.common import HandoffReason


def test_call_flow_input_accepts_valid_data() -> None:
    model = CallFlowInput(
        call_id="CALL-REDACTED",
        merchant_id="merchant_demo",
        locale="en-GB",
        intent="order_status",
        utterance="Where is my order?",
        order_id_candidate="ORDER-REDACTED-001",
        order_id_confirmed=True,
        asr_confidence=0.91,
        customer_requested_human=False,
    )

    assert model.order_id_confirmed is True
    assert model.asr_confidence == 0.91


def test_call_flow_output_accepts_valid_data() -> None:
    model = CallFlowOutput(
        resolved=False,
        response_text="I will transfer you to a human agent.",
        tools_called=["handoff_to_human"],
        handoff_required=True,
        handoff_reason=HandoffReason.LOW_ASR_CONFIDENCE,
        handoff_id="HANDOFF-REDACTED",
    )

    assert model.handoff_required is True
    assert model.handoff_reason == HandoffReason.LOW_ASR_CONFIDENCE


def test_call_flow_input_rejects_confidence_above_one() -> None:
    with pytest.raises(ValidationError):
        CallFlowInput(
            call_id="CALL-REDACTED",
            merchant_id="merchant_demo",
            locale="en-GB",
            intent="order_status",
            utterance="Where is my order?",
            order_id_candidate="ORDER-REDACTED-001",
            order_id_confirmed=True,
            asr_confidence=1.2,
            customer_requested_human=False,
        )

