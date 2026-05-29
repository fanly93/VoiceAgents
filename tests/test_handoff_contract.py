import pytest
from pydantic import ValidationError

from voiceagents.contracts.common import HandoffMode, HandoffReason
from voiceagents.contracts.handoff import HandoffRequest, HandoffResponse


def test_handoff_request_accepts_live_transfer_details() -> None:
    request = HandoffRequest(
        call_id="call-123",
        merchant_id="merchant-456",
        intent_primary="order_status",
        order_id_candidate="order-789",
        summary="Customer needs a human agent to confirm an ambiguous delivery issue.",
        tools_called=["lookup_order", "lookup_logistics"],
        handoff_reason=HandoffReason.CUSTOMER_REQUESTS_HUMAN,
        recommended_next_step="Transfer to the merchant support queue.",
    )

    assert request.call_id == "call-123"
    assert request.merchant_id == "merchant-456"
    assert request.order_id_candidate == "order-789"
    assert request.tools_called == ["lookup_order", "lookup_logistics"]
    assert request.handoff_reason is HandoffReason.CUSTOMER_REQUESTS_HUMAN


def test_handoff_response_accepts_live_transfer_mode() -> None:
    response = HandoffResponse(
        ok=True,
        handoff_id="handoff-123",
        mode=HandoffMode.LIVE_TRANSFER,
    )

    assert response.ok is True
    assert response.handoff_id == "handoff-123"
    assert response.mode is HandoffMode.LIVE_TRANSFER


def test_handoff_request_requires_non_empty_summary() -> None:
    with pytest.raises(ValidationError):
        HandoffRequest(
            call_id="call-123",
            merchant_id="merchant-456",
            intent_primary="order_status",
            order_id_candidate=None,
            summary="",
            tools_called=[],
            handoff_reason=HandoffReason.LOW_ASR_CONFIDENCE,
            recommended_next_step="Call the customer back.",
        )
