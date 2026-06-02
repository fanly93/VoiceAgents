import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from voiceagents.realtime.contracts import (
    RealtimeEventIngestRequest,
    RealtimeProviderName,
)
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
