from fastapi import FastAPI

from voiceagents.adapters.handoff import MockHandoffAdapter
from voiceagents.adapters.knowledge import MockKnowledgeAdapter
from voiceagents.adapters.logistics import MockLogisticsAdapter
from voiceagents.adapters.order import MockOrderAdapter
from voiceagents.agent.models import CallFlowInput, CallFlowOutput
from voiceagents.agent.service import CallFlowService


def create_app() -> FastAPI:
    app = FastAPI(title="VoiceAgents")
    call_flow_service = CallFlowService(
        handoff_adapter=MockHandoffAdapter(),
        order_adapter=MockOrderAdapter(),
        logistics_adapter=MockLogisticsAdapter(),
        knowledge_adapter=MockKnowledgeAdapter(),
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/calls/simulate")
    def simulate_call(call: CallFlowInput) -> CallFlowOutput:
        return call_flow_service.handle(call)

    return app
