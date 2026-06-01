from voiceagents.adapters.knowledge import MockKnowledgeAdapter
from voiceagents.contracts.common import ToolErrorCode
from voiceagents.contracts.knowledge import ProductKnowledgeRequest


def test_known_lunacare_wig_washing_query_returns_answer() -> None:
    adapter = MockKnowledgeAdapter()

    response = adapter.query(
        ProductKnowledgeRequest(
            merchant_id="merchant_demo",
            locale="zh-CN",
            query="LunaCare 假发护理套装应该怎么清洗假发？",
        )
    )

    assert response.ok is True
    assert "cool water" in response.short_answer
    assert "wig-safe shampoo" in response.short_answer
    assert "faq:lunacare-wig-washing" in response.citations
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
