from datetime import datetime, timezone
import os
from pathlib import Path
import uuid

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse

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
    RealtimeToolCallRequest,
    RealtimeToolCallResponse,
    VoiceEvent,
    VoiceSessionState,
)
from voiceagents.realtime.event_log import JsonlVoiceEventRepository, VoiceEventRepository
from voiceagents.realtime.providers import (
    MockRealtimeProvider,
    OpenAIRealtimeProvider,
    RealtimeProviderError,
)
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore
from voiceagents.realtime.tool_router import (
    InvalidToolArgumentsError,
    InvalidToolCallTokenError,
    RealtimeToolRouter,
    UnknownRealtimeToolError,
)


REALTIME_TEST_PAGE_PATH = Path(__file__).parent / "static" / "realtime-test.html"


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
    event_repository = realtime_event_repository or JsonlVoiceEventRepository()
    tool_router = RealtimeToolRouter(
        session_store=session_store,
        order_adapter=MockOrderAdapter(),
        logistics_adapter=MockLogisticsAdapter(),
        knowledge_adapter=MockKnowledgeAdapter(),
        handoff_adapter=MockHandoffAdapter(),
    )
    app.state.realtime_session_store = session_store
    app.state.realtime_event_repository = event_repository

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/calls/simulate")
    def simulate_call(call: CallFlowInput) -> CallFlowOutput:
        return call_flow_service.handle(call)

    @app.get("/realtime-test")
    def realtime_test_page() -> FileResponse:
        return FileResponse(REALTIME_TEST_PAGE_PATH, media_type="text/html")

    @app.post("/v1/realtime/client-secret")
    def create_realtime_client_secret(
        request: RealtimeClientSecretRequest,
    ) -> RealtimeClientSecretResponse:
        created_session = session_store.create_session(
            session_id=request.session_id,
            call_id=request.call_id,
            merchant_id=request.merchant_id,
        )
        provider_name = _current_realtime_provider_name()
        provider = _build_realtime_provider(provider_name)
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

    @app.post("/v1/realtime/tool-call")
    def execute_realtime_tool_call(
        request: RealtimeToolCallRequest,
        authorization: str | None = Header(default=None),
    ) -> RealtimeToolCallResponse:
        tool_call_token = _extract_bearer_token(authorization)
        try:
            response = tool_router.execute(request, tool_call_token=tool_call_token)
        except UnknownRealtimeToolError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except InvalidToolArgumentsError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except InvalidToolCallTokenError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error

        event_repository.append(
            VoiceEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=request.session_id,
                call_id=request.call_id,
                merchant_id=request.merchant_id,
                state=(
                    VoiceSessionState.HANDOFF_PENDING
                    if response.handoff_required
                    else VoiceSessionState.TOOL_CALLING
                ),
                event_type="tool_call",
                transcript_text_redacted=None,
                response_text_redacted=None,
                tool_name=request.tool_name,
                tool_arguments_redacted=request.arguments,
                tool_result_summary=response.safe_summary,
                handoff_reason=response.handoff_reason,
                latency_ms=None,
                provider=_current_realtime_provider_name(),
                provider_event_type=None,
                redaction_applied=False,
            )
        )
        session_store.append_tool_call(
            request.session_id,
            request.tool_name,
            response.safe_summary,
        )
        return response

    return app


def _current_realtime_provider_name() -> RealtimeProviderName:
    provider_name = os.getenv("VOICEAGENTS_REALTIME_PROVIDER", RealtimeProviderName.MOCK.value)
    try:
        return RealtimeProviderName(provider_name)
    except ValueError as error:
        raise HTTPException(status_code=500, detail=f"Unsupported realtime provider: {provider_name}") from error


def _build_realtime_provider(
    provider_name: RealtimeProviderName,
) -> MockRealtimeProvider | OpenAIRealtimeProvider:
    if provider_name is RealtimeProviderName.MOCK:
        return MockRealtimeProvider()
    if provider_name is RealtimeProviderName.OPENAI_REALTIME:
        return OpenAIRealtimeProvider(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("VOICEAGENTS_OPENAI_REALTIME_MODEL", "gpt-realtime"),
            voice=os.getenv("VOICEAGENTS_OPENAI_REALTIME_VOICE", "alloy"),
        )
    raise HTTPException(status_code=500, detail=f"Unsupported realtime provider: {provider_name}")


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Malformed Authorization header")
    return token
