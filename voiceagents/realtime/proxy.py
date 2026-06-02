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
    TranscriptLoggingMode,
    VoiceEvent,
)
from voiceagents.realtime.event_log import VoiceEventRepository
from voiceagents.realtime.redaction import redact_text
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore, VoiceSessionNotFound


ValidateProxyMessage = Callable[[object], dict[str, object]]
NormalizeProviderEvent = Callable[..., RealtimeEventIngestRequest]


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
    normalize_provider_event: NormalizeProviderEvent | None = None
    event_repository: VoiceEventRepository | None = None
    transcript_logging_mode: TranscriptLoggingMode = TranscriptLoggingMode.STRUCTURED

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
            if self.upstream_transport is not None and self.normalize_provider_event is not None:
                provider_event = await _send_upstream(self.upstream_transport, safe_message)
                session = self.session_store.get_session(self.session_id)
                normalized_event = self.normalize_provider_event(
                    provider_event,
                    session_id=self.session_id,
                    call_id=session.call_id,
                    merchant_id=session.merchant_id,
                )
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


async def _send_upstream(
    transport: object,
    message: Mapping[str, object],
) -> dict[str, object]:
    sender = getattr(transport, "send", None)
    if sender is None:
        raise RuntimeError("Realtime upstream transport must define send")
    result = sender(dict(message))
    if inspect.isawaitable(result):
        result = await result
    if not isinstance(result, dict):
        raise RuntimeError("Realtime upstream transport returned invalid event")
    return result


def _serialize_normalized_event(event: RealtimeEventIngestRequest) -> dict[str, object]:
    return {
        "provider": event.provider.value,
        "event_type": event.event_type.value,
        "state": event.state.value,
        "speaker": event.speaker,
        "text": event.text,
    }


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
