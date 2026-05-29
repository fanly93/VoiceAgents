from voiceagents.contracts.common import ToolErrorCode
from voiceagents.contracts.logistics import (
    LookupLogisticsRequest,
    LookupLogisticsResponse,
)


class MockLogisticsAdapter:
    def lookup_logistics(
        self,
        request: LookupLogisticsRequest,
    ) -> LookupLogisticsResponse:
        if request.order_id == "ORDER-REDACTED-001":
            return LookupLogisticsResponse(
                ok=True,
                status="in_transit",
                latest_event="Package departed the redacted sorting facility.",
                estimated_delivery="2026-06-02",
                carrier="carrier-redacted",
                user_summary=(
                    "Your package is in transit with carrier-redacted and is "
                    "estimated to arrive on 2026-06-02."
                ),
                error_code=None,
            )

        return LookupLogisticsResponse(
            ok=False,
            status=None,
            latest_event=None,
            estimated_delivery=None,
            carrier=None,
            user_summary="I could not find logistics information for that order.",
            error_code=ToolErrorCode.NOT_FOUND,
        )
