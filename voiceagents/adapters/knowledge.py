from voiceagents.contracts.common import ToolErrorCode
from voiceagents.contracts.knowledge import ProductKnowledgeRequest, ProductKnowledgeResponse


class MockKnowledgeAdapter:
    def query(self, request: ProductKnowledgeRequest) -> ProductKnowledgeResponse:
        if "wash" in request.query.lower():
            return ProductKnowledgeResponse(
                ok=True,
                short_answer=(
                    "Use cool water and a small amount of wig-safe shampoo. "
                    "Do not twist the hair. Let it air dry on a stand."
                ),
                citations=["faq:washing-care"],
                confidence=0.86,
                handoff_recommended=False,
                error_code=None,
            )

        return ProductKnowledgeResponse(
            ok=False,
            short_answer="I do not have enough information to answer that safely. I will transfer you to a human agent.",
            citations=[],
            confidence=0.0,
            handoff_recommended=True,
            error_code=ToolErrorCode.NO_ANSWER,
        )
