import base64
import asyncio
from contextlib import suppress
import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from voiceagents.realtime.contracts import (
    RealtimeEventIngestRequest,
    RealtimeProviderName,
    RealtimeToolCallRequest,
    RealtimeToolCallResponse,
    TranscriptLoggingMode,
    VoiceEvent,
    VoiceSessionState,
)
from voiceagents.realtime.outbound import RealtimeOutboundEvent, RealtimeOutboundEventKind
from voiceagents.realtime.event_log import VoiceEventRepository
from voiceagents.realtime.redaction import redact_text
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore, VoiceSessionNotFound
from voiceagents.realtime.tool_router import RealtimeToolRouter


ValidateProxyMessage = Callable[[object], dict[str, object]]
NormalizeProviderEvent = Callable[..., RealtimeEventIngestRequest | RealtimeOutboundEvent]
NormalizeToolCall = Callable[..., RealtimeToolCallRequest]
BuildToolResultMessages = Callable[..., list[Mapping[str, object]]]
UpstreamTransportFactory = Callable[[], object]
MapBrowserMessage = Callable[[Mapping[str, object]], Mapping[str, object] | bytes | None]


@dataclass
class RealtimeProxyCoordinator:
    session_store: InMemoryVoiceSessionStore
    session_id: str
    token: str | None
    provider: RealtimeProviderName
    validate_message: ValidateProxyMessage
    ready_event_type: str
    accepted_event_type: str
    error_event_type: str
    upstream_transport: object | None = None
    upstream_transport_factory: UpstreamTransportFactory | None = None
    map_browser_message: MapBrowserMessage | None = None
    normalize_provider_event: NormalizeProviderEvent | None = None
    event_repository: VoiceEventRepository | None = None
    transcript_logging_mode: TranscriptLoggingMode = TranscriptLoggingMode.STRUCTURED
    tool_router: RealtimeToolRouter | None = None
    normalize_tool_call: NormalizeToolCall | None = None
    build_tool_result_messages: BuildToolResultMessages | None = None
    tool_call_event_types: frozenset[str] = frozenset()
    tool_result_event_type: str = "realtime.proxy.tool_result"

    async def run(self, websocket: WebSocket) -> None:
        if not self._authenticate():
            await websocket.close(code=1008, reason="Invalid realtime proxy token")
            return

        await websocket.accept()
        await websocket.send_json(
            {
                "type": self.ready_event_type,
                "session_id": self.session_id,
            }
        )
        try:
            while True:
                try:
                    message = await websocket.receive_json()
                except WebSocketDisconnect:
                    return
                try:
                    safe_message = self.validate_message(message)
                except ValueError:
                    await websocket.send_json(
                        {
                            "type": self.error_event_type,
                            "error_code": "invalid_envelope",
                        }
                    )
                    await websocket.close(code=1008, reason="Invalid realtime proxy envelope")
                    return

                await websocket.send_json(
                    {
                        "type": self.accepted_event_type,
                        "message_type": safe_message["type"],
                    }
                )
                upstream_transport = await self._get_upstream_transport()
                if upstream_transport is not None and self.normalize_provider_event is not None:
                    if _is_duplex_transport(upstream_transport):
                        await self._run_duplex_proxy(websocket, upstream_transport, safe_message)
                        return
                    provider_message = (
                        self.map_browser_message(safe_message)
                        if self.map_browser_message is not None
                        else safe_message
                    )
                    if provider_message is None:
                        continue
                    provider_event = await _send_upstream(upstream_transport, provider_message)
                    await self._handle_provider_event(
                        websocket,
                        upstream_transport,
                        provider_event,
                    )
        finally:
            if self.upstream_transport is not None:
                await _close_upstream(self.upstream_transport)

    async def _run_duplex_proxy(
        self,
        websocket: WebSocket,
        upstream_transport: object,
        first_message: Mapping[str, object],
    ) -> None:
        upstream_send_lock = asyncio.Lock()
        provider_task = asyncio.create_task(
            self._relay_provider_events(websocket, upstream_transport, upstream_send_lock)
        )
        try:
            await self._send_browser_message_to_upstream(
                upstream_transport,
                first_message,
                upstream_send_lock,
            )
            while True:
                try:
                    message = await websocket.receive_json()
                except WebSocketDisconnect:
                    return
                try:
                    safe_message = self.validate_message(message)
                except ValueError:
                    await websocket.send_json(
                        {
                            "type": self.error_event_type,
                            "error_code": "invalid_envelope",
                        }
                    )
                    await websocket.close(code=1008, reason="Invalid realtime proxy envelope")
                    return
                await websocket.send_json(
                    {
                        "type": self.accepted_event_type,
                        "message_type": safe_message["type"],
                    }
                )
                await self._send_browser_message_to_upstream(
                    upstream_transport,
                    safe_message,
                    upstream_send_lock,
                )
        finally:
            provider_task.cancel()
            with suppress(asyncio.CancelledError):
                await provider_task

    async def _send_browser_message_to_upstream(
        self,
        upstream_transport: object,
        safe_message: Mapping[str, object],
        upstream_send_lock: asyncio.Lock | None = None,
    ) -> None:
        provider_message = (
            self.map_browser_message(safe_message)
            if self.map_browser_message is not None
            else safe_message
        )
        if provider_message is None:
            return
        if upstream_send_lock is None:
            await _send_upstream_message(upstream_transport, provider_message)
            return
        async with upstream_send_lock:
            await _send_upstream_message(upstream_transport, provider_message)

    async def _relay_provider_events(
        self,
        websocket: WebSocket,
        upstream_transport: object,
        upstream_send_lock: asyncio.Lock,
    ) -> None:
        await _connect_upstream(upstream_transport)
        while True:
            provider_event = await _receive_upstream(upstream_transport)
            await self._handle_provider_event(
                websocket,
                upstream_transport,
                provider_event,
                upstream_send_lock,
            )

    async def _handle_provider_event(
        self,
        websocket: WebSocket,
        upstream_transport: object,
        provider_event: Mapping[str, object] | RealtimeOutboundEvent,
        upstream_send_lock: asyncio.Lock | None = None,
    ) -> None:
        if self.normalize_provider_event is None:
            return
        if isinstance(provider_event, RealtimeOutboundEvent):
            await websocket.send_json(_serialize_outbound_event(provider_event))
            return
        session = self.session_store.get_session(self.session_id)
        if self._is_tool_call_event(provider_event):
            tool_response = self._execute_tool_call(provider_event, session)
            provider_call_id = _provider_call_id(provider_event)
            if self.build_tool_result_messages is not None:
                for provider_message in self.build_tool_result_messages(
                    tool_response,
                    provider_call_id=provider_call_id,
                ):
                    if upstream_send_lock is None:
                        await _send_upstream_message(upstream_transport, provider_message)
                    else:
                        async with upstream_send_lock:
                            await _send_upstream_message(upstream_transport, provider_message)
            await websocket.send_json(
                {
                    "type": self.tool_result_event_type,
                    "tool_name": tool_response.tool_name,
                    "tool_status": tool_response.tool_status.value,
                }
            )
            return
        normalized_event = self.normalize_provider_event(
            provider_event,
            session_id=self.session_id,
            call_id=session.call_id,
            merchant_id=session.merchant_id,
        )
        if isinstance(normalized_event, RealtimeOutboundEvent):
            await websocket.send_json(_serialize_outbound_event(normalized_event))
            return
        if self.event_repository is not None:
            _persist_normalized_event(
                normalized_event,
                session_store=self.session_store,
                event_repository=self.event_repository,
                transcript_logging_mode=self.transcript_logging_mode,
            )
        await websocket.send_json(
            {
                "type": "dashscope.proxy.event",
                "event": _serialize_normalized_event(normalized_event),
            }
        )

    def _authenticate(self) -> bool:
        if self.token is None:
            return False
        try:
            provider_name = self.session_store.get_session_provider(self.session_id)
            token_is_valid = self.session_store.verify_tool_call_token(self.session_id, self.token)
        except VoiceSessionNotFound:
            return False
        return provider_name is self.provider and token_is_valid

    async def _get_upstream_transport(self) -> object | None:
        if self.upstream_transport is not None:
            return self.upstream_transport
        if self.upstream_transport_factory is None:
            return None
        result = self.upstream_transport_factory()
        if inspect.isawaitable(result):
            result = await result
        self.upstream_transport = result
        return result

    def _is_tool_call_event(self, provider_event: Mapping[str, object]) -> bool:
        provider_event_type = provider_event.get("type")
        return isinstance(provider_event_type, str) and provider_event_type in self.tool_call_event_types

    def _execute_tool_call(
        self,
        provider_event: Mapping[str, object],
        session,
    ) -> RealtimeToolCallResponse:
        if self.tool_router is None or self.normalize_tool_call is None or self.token is None:
            raise RuntimeError("Realtime proxy tool routing is not configured")
        request = self.normalize_tool_call(
            provider_event,
            session_id=self.session_id,
            call_id=session.call_id,
            merchant_id=session.merchant_id,
        )
        response = self.tool_router.execute(
            request,
            tool_call_token=self.token,
            provider=self.provider,
        )
        self.session_store.append_tool_call(
            request.session_id,
            request.tool_name,
            response.safe_summary,
        )
        if self.event_repository is not None:
            self.event_repository.append(
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
                    provider=self.provider,
                    provider_event_type=str(provider_event.get("type")),
                    provider_call_id=_provider_call_id(provider_event),
                    tool_status=response.tool_status.value,
                    redaction_applied=False,
                )
            )
        return response


def _is_duplex_transport(transport: object) -> bool:
    return callable(getattr(transport, "send_json", None)) and callable(
        getattr(transport, "receive", None)
    )


async def _send_upstream(
    transport: object,
    message: Mapping[str, object],
) -> dict[str, object]:
    await _connect_upstream(transport)
    sender = getattr(transport, "send", None)
    if sender is None:
        raise RuntimeError("Realtime upstream transport must define send")
    result = sender(dict(message))
    if inspect.isawaitable(result):
        result = await result
    if not isinstance(result, dict):
        raise RuntimeError("Realtime upstream transport returned invalid event")
    return result


async def _send_upstream_message(
    transport: object,
    message: Mapping[str, object] | bytes,
) -> None:
    await _connect_upstream(transport)
    if isinstance(message, bytes):
        sender = getattr(transport, "send_audio", None)
        if sender is None:
            raise RuntimeError("Realtime upstream transport must define send_audio")
        result = sender(message)
    else:
        sender = getattr(transport, "send_json", None) or getattr(transport, "send", None)
        if sender is None:
            raise RuntimeError("Realtime upstream transport must define send_json")
        result = sender(dict(message))
    if inspect.isawaitable(result):
        await result


async def _receive_upstream(transport: object) -> Mapping[str, object] | RealtimeOutboundEvent:
    receiver = getattr(transport, "receive", None)
    if receiver is None:
        raise RuntimeError("Realtime upstream transport must define receive")
    result = receiver()
    if inspect.isawaitable(result):
        result = await result
    if isinstance(result, RealtimeOutboundEvent):
        if result.kind is RealtimeOutboundEventKind.JSON and result.payload is not None:
            return result.payload
        return result
    if not isinstance(result, dict):
        raise RuntimeError("Realtime upstream transport returned invalid event")
    return result


async def _connect_upstream(transport: object) -> None:
    connector = getattr(transport, "connect", None)
    if connector is None:
        return
    result = connector()
    if inspect.isawaitable(result):
        await result


async def _close_upstream(transport: object) -> None:
    closer = getattr(transport, "close", None)
    if closer is None:
        return
    result = closer()
    if inspect.isawaitable(result):
        await result


def _serialize_normalized_event(event: RealtimeEventIngestRequest) -> dict[str, object]:
    return {
        "provider": event.provider.value,
        "event_type": event.event_type.value,
        "state": event.state.value,
        "speaker": event.speaker,
        "text": event.text,
    }


def _serialize_outbound_event(event: RealtimeOutboundEvent) -> dict[str, object]:
    if event.kind is RealtimeOutboundEventKind.AUDIO and event.audio is not None:
        return {
            "type": "dashscope.proxy.audio",
            "audio": base64.b64encode(event.audio).decode("ascii"),
        }
    if event.kind is RealtimeOutboundEventKind.ERROR and event.safe_error is not None:
        return {
            "type": "dashscope.proxy.error",
            "error_code": event.safe_error.code,
            "safe_summary": event.safe_error.safe_summary,
        }
    if event.kind is RealtimeOutboundEventKind.CLOSE and event.close_code is not None:
        return {
            "type": "dashscope.proxy.close",
            "close_code": event.close_code,
        }
    return {
        "type": "dashscope.proxy.error",
        "error_code": "invalid_outbound_event",
    }


def _provider_call_id(provider_event: Mapping[str, object]) -> str:
    for field_name in ("call_id", "tool_call_id"):
        value = provider_event.get(field_name)
        if isinstance(value, str) and value:
            return value
    raise RuntimeError("Provider tool call event is missing call id")


def _persist_normalized_event(
    event: RealtimeEventIngestRequest,
    *,
    session_store: InMemoryVoiceSessionStore,
    event_repository: VoiceEventRepository,
    transcript_logging_mode: TranscriptLoggingMode,
) -> None:
    text_redaction = redact_text(event.text) if event.text is not None else None
    summary_redaction = (
        redact_text(event.safe_summary) if event.safe_summary is not None else None
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
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=event.session_id,
            call_id=event.call_id,
            merchant_id=event.merchant_id,
            state=event.state,
            event_type=event.event_type.value,
            transcript_text_redacted=structured_text if event.speaker == "user" else None,
            response_text_redacted=structured_text if event.speaker == "assistant" else None,
            tool_name=event.tool_name,
            tool_arguments_redacted=None,
            tool_result_summary=redacted_summary,
            handoff_reason=None,
            latency_ms=event.latency_ms,
            provider=event.provider,
            provider_event_type=event.provider_event_type,
            provider_call_id=event.provider_call_id,
            tool_status=event.tool_status,
            redaction_applied=redaction_applied,
        )
    )
    if (
        redacted_text is not None
        and event.speaker is not None
        and transcript_logging_mode is not TranscriptLoggingMode.OFF
    ):
        session_store.append_transcript(event.session_id, event.speaker, redacted_text)
    session_store.update_state(event.session_id, event.state)
