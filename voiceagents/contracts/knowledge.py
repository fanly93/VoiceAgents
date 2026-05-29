from pydantic import BaseModel, Field

from voiceagents.contracts.common import ToolErrorCode


class ProductKnowledgeRequest(BaseModel):
    merchant_id: str
    locale: str
    query: str


class ProductKnowledgeResponse(BaseModel):
    ok: bool
    short_answer: str
    citations: list[str]
    confidence: float = Field(ge=0, le=1)
    handoff_recommended: bool
    error_code: ToolErrorCode | None
