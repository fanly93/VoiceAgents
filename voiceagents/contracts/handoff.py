from pydantic import BaseModel, Field

from voiceagents.contracts.common import HandoffMode, HandoffReason


class HandoffRequest(BaseModel):
    call_id: str
    merchant_id: str
    intent_primary: str
    order_id_candidate: str | None
    summary: str = Field(min_length=1)
    tools_called: list[str]
    handoff_reason: HandoffReason
    recommended_next_step: str


class HandoffResponse(BaseModel):
    ok: bool
    handoff_id: str
    mode: HandoffMode
