import inspect
from collections.abc import Awaitable, Callable, Mapping

from voiceagents.realtime.dashscope import DashScopeRealtimeAdapter
from voiceagents.realtime.outbound import (
    RealtimeOutboundEvent,
    RealtimeOutboundEventKind,
    RealtimeSafeProviderError,
)


class DashScopeTransportError(RuntimeError):
    pass


DashScopeClientFactory = Callable[[str, dict[str, str]], object | Awaitable[object]]


class DashScopeRealtimeTransport:
    def __init__(
        self,
        adapter: DashScopeRealtimeAdapter,
        *,
        client_factory: DashScopeClientFactory | None = None,
    ) -> None:
        self._adapter = adapter
        self._client_factory = client_factory or _default_client_factory
        self._client: object | None = None

    async def connect(self) -> None:
        if self._client is not None:
            return
        try:
            result = self._client_factory(
                self._adapter.build_connection_url(),
                dict(self._adapter.build_headers()),
            )
            if inspect.isawaitable(result):
                result = await result
        except Exception as error:
            raise DashScopeTransportError(_safe_transport_error(error)) from error
        self._client = result

    async def send_json(self, payload: Mapping[str, object]) -> None:
        client = self._require_client()
        await _call_client_method(client, "send", dict(payload))

    async def send_audio(self, audio: bytes) -> None:
        client = self._require_client()
        await _call_client_method(client, "send", audio)

    async def receive(self) -> RealtimeOutboundEvent:
        client = self._require_client()
        payload = await _call_client_method(client, "recv")
        if isinstance(payload, bytes):
            return RealtimeOutboundEvent(kind=RealtimeOutboundEventKind.AUDIO, audio=payload)
        if isinstance(payload, dict):
            return RealtimeOutboundEvent(kind=RealtimeOutboundEventKind.JSON, payload=payload)
        return RealtimeOutboundEvent(
            kind=RealtimeOutboundEventKind.ERROR,
            safe_error=RealtimeSafeProviderError(
                code="invalid_provider_event",
                safe_summary="DashScope returned an unsupported outbound event shape",
            ),
        )

    async def close(self) -> None:
        if self._client is None:
            return
        await _call_client_method(self._client, "close")
        self._client = None

    async def send(self, payload: Mapping[str, object]) -> dict[str, object]:
        await self.send_json(payload)
        event = await self.receive()
        if event.kind is RealtimeOutboundEventKind.JSON and event.payload is not None:
            return event.payload
        raise DashScopeTransportError("DashScope transport did not return a JSON provider event")

    def _require_client(self) -> object:
        if self._client is None:
            raise DashScopeTransportError("DashScope transport is not connected")
        return self._client


async def _default_client_factory(url: str, headers: dict[str, str]) -> object:
    try:
        import websockets
    except ImportError as error:
        raise DashScopeTransportError(
            "DashScope outbound WebSocket dependency is not installed"
        ) from error
    return await websockets.connect(url, additional_headers=headers)


async def _call_client_method(client: object, name: str, *args: object) -> object:
    method = getattr(client, name, None)
    if method is None:
        raise DashScopeTransportError(f"DashScope WebSocket client does not define {name}")
    try:
        result = method(*args)
        if inspect.isawaitable(result):
            return await result
        return result
    except Exception as error:
        raise DashScopeTransportError(_safe_transport_error(error)) from error


def _safe_transport_error(error: Exception) -> str:
    message = str(error)
    unsafe_markers = ("authorization", "bearer", "api_key", "dashscope-secret")
    if any(marker in message.lower() for marker in unsafe_markers):
        return "DashScope outbound transport failed"
    return message or "DashScope outbound transport failed"
