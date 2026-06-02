from fastapi.testclient import TestClient

from voiceagents.api.app import create_app


def test_dashscope_proxy_route_is_declared_without_credentials() -> None:
    client = TestClient(create_app())

    websocket_paths = {
        route.path
        for route in client.app.routes
        if getattr(route, "path", None) is not None
    }

    assert "/v1/realtime/dashscope/proxy/{session_id}" in websocket_paths
