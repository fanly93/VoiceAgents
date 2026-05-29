from voiceagents.contracts.common import ToolErrorCode
from voiceagents.contracts.order import LookupOrderRequest, LookupOrderResponse


def test_lookup_order_request_contains_merchant_and_order_ids() -> None:
    request = LookupOrderRequest(merchant_id="merchant-123", order_id="order-456")

    assert request.merchant_id == "merchant-123"
    assert request.order_id == "order-456"


def test_lookup_order_response_can_describe_successful_order() -> None:
    response = LookupOrderResponse(
        ok=True,
        order_exists=True,
        status="paid",
        user_summary="Order order-456 is paid.",
        safe_fields={"order_status": "paid"},
        error_code=None,
    )

    assert response.ok is True
    assert response.order_exists is True
    assert response.status == "paid"
    assert response.safe_fields["order_status"] == "paid"
    assert response.error_code is None


def test_lookup_order_response_can_describe_missing_order() -> None:
    response = LookupOrderResponse(
        ok=False,
        order_exists=False,
        status=None,
        user_summary="I could not find that order.",
        safe_fields={},
        error_code=ToolErrorCode.NOT_FOUND,
    )

    assert response.ok is False
    assert response.order_exists is False
    assert response.error_code is ToolErrorCode.NOT_FOUND
