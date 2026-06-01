from datetime import datetime, timezone
import os
from pathlib import Path
from urllib.parse import urlparse
import uuid

from fastapi import Body, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import ValidationError

from voiceagents.adapters.handoff import MockHandoffAdapter
from voiceagents.adapters.knowledge import MockKnowledgeAdapter
from voiceagents.adapters.logistics import MockLogisticsAdapter
from voiceagents.adapters.order import MockOrderAdapter
from voiceagents.agent.models import CallFlowInput, CallFlowOutput
from voiceagents.agent.service import CallFlowService
from voiceagents.realtime.contracts import (
    NormalizedRealtimeEventType,
    RealtimeClientSecretRequest,
    RealtimeClientSecretResponse,
    RealtimeEventIngestRequest,
    RealtimeEventIngestResponse,
    RealtimeProviderName,
    RealtimeTranscriptEvent,
    RealtimeTranscriptEventType,
    RealtimeToolCallRequest,
    RealtimeToolCallResponse,
    TranscriptLoggingMode,
    VoiceEvent,
    VoiceSessionState,
)
from voiceagents.realtime.event_log import (
    find_blocked_event_keys,
    JsonlRealtimeTranscriptRepository,
    JsonlVoiceEventRepository,
    RealtimeTranscriptRepository,
    VoiceEventRepository,
)
from voiceagents.realtime.providers import (
    MockRealtimeProvider,
    OpenAIRealtimeProvider,
    RealtimeProviderError,
)
from voiceagents.realtime.redaction import redact_text
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore, VoiceSessionNotFound
from voiceagents.realtime.tool_router import (
    InvalidToolArgumentsError,
    InvalidToolCallTokenError,
    RealtimeToolRouter,
    UnknownRealtimeToolError,
)
from voiceagents.realtime.validation import (
    STANDARD_VALIDATION_SCENARIOS,
    ValidationRunFinishRequest,
    ValidationRunFinishResponse,
    ValidationRunRepository,
    ValidationRunStartRequest,
    ValidationRunStartResponse,
)


REALTIME_TEST_PAGE_PATH = Path(__file__).parent / "static" / "realtime-test.html"
REALTIME_OPENAI_ADAPTER_PATH = Path(__file__).parent / "static" / "realtime-openai-adapter.js"
DEFAULT_REALTIME_CLIENT_SECRET_RATE_LIMIT = 20


def create_app(
    *,
    realtime_session_store: InMemoryVoiceSessionStore | None = None,
    realtime_event_repository: VoiceEventRepository | None = None,
    realtime_transcript_repository: RealtimeTranscriptRepository | None = None,
    realtime_validation_repository: ValidationRunRepository | None = None,
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
    transcript_repository = realtime_transcript_repository or JsonlRealtimeTranscriptRepository()
    validation_repository = realtime_validation_repository or ValidationRunRepository()
    tool_router = RealtimeToolRouter(
        session_store=session_store,
        order_adapter=MockOrderAdapter(),
        logistics_adapter=MockLogisticsAdapter(),
        knowledge_adapter=MockKnowledgeAdapter(),
        handoff_adapter=MockHandoffAdapter(),
    )
    app.state.realtime_session_store = session_store
    app.state.realtime_event_repository = event_repository
    app.state.realtime_transcript_repository = transcript_repository
    app.state.realtime_validation_repository = validation_repository
    app.state.realtime_client_secret_rate_limits = {}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/calls/simulate")
    def simulate_call(call: CallFlowInput) -> CallFlowOutput:
        return call_flow_service.handle(call)

    @app.get("/realtime-test")
    def realtime_test_page() -> FileResponse:
        return FileResponse(REALTIME_TEST_PAGE_PATH, media_type="text/html")

    @app.get("/static/realtime-openai-adapter.js")
    def realtime_openai_adapter() -> FileResponse:
        return FileResponse(REALTIME_OPENAI_ADAPTER_PATH, media_type="application/javascript")

    @app.get("/v1/realtime/validation-scenarios")
    def list_realtime_validation_scenarios() -> list:
        return STANDARD_VALIDATION_SCENARIOS

    @app.post("/v1/realtime/validation-runs")
    def start_realtime_validation_run(
        request: ValidationRunStartRequest,
    ) -> ValidationRunStartResponse:
        try:
            return validation_repository.start_run(request)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/v1/realtime/validation-runs/{run_id}/finish")
    def finish_realtime_validation_run(
        run_id: str,
        request: ValidationRunFinishRequest,
    ) -> ValidationRunFinishResponse:
        try:
            return validation_repository.finish_run(run_id, request)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post("/v1/realtime/client-secret")
    def create_realtime_client_secret(
        request: RealtimeClientSecretRequest,
        http_request: Request,
    ) -> RealtimeClientSecretResponse:
        provider_name = _current_realtime_provider_name()
        _enforce_real_provider_dev_gate(provider_name, http_request, app)
        provider = _build_realtime_provider(provider_name)
        try:
            provider_response = provider.create_client_secret(request)
        except RealtimeProviderError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

        created_session = session_store.create_session(
            session_id=request.session_id,
            call_id=request.call_id,
            merchant_id=request.merchant_id,
            provider=provider_response.provider,
            token_expires_at=_parse_provider_expiry(provider_response.expires_at),
        )
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
                provider_call_id=None,
                tool_status=None,
                redaction_applied=False,
            )
        )
        return response

    @app.post("/v1/realtime/event")
    def ingest_realtime_event(
        payload: dict[str, object] = Body(...),
        authorization: str | None = Header(default=None),
    ) -> RealtimeEventIngestResponse:
        tool_call_token = _extract_bearer_token(authorization)
        blocked_keys = find_blocked_event_keys(payload)
        if blocked_keys:
            raise HTTPException(
                status_code=422,
                detail=f"Blocked realtime event keys: {', '.join(blocked_keys)}",
            )
        try:
            request = RealtimeEventIngestRequest.model_validate(payload)
        except ValidationError as error:
            raise HTTPException(
                status_code=422,
                detail=_serializable_validation_errors(error),
            ) from error
        try:
            token_is_bound = session_store.verify_session_token_binding(
                request.session_id,
                tool_call_token,
                call_id=request.call_id,
                merchant_id=request.merchant_id,
                provider=request.provider,
            )
        except VoiceSessionNotFound as error:
            raise HTTPException(status_code=403, detail="Invalid realtime event session") from error

        if not token_is_bound:
            raise HTTPException(status_code=403, detail="Invalid realtime event token or binding")

        event_id = str(uuid.uuid4())
        transcript_logging_mode = _current_transcript_logging_mode()
        text_redaction = redact_text(request.text) if request.text is not None else None
        summary_redaction = (
            redact_text(request.safe_summary) if request.safe_summary is not None else None
        )
        redacted_text = text_redaction.value if text_redaction is not None else None
        redacted_summary = summary_redaction.value if summary_redaction is not None else None
        redaction_applied = (
            (text_redaction.redaction_applied if text_redaction is not None else False)
            or (summary_redaction.redaction_applied if summary_redaction is not None else False)
        )
        structured_text = (
            redacted_text
            if transcript_logging_mode is not TranscriptLoggingMode.OFF
            else None
        )
        event_repository.append(
            VoiceEvent(
                event_id=event_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=request.session_id,
                call_id=request.call_id,
                merchant_id=request.merchant_id,
                state=request.state,
                event_type=request.event_type.value,
                transcript_text_redacted=structured_text if request.speaker == "user" else None,
                response_text_redacted=structured_text if request.speaker == "assistant" else None,
                tool_name=request.tool_name,
                tool_arguments_redacted=None,
                tool_result_summary=redacted_summary,
                handoff_reason=None,
                latency_ms=request.latency_ms,
                provider=request.provider,
                provider_event_type=request.provider_event_type,
                provider_call_id=request.provider_call_id,
                tool_status=request.tool_status,
                redaction_applied=redaction_applied,
            )
        )
        if (
            redacted_text is not None
            and request.speaker is not None
            and transcript_logging_mode is not TranscriptLoggingMode.OFF
        ):
            session_store.append_transcript(request.session_id, request.speaker, redacted_text)
        if (
            redacted_text is not None
            and request.speaker is not None
            and transcript_logging_mode is TranscriptLoggingMode.TRANSCRIPT
            and _is_transcript_done_event(request.event_type)
        ):
            transcript_repository.append(
                RealtimeTranscriptEvent(
                    event_id=event_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    session_id=request.session_id,
                    call_id=request.call_id,
                    merchant_id=request.merchant_id,
                    speaker=request.speaker,
                    event_type=RealtimeTranscriptEventType.TRANSCRIPT_DONE,
                    turn_id=request.turn_id,
                    sequence=request.sequence,
                    text_redacted=redacted_text,
                    provider=request.provider,
                    provider_event_type=request.provider_event_type,
                    redaction_applied=redaction_applied,
                )
            )
        session_store.update_state(request.session_id, request.state)
        return RealtimeEventIngestResponse(
            ok=True,
            event_id=event_id,
            redaction_applied=redaction_applied,
        )

    @app.post("/v1/realtime/tool-call")
    def execute_realtime_tool_call(
        request: RealtimeToolCallRequest,
        authorization: str | None = Header(default=None),
    ) -> RealtimeToolCallResponse:
        tool_call_token = _extract_bearer_token(authorization)
        provider_name = _current_realtime_provider_name()
        try:
            response = tool_router.execute(
                request,
                tool_call_token=tool_call_token,
                provider=provider_name,
            )
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
                tool_arguments_redacted=None,
                tool_result_summary=response.safe_summary,
                handoff_reason=response.handoff_reason,
                latency_ms=None,
                provider=provider_name,
                provider_event_type=None,
                provider_call_id=None,
                tool_status="completed",
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


def _enforce_real_provider_dev_gate(
    provider_name: RealtimeProviderName,
    request: Request,
    app: FastAPI,
) -> None:
    if provider_name is not RealtimeProviderName.OPENAI_REALTIME:
        return

    if os.getenv("VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS", "false").lower() != "true":
        raise HTTPException(
            status_code=403,
            detail="OpenAI realtime dev endpoints are disabled",
        )

    origin = request.headers.get("origin")
    host = request.headers.get("host")
    client_host = request.client.host if request.client is not None else "unknown"
    if origin is not None and not _is_allowed_realtime_dev_origin(origin, host):
        raise HTTPException(status_code=403, detail="Origin is not allowed for realtime dev endpoints")
    if origin is None and not _is_allowed_realtime_dev_client(client_host):
        raise HTTPException(status_code=403, detail="Origin is not allowed for realtime dev endpoints")

    limit = _current_realtime_client_secret_rate_limit()
    counters: dict[str, int] = app.state.realtime_client_secret_rate_limits
    current_count = counters.get(client_host, 0)
    if current_count >= limit:
        raise HTTPException(status_code=429, detail="Realtime client-secret rate limit exceeded")
    counters[client_host] = current_count + 1


def _is_allowed_realtime_dev_origin(origin: str, host: str | None) -> bool:
    parsed = urlparse(origin)
    origin_host = parsed.hostname
    if origin_host in {"localhost", "127.0.0.1", "::1"}:
        return True
    if host is None:
        return False
    return parsed.netloc == host


def _is_allowed_realtime_dev_client(client_host: str) -> bool:
    return client_host in {"localhost", "127.0.0.1", "::1"}


def _current_realtime_client_secret_rate_limit() -> int:
    configured = os.getenv("VOICEAGENTS_REALTIME_CLIENT_SECRET_RATE_LIMIT")
    if configured is None:
        return DEFAULT_REALTIME_CLIENT_SECRET_RATE_LIMIT
    try:
        return max(1, int(configured))
    except ValueError:
        return DEFAULT_REALTIME_CLIENT_SECRET_RATE_LIMIT


def _current_transcript_logging_mode() -> TranscriptLoggingMode:
    configured = os.getenv(
        "VOICEAGENTS_TRANSCRIPT_LOGGING",
        TranscriptLoggingMode.STRUCTURED.value,
    )
    try:
        return TranscriptLoggingMode(configured)
    except ValueError:
        return TranscriptLoggingMode.STRUCTURED


def _is_transcript_done_event(event_type: NormalizedRealtimeEventType) -> bool:
    return event_type in {
        NormalizedRealtimeEventType.TRANSCRIPT_USER_DONE,
        NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DONE,
    }


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
            model=os.getenv("VOICEAGENTS_OPENAI_REALTIME_MODEL", "gpt-realtime-2"),
            voice=os.getenv("VOICEAGENTS_OPENAI_REALTIME_VOICE", "marin"),
        )
    raise HTTPException(status_code=500, detail=f"Unsupported realtime provider: {provider_name}")


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Malformed Authorization header")
    return token


def _serializable_validation_errors(error: ValidationError) -> list[dict[str, object]]:
    details: list[dict[str, object]] = []
    for item in error.errors():
        detail: dict[str, object] = {
            key: value
            for key, value in item.items()
            if key not in {"ctx", "input", "url"}
        }
        if "ctx" in item and isinstance(item["ctx"], dict):
            detail["ctx"] = {key: str(value) for key, value in item["ctx"].items()}
        details.append(detail)
    return details


def _parse_provider_expiry(expires_at: str | None) -> datetime | None:
    if expires_at is None:
        return None
    normalized = expires_at.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None
