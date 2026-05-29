from voiceagents.contracts.common import ToolErrorCode
from voiceagents.contracts.logistics import (
    LookupLogisticsRequest,
    LookupLogisticsResponse,
)


def test_lookup_logistics_request_accepts_required_identifiers() -> None:
    request = LookupLogisticsRequest(merchant_id="merchant-123", order_id="order-456")

    assert request.merchant_id == "merchant-123"
    assert request.order_id == "order-456"


def test_lookup_logistics_response_accepts_in_transit_details() -> None:
    response = LookupLogisticsResponse(
        ok=True,
        status="in_transit",
        latest_event="Departed sorting facility",
        estimated_delivery="2026-06-01",
        carrier="SF Express",
        user_summary="Your package is in transit and expected on 2026-06-01.",
        error_code=None,
    )

    assert response.ok is True
    assert response.status == "in_transit"
    assert response.latest_event == "Departed sorting facility"
    assert response.estimated_delivery == "2026-06-01"
    assert response.carrier == "SF Express"
    assert response.user_summary == "Your package is in transit and expected on 2026-06-01."
    assert response.error_code is None


def test_lookup_logistics_response_accepts_system_error() -> None:
    response = LookupLogisticsResponse(
        ok=False,
        status=None,
        latest_event=None,
        estimated_delivery=None,
        carrier=None,
        user_summary="Logistics lookup is temporarily unavailable.",
        error_code=ToolErrorCode.SYSTEM_ERROR,
    )

    assert response.ok is False
    assert response.error_code is ToolErrorCode.SYSTEM_ERROR
