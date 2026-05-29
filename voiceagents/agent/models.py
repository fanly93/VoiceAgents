from pydantic import BaseModel, Field

from voiceagents.contracts.common import HandoffReason


class CallFlowInput(BaseModel):
    call_id: str
    merchant_id: str
    locale: str
    intent: str
    utterance: str
    order_id_candidate: str | None
    order_id_confirmed: bool
    asr_confidence: float = Field(ge=0.0, le=1.0)
    customer_requested_human: bool


class CallFlowOutput(BaseModel):
    resolved: bool
    response_text: str
    tools_called: list[str]
    handoff_required: bool
    handoff_reason: HandoffReason
    handoff_id: str | None

