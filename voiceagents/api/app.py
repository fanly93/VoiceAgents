from datetime import datetime, timezone
import os
import uuid

from fastapi import FastAPI, HTTPException

from voiceagents.adapters.handoff import MockHandoffAdapter
from voiceagents.adapters.knowledge import MockKnowledgeAdapter
from voiceagents.adapters.logistics import MockLogisticsAdapter
from voiceagents.adapters.order import MockOrderAdapter
from voiceagents.agent.models import CallFlowInput, CallFlowOutput
from voiceagents.agent.service import CallFlowService
from voiceagents.realtime.contracts import (
    RealtimeClientSecretRequest,
    RealtimeClientSecretResponse,
    RealtimeProviderName,
    VoiceEvent,
    VoiceSessionState,
)
from voiceagents.realtime.event_log import InMemoryVoiceEventRepository, VoiceEventRepository
from voiceagents.realtime.providers import (
    MockRealtimeProvider,
    OpenAIRealtimeProvider,
    RealtimeProviderError,
)
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore


def create_app(
    *,
    realtime_session_store: InMemoryVoiceSessionStore | None = None,
    realtime_event_repository: VoiceEventRepository | None = None,
) -> FastAPI:
    app = FastAPI(title="VoiceAgents")
    call_flow_service = CallFlowService(
        handoff_adapter=MockHandoffAdapter(),
        order_adapter=MockOrderAdapter(),
        logistics_adapter=MockLogisticsAdapter(),
        knowledge_adapter=MockKnowledgeAdapter(),
    )
    session_store = realtime_session_store or InMemoryVoiceSessionStore()
    event_repository = realtime_event_repository or InMemoryVoiceEventRepository()
    app.state.realtime_session_store = session_store
    app.state.realtime_event_repository = event_repository

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/calls/simulate")
    def simulate_call(call: CallFlowInput) -> CallFlowOutput:
        return call_flow_service.handle(call)

    @app.post("/v1/realtime/client-secret")
    def create_realtime_client_secret(
        request: RealtimeClientSecretRequest,
    ) -> RealtimeClientSecretResponse:
        created_session = session_store.create_session(
            session_id=request.session_id,
            call_id=request.call_id,
            merchant_id=request.merchant_id,
        )
        provider = _build_realtime_provider()
        try:
            provider_response = provider.create_client_secret(request)
        except RealtimeProviderError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

        response = provider_response.model_copy(
            update={"tool_call_token": created_session.tool_call_token}
        )
        event_repository.append(
            VoiceEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=request.session_id,
                call_id=request.call_id,
                merchant_id=request.merchant_id,
                state=VoiceSessionState.IDLE,
                event_type="session_created",
                transcript_text_redacted=None,
                response_text_redacted=None,
                tool_name=None,
                tool_arguments_redacted=None,
                tool_result_summary="Realtime session created.",
                handoff_reason=None,
                latency_ms=None,
                provider=response.provider,
                provider_event_type=None,
                redaction_applied=False,
            )
        )
        return response

    return app


def _build_realtime_provider() -> MockRealtimeProvider | OpenAIRealtimeProvider:
    provider_name = os.getenv("VOICEAGENTS_REALTIME_PROVIDER", RealtimeProviderName.MOCK.value)
    if provider_name == RealtimeProviderName.MOCK.value:
        return MockRealtimeProvider()
    if provider_name == RealtimeProviderName.OPENAI_REALTIME.value:
        return OpenAIRealtimeProvider(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("VOICEAGENTS_OPENAI_REALTIME_MODEL", "gpt-realtime"),
            voice=os.getenv("VOICEAGENTS_OPENAI_REALTIME_VOICE", "alloy"),
        )
    raise HTTPException(status_code=500, detail=f"Unsupported realtime provider: {provider_name}")
