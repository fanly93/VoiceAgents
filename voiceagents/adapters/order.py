from voiceagents.contracts.common import ToolErrorCode
from voiceagents.contracts.order import LookupOrderRequest, LookupOrderResponse


class MockOrderAdapter:
    def lookup_order(self, request: LookupOrderRequest) -> LookupOrderResponse:
        if request.order_id == "ORDER-REDACTED-001":
            return LookupOrderResponse(
                ok=True,
                order_exists=True,
                status="paid",
                user_summary="Order ORDER-REDACTED-001 has been paid.",
                safe_fields={"order_status": "paid"},
                error_code=None,
            )

        return LookupOrderResponse(
            ok=False,
            order_exists=False,
            status=None,
            user_summary="I could not find that order.",
            safe_fields={},
            error_code=ToolErrorCode.NOT_FOUND,
        )
