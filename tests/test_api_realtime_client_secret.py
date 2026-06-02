from fastapi.testclient import TestClient
import pytest

import voiceagents.api.app as api_app
from voiceagents.api.app import create_app
from voiceagents.realtime.contracts import (
    RealtimeClientSecretResponse,
    RealtimeConnectionMode,
    RealtimeProviderName,
    build_default_realtime_session_config,
)
from voiceagents.realtime.event_log import InMemoryVoiceEventRepository
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore, VoiceSessionNotFound


def test_realtime_client_secret_endpoint_returns_mock_credentials(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    event_repository = InMemoryVoiceEventRepository()
    client = TestClient(
        create_app(
            realtime_session_store=InMemoryVoiceSessionStore(),
            realtime_event_repository=event_repository,
        )
    )

    response = client.post(
        "/v1/realtime/client-secret",
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "response_mode": "text",
            "locale": "en-US",
            "safety_subject_id": "subject_hash_123",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["client_secret"].startswith("mock-client-secret")
    assert body["tool_call_token"]
    assert body["model"] == "mock-realtime"
    assert {tool["name"] for tool in body["session_config"]["tools"]} == {
        "lookup_order",
        "lookup_logistics",
        "query_product_knowledge",
        "handoff_to_human",
    }
    assert "OPENAI_API_KEY" not in str(body)
    assert len(event_repository.events) == 1
    assert event_repository.events[0].event_type == "session_created"


def test_realtime_client_secret_endpoint_blocks_real_provider_without_dev_gate(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "openai_realtime")
    monkeypatch.delenv("VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    store = InMemoryVoiceSessionStore()

    def fail_if_provider_is_built(provider_name: RealtimeProviderName) -> object:
        raise AssertionError(f"provider should not be built while gated: {provider_name}")

    monkeypatch.setattr(api_app, "_build_realtime_provider", fail_if_provider_is_built)
    client = TestClient(create_app(realtime_session_store=store))

    response = client.post(
        "/v1/realtime/client-secret",
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "response_mode": "text",
            "locale": "en-US",
        },
    )

    assert response.status_code == 403
    assert "realtime dev endpoints" in response.json()["detail"]
    with pytest.raises(VoiceSessionNotFound):
        store.get_session("session-123")


def test_realtime_client_secret_endpoint_blocks_dashscope_without_dev_gate(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "dashscope_realtime")
    monkeypatch.delenv("VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS", raising=False)
    monkeypatch.setenv("VOICEAGENTS_DASHSCOPE_API_KEY", "dashscope-secret")
    store = InMemoryVoiceSessionStore()

    def fail_if_provider_is_built(provider_name: RealtimeProviderName) -> object:
        raise AssertionError(f"provider should not be built while gated: {provider_name}")

    monkeypatch.setattr(api_app, "_build_realtime_provider", fail_if_provider_is_built)
    client = TestClient(create_app(realtime_session_store=store))

    response = client.post(
        "/v1/realtime/client-secret",
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "response_mode": "voice",
            "locale": "zh-CN",
        },
    )

    assert response.status_code == 403
    assert "realtime dev endpoints" in response.json()["detail"]
    with pytest.raises(VoiceSessionNotFound):
        store.get_session("session-123")


def test_realtime_client_secret_endpoint_rejects_disallowed_real_provider_origin(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "openai_realtime")
    monkeypatch.setenv("VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    store = InMemoryVoiceSessionStore()

    def fail_if_provider_is_built(provider_name: RealtimeProviderName) -> object:
        raise AssertionError(f"provider should not be built for bad origin: {provider_name}")

    monkeypatch.setattr(api_app, "_build_realtime_provider", fail_if_provider_is_built)
    client = TestClient(create_app(realtime_session_store=store))

    response = client.post(
        "/v1/realtime/client-secret",
        headers={"Origin": "https://evil.example"},
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "response_mode": "text",
            "locale": "en-US",
        },
    )

    assert response.status_code == 403
    assert "origin" in response.json()["detail"].lower()
    with pytest.raises(VoiceSessionNotFound):
        store.get_session("session-123")


def test_realtime_client_secret_endpoint_rejects_non_local_request_without_origin(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "openai_realtime")
    monkeypatch.setenv("VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    store = InMemoryVoiceSessionStore()

    def fail_if_provider_is_built(provider_name: RealtimeProviderName) -> object:
        raise AssertionError(f"provider should not be built without a local origin: {provider_name}")

    monkeypatch.setattr(api_app, "_build_realtime_provider", fail_if_provider_is_built)
    client = TestClient(create_app(realtime_session_store=store))

    response = client.post(
        "/v1/realtime/client-secret",
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "response_mode": "text",
            "locale": "en-US",
        },
    )

    assert response.status_code == 403
    assert "origin" in response.json()["detail"].lower()
    with pytest.raises(VoiceSessionNotFound):
        store.get_session("session-123")


def test_realtime_client_secret_endpoint_rate_limits_real_provider_minting(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "openai_realtime")
    monkeypatch.setenv("VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS", "true")
    monkeypatch.setenv("VOICEAGENTS_REALTIME_CLIENT_SECRET_RATE_LIMIT", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class FakeProvider:
        def create_client_secret(self, request):
            return RealtimeClientSecretResponse(
                provider=RealtimeProviderName.OPENAI_REALTIME,
                session_id=request.session_id,
                call_id=request.call_id,
                    client_secret="ephemeral-secret",
                    tool_call_token="provider-token-overwritten-by-app",
                    connection_url="https://api.openai.com/v1/realtime/calls",
                    connection_mode=RealtimeConnectionMode.BROWSER_WEBRTC_EPHEMERAL,
                    ephemeral_credential="ephemeral-secret",
                    expires_at=None,
                    credential_expires_at=None,
                    model="gpt-realtime-2",
                voice="marin",
                session_config=build_default_realtime_session_config(),
            )

    monkeypatch.setattr(api_app, "_build_realtime_provider", lambda provider_name: FakeProvider())
    client = TestClient(create_app(realtime_session_store=InMemoryVoiceSessionStore()))

    first = client.post(
        "/v1/realtime/client-secret",
        headers={"Origin": "http://127.0.0.1:8000"},
        json={
            "session_id": "session-1",
            "call_id": "call-1",
            "merchant_id": "merchant-123",
            "response_mode": "text",
            "locale": "en-US",
        },
    )
    second = client.post(
        "/v1/realtime/client-secret",
        headers={"Origin": "http://127.0.0.1:8000"},
        json={
            "session_id": "session-2",
            "call_id": "call-2",
            "merchant_id": "merchant-123",
            "response_mode": "text",
            "locale": "en-US",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 429


def test_realtime_client_secret_endpoint_rejects_missing_openai_key(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "openai_realtime")
    monkeypatch.setenv("VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = InMemoryVoiceSessionStore()
    client = TestClient(create_app(realtime_session_store=store))

    response = client.post(
        "/v1/realtime/client-secret",
        headers={"Origin": "http://127.0.0.1:8000"},
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "response_mode": "text",
            "locale": "en-US",
        },
    )

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
    with pytest.raises(VoiceSessionNotFound):
        store.get_session("session-123")


def test_realtime_client_secret_endpoint_returns_dashscope_proxy_metadata(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "dashscope_realtime")
    monkeypatch.setenv("VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS", "true")
    monkeypatch.setenv("VOICEAGENTS_DASHSCOPE_API_KEY", "dashscope-secret")
    monkeypatch.setenv("VOICEAGENTS_DASHSCOPE_REALTIME_MODEL", "qwen3.5-omni-flash-realtime")
    store = InMemoryVoiceSessionStore()
    client = TestClient(create_app(realtime_session_store=store))

    response = client.post(
        "/v1/realtime/client-secret",
        headers={"Origin": "http://127.0.0.1:8000"},
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "response_mode": "voice",
            "locale": "zh-CN",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "dashscope_realtime"
    assert body["connection_mode"] == "server_websocket_proxy"
    assert body["connection_url"] == "/v1/realtime/dashscope/proxy/session-123"
    assert body["model"] == "qwen3.5-omni-flash-realtime"
    assert body["client_secret"] is None
    assert body["ephemeral_credential"] is None
    assert body["tool_call_token"]
    assert store.get_session_provider("session-123") is RealtimeProviderName.DASHSCOPE_REALTIME
    assert "dashscope-secret" not in response.text
    assert "DASHSCOPE_API_KEY" not in response.text


def test_realtime_client_secret_endpoint_rejects_raw_safety_subject_id(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    client = TestClient(create_app())

    response = client.post(
        "/v1/realtime/client-secret",
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "response_mode": "text",
            "locale": "en-US",
            "safety_subject_id": "customer@example.com",
        },
    )

    assert response.status_code == 422
