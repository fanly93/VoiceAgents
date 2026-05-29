from pydantic import BaseModel

from voiceagents.contracts.common import ToolErrorCode


class LookupLogisticsRequest(BaseModel):
    merchant_id: str
    order_id: str


class LookupLogisticsResponse(BaseModel):
    ok: bool
    status: str | None
    latest_event: str | None
    estimated_delivery: str | None
    carrier: str | None
    user_summary: str
    error_code: ToolErrorCode | None
