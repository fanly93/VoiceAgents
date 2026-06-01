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
        if request.order_id == "ORD-20260601-1842":
            return LookupLogisticsResponse(
                ok=True,
                status="in_transit",
                latest_event="Package departed the Shanghai Hongqiao sorting center.",
                estimated_delivery="2026-06-02",
                carrier="YTO Express",
                user_summary=(
                    "Your package is in transit with YTO Express and is "
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
