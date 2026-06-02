from datetime import datetime, timedelta, timezone

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


def create_dashscope_session_with_transport(transport: object) -> tuple[TestClient, str]:
    store = InMemoryVoiceSessionStore()
    created = store.create_session(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        provider=RealtimeProviderName.DASHSCOPE_REALTIME,
    )
    return (
        TestClient(
            create_app(
                realtime_session_store=store,
                dashscope_upstream_transport=transport,
            )
        ),
        created.tool_call_token,
    )


class FakeDashScopeUpstreamTransport:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def send(self, message: dict[str, object]) -> dict[str, object]:
        self.messages.append(message)
        return {"type": "dashscope.transcript.assistant.delta", "text": "Checking that order."}


def test_realtime_proxy_coordinator_contract_exists() -> None:
    from voiceagents.realtime.proxy import RealtimeProxyCoordinator

    assert RealtimeProxyCoordinator.__name__ == "RealtimeProxyCoordinator"


def test_dashscope_proxy_rejects_missing_token() -> None:
    client, _token = create_dashscope_session()

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/v1/realtime/dashscope/proxy/session-123"):
            pass

    assert error.value.code == 1008


def test_dashscope_proxy_rejects_expired_session_token() -> None:
    store = InMemoryVoiceSessionStore()
    created = store.create_session(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        provider=RealtimeProviderName.DASHSCOPE_REALTIME,
        token_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    client = TestClient(create_app(realtime_session_store=store))

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(
            f"/v1/realtime/dashscope/proxy/session-123?token={created.tool_call_token}"
        ):
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


def test_dashscope_proxy_rejects_non_dashscope_session_token() -> None:
    store = InMemoryVoiceSessionStore()
    created = store.create_session(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        provider=RealtimeProviderName.OPENAI_REALTIME,
    )
    client = TestClient(create_app(realtime_session_store=store))

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(
            f"/v1/realtime/dashscope/proxy/session-123?token={created.tool_call_token}"
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


def test_dashscope_proxy_accepts_allowed_message_envelope() -> None:
    client, token = create_dashscope_session()

    with client.websocket_connect(
        f"/v1/realtime/dashscope/proxy/session-123?token={token}"
    ) as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "control", "payload": {"action": "start"}})

        assert websocket.receive_json() == {
            "type": "dashscope.proxy.accepted",
            "message_type": "control",
        }


def test_dashscope_proxy_rejects_secret_bearing_message_envelope() -> None:
    client, token = create_dashscope_session()

    with client.websocket_connect(
        f"/v1/realtime/dashscope/proxy/session-123?token={token}"
    ) as websocket:
        websocket.receive_json()
        websocket.send_json(
            {
                "type": "control",
                "payload": {"Authorization": "Bearer dashscope-secret"},
            }
        )

        assert websocket.receive_json() == {
            "type": "dashscope.proxy.error",
            "error_code": "invalid_envelope",
        }
        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()

    assert error.value.code == 1008


def test_dashscope_proxy_does_not_touch_upstream_before_auth() -> None:
    transport = FakeDashScopeUpstreamTransport()
    store = InMemoryVoiceSessionStore()
    store.create_session(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        provider=RealtimeProviderName.DASHSCOPE_REALTIME,
    )
    client = TestClient(
        create_app(
            realtime_session_store=store,
            dashscope_upstream_transport=transport,
        )
    )

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/v1/realtime/dashscope/proxy/session-123"):
            pass

    assert transport.messages == []


def test_dashscope_proxy_relays_to_fake_upstream_and_returns_normalized_event() -> None:
    transport = FakeDashScopeUpstreamTransport()
    client, token = create_dashscope_session_with_transport(transport)

    with client.websocket_connect(
        f"/v1/realtime/dashscope/proxy/session-123?token={token}"
    ) as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "control", "payload": {"action": "start"}})
        websocket.receive_json()

        assert websocket.receive_json() == {
            "type": "dashscope.proxy.event",
            "event": {
                "provider": "dashscope_realtime",
                "event_type": "transcript.assistant.delta",
                "state": "speaking",
                "speaker": "assistant",
                "text": "Checking that order.",
            },
        }

    assert transport.messages == [{"type": "control", "payload": {"action": "start"}}]
