from voiceagents.adapters.knowledge import MockKnowledgeAdapter
from voiceagents.contracts.common import ToolErrorCode
from voiceagents.contracts.knowledge import ProductKnowledgeRequest


def test_known_wig_washing_query_returns_answer() -> None:
    adapter = MockKnowledgeAdapter()

    response = adapter.query(
        ProductKnowledgeRequest(
            merchant_id="merchant_demo",
            locale="en-GB",
            query="How should I wash my wig?",
        )
    )

    assert response.ok is True
    assert "cool water" in response.short_answer
    assert "faq:washing-care" in response.citations
    assert response.confidence > 0.8
    assert response.handoff_recommended is False


def test_unknown_query_recommends_handoff() -> None:
    adapter = MockKnowledgeAdapter()

    response = adapter.query(
        ProductKnowledgeRequest(
            merchant_id="merchant_demo",
            locale="en-GB",
            query="Can this wig survive a space flight?",
        )
    )

    assert response.ok is False
    assert response.short_answer
    assert response.citations == []
    assert response.confidence == 0.0
    assert response.handoff_recommended is True
    assert response.error_code == ToolErrorCode.NO_ANSWER

