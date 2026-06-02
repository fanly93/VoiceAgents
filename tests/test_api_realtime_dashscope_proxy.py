from fastapi.testclient import TestClient
import pytest
from starlette.websockets import WebSocketDisconnect

from voiceagents.api.app import create_app
from voiceagents.realtime.contracts import RealtimeProviderName
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore


def test_dashscope_proxy_route_is_declared_without_credentials() -> None:
    client = TestClient(create_app())

    websocket_paths = {
        route.path
        for route in client.app.routes
        if getattr(route, "path", None) is not None
    }

    assert "/v1/realtime/dashscope/proxy/{session_id}" in websocket_paths


def create_dashscope_session() -> tuple[TestClient, str]:
    store = InMemoryVoiceSessionStore()
    created = store.create_session(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        provider=RealtimeProviderName.DASHSCOPE_REALTIME,
    )
    return TestClient(create_app(realtime_session_store=store)), created.tool_call_token


def test_dashscope_proxy_rejects_missing_token() -> None:
    client, _token = create_dashscope_session()

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/v1/realtime/dashscope/proxy/session-123"):
            pass

    assert error.value.code == 1008


def test_dashscope_proxy_rejects_wrong_session_token() -> None:
    client, token = create_dashscope_session()

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(
            f"/v1/realtime/dashscope/proxy/session-other?token={token}"
        ):
            pass

    assert error.value.code == 1008


def test_dashscope_proxy_accepts_valid_session_token() -> None:
    client, token = create_dashscope_session()

    with client.websocket_connect(
        f"/v1/realtime/dashscope/proxy/session-123?token={token}"
    ) as websocket:
        assert websocket.receive_json() == {
            "type": "dashscope.proxy.ready",
            "session_id": "session-123",
        }
