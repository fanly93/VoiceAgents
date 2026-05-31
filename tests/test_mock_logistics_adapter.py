from voiceagents.adapters.logistics import MockLogisticsAdapter
from voiceagents.contracts.common import ToolErrorCode
from voiceagents.contracts.logistics import LookupLogisticsRequest


def test_lookup_logistics_returns_known_order_status() -> None:
    adapter = MockLogisticsAdapter()
    request = LookupLogisticsRequest(
        merchant_id="merchant-demo",
        order_id="ORD-20260601-1842",
    )

    response = adapter.lookup_logistics(request)

    assert response.ok is True
    assert response.status == "in_transit"
    assert response.latest_event == "Package departed the Shanghai Hongqiao sorting center."
    assert response.estimated_delivery == "2026-06-02"
    assert response.carrier == "YTO Express"
    assert response.user_summary == (
        "Your package is in transit with YTO Express and is estimated to arrive on 2026-06-02."
    )
    assert response.error_code is None


def test_lookup_logistics_returns_not_found_for_unknown_order() -> None:
    adapter = MockLogisticsAdapter()
    request = LookupLogisticsRequest(
        merchant_id="merchant-redacted",
        order_id="ORDER-UNKNOWN",
    )

    response = adapter.lookup_logistics(request)

    assert response.ok is False
    assert response.status is None
    assert response.latest_event is None
    assert response.estimated_delivery is None
    assert response.carrier is None
    assert response.user_summary
    assert response.error_code is ToolErrorCode.NOT_FOUND
