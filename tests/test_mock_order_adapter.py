from voiceagents.adapters.order import MockOrderAdapter
from voiceagents.contracts.common import ToolErrorCode
from voiceagents.contracts.order import LookupOrderRequest


def test_lookup_order_returns_known_redacted_order() -> None:
    adapter = MockOrderAdapter()

    response = adapter.lookup_order(
        LookupOrderRequest(
            merchant_id="merchant-123",
            order_id="ORDER-REDACTED-001",
        )
    )

    assert response.ok is True
    assert response.order_exists is True
    assert response.status == "paid"
    assert response.user_summary
    assert response.safe_fields["order_status"] == "paid"
    assert response.error_code is None


def test_lookup_order_returns_not_found_for_unknown_order() -> None:
    adapter = MockOrderAdapter()

    response = adapter.lookup_order(
        LookupOrderRequest(
            merchant_id="merchant-123",
            order_id="ORDER-UNKNOWN-001",
        )
    )

    assert response.ok is False
    assert response.order_exists is False
    assert response.status is None
    assert response.user_summary
    assert response.safe_fields == {}
    assert response.error_code is ToolErrorCode.NOT_FOUND
