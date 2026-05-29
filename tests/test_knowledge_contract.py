import pytest
from pydantic import ValidationError

from voiceagents.contracts.common import ToolErrorCode
from voiceagents.contracts.knowledge import (
    ProductKnowledgeRequest,
    ProductKnowledgeResponse,
)


def test_product_knowledge_response_accepts_high_confidence_rag_answer() -> None:
    request = ProductKnowledgeRequest(
        merchant_id="merchant_123",
        locale="en-US",
        query="What is your return policy?",
    )
    response = ProductKnowledgeResponse(
        ok=True,
        short_answer="Items can be returned within 30 days with a receipt.",
        citations=["returns-policy"],
        confidence=0.86,
        handoff_recommended=False,
        error_code=None,
    )

    assert request.merchant_id == "merchant_123"
    assert request.locale == "en-US"
    assert request.query == "What is your return policy?"
    assert response.ok is True
    assert response.short_answer == "Items can be returned within 30 days with a receipt."
    assert response.citations == ["returns-policy"]
    assert response.confidence == 0.86
    assert response.handoff_recommended is False
    assert response.error_code is None


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_product_knowledge_response_rejects_confidence_outside_unit_interval(
    confidence: float,
) -> None:
    with pytest.raises(ValidationError):
        ProductKnowledgeResponse(
            ok=False,
            short_answer="",
            citations=[],
            confidence=confidence,
            handoff_recommended=True,
            error_code=ToolErrorCode.LOW_CONFIDENCE,
        )
