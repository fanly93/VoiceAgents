import json

import pytest

from voiceagents.realtime.dashscope import DashScopeRealtimeAdapter, DashScopeRealtimeConfig
from voiceagents.realtime.dashscope_transport import (
    DashScopeRealtimeTransport,
    DashScopeTransportError,
)
from voiceagents.realtime.outbound import RealtimeOutboundEventKind


class FakeWebSocketClient:
    def __init__(self) -> None:
        self.sent_json: list[object] = []
        self.sent_audio: list[bytes] = []
        self.closed = False
        self.events: list[object] = [{"type": "session.created"}]

    async def send(self, payload: object) -> None:
        if isinstance(payload, bytes):
            self.sent_audio.append(payload)
        else:
            self.sent_json.append(payload)

    async def recv(self) -> object:
        return self.events.pop(0)

    async def close(self) -> None:
        self.closed = True


def make_adapter() -> DashScopeRealtimeAdapter:
    return DashScopeRealtimeAdapter(
        DashScopeRealtimeConfig(
            api_key="dashscope-secret",
            model="qwen-test-realtime",
            voice=None,
            base_url="https://dashscope.aliyuncs.com",
        )
    )


@pytest.mark.anyio
async def test_dashscope_transport_connects_lazily_with_url_and_headers() -> None:
    calls: list[tuple[str, dict[str, str]]] = []
    fake_client = FakeWebSocketClient()

    async def factory(url: str, headers: dict[str, str]) -> FakeWebSocketClient:
        calls.append((url, headers))
        return fake_client

    transport = DashScopeRealtimeTransport(make_adapter(), client_factory=factory)

    assert calls == []
    await transport.connect()

    assert calls == [
        (
            "wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen-test-realtime",
            {"Authorization": "Bearer dashscope-secret"},
        )
    ]


@pytest.mark.anyio
async def test_dashscope_transport_sends_json_audio_receives_and_closes_fake_client() -> None:
    fake_client = FakeWebSocketClient()
    transport = DashScopeRealtimeTransport(
        make_adapter(),
        client_factory=lambda _url, _headers: fake_client,
    )

    await transport.connect()
    await transport.send_json({"type": "session.update"})
    await transport.send_audio(b"pcm16")
    event = await transport.receive()
    await transport.close()

    assert fake_client.sent_json == [json.dumps({"type": "session.update"})]
    assert fake_client.sent_audio == [b"pcm16"]
    assert event.kind is RealtimeOutboundEventKind.JSON
    assert event.payload == {"type": "session.created"}
    assert fake_client.closed is True


@pytest.mark.anyio
async def test_dashscope_transport_serializes_json_for_real_websocket_shape() -> None:
    fake_client = FakeWebSocketClient()
    transport = DashScopeRealtimeTransport(
        make_adapter(),
        client_factory=lambda _url, _headers: fake_client,
    )

    await transport.connect()
    await transport.send_json({"type": "session.update"})
    await transport.close()

    assert fake_client.sent_json == [json.dumps({"type": "session.update"})]


@pytest.mark.anyio
async def test_dashscope_transport_parses_json_string_provider_events() -> None:
    fake_client = FakeWebSocketClient()
    fake_client.events = [json.dumps({"type": "session.created"})]
    transport = DashScopeRealtimeTransport(
        make_adapter(),
        client_factory=lambda _url, _headers: fake_client,
    )

    await transport.connect()
    event = await transport.receive()
    await transport.close()

    assert event.kind is RealtimeOutboundEventKind.JSON
    assert event.payload == {"type": "session.created"}


@pytest.mark.anyio
async def test_dashscope_transport_safe_error_does_not_leak_secret() -> None:
    async def factory(_url: str, _headers: dict[str, str]) -> FakeWebSocketClient:
        raise RuntimeError("Authorization: Bearer dashscope-secret failed")

    transport = DashScopeRealtimeTransport(make_adapter(), client_factory=factory)

    with pytest.raises(DashScopeTransportError) as error:
        await transport.connect()

    assert "dashscope-secret" not in str(error.value)
    assert "Authorization" not in str(error.value)
