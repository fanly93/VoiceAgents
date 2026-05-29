from pydantic import BaseModel

from voiceagents.contracts.common import ToolErrorCode


class LookupOrderRequest(BaseModel):
    merchant_id: str
    order_id: str


class LookupOrderResponse(BaseModel):
    ok: bool
    order_exists: bool
    status: str | None
    user_summary: str
    safe_fields: dict[str, str]
    error_code: ToolErrorCode | None
