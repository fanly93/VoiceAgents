from fastapi.testclient import TestClient
import pytest

from voiceagents.api.app import create_app
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


def test_realtime_client_secret_endpoint_rejects_missing_openai_key(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "openai_realtime")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = InMemoryVoiceSessionStore()
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

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
    with pytest.raises(VoiceSessionNotFound):
        store.get_session("session-123")


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
