from fastapi.testclient import TestClient
import json

from voiceagents.api.app import create_app
from voiceagents.realtime.contracts import RealtimeProviderName
from voiceagents.realtime.event_log import InMemoryVoiceEventRepository, JsonlVoiceEventRepository
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore


def make_client() -> tuple[TestClient, InMemoryVoiceEventRepository]:
    event_repository = InMemoryVoiceEventRepository()
    client = TestClient(
        create_app(
            realtime_session_store=InMemoryVoiceSessionStore(),
            realtime_event_repository=event_repository,
        )
    )
    return client, event_repository


def create_session_and_token(client: TestClient) -> str:
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
    assert response.status_code == 200
    return response.json()["tool_call_token"]


def test_realtime_tool_call_endpoint_routes_known_tool(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    client, event_repository = make_client()
    token = create_session_and_token(client)

    response = client.post(
        "/v1/realtime/tool-call",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "tool_name": "lookup_order",
            "arguments": {"order_id": "ORDER-REDACTED-001"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["tool_name"] == "lookup_order"
    assert body["result"] == {"order_status": "paid"}
    assert event_repository.events[-1].event_type == "tool_call"
    assert event_repository.events[-1].tool_result_summary == "Order ORDER-REDACTED-001 has been paid."
    assert event_repository.events[-1].tool_arguments_redacted is None


def test_realtime_tool_call_endpoint_does_not_persist_raw_arguments(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    path = tmp_path / "events" / "realtime-events.jsonl"
    client = TestClient(
        create_app(
            realtime_session_store=InMemoryVoiceSessionStore(),
            realtime_event_repository=JsonlVoiceEventRepository(path),
        )
    )
    token = create_session_and_token(client)

    response = client.post(
        "/v1/realtime/tool-call",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "tool_name": "query_product_knowledge",
            "arguments": {"query": "My private hair routine is weekly leave-in conditioner."},
        },
    )

    assert response.status_code == 200
    file_content = path.read_text(encoding="utf-8")
    payload = json.loads(file_content.splitlines()[-1])
    assert payload["tool_arguments_redacted"] is None
    assert "private hair routine" not in file_content
    assert "weekly leave-in conditioner" not in file_content


def test_realtime_tool_call_endpoint_rejects_missing_authorization(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    client, _event_repository = make_client()
    create_session_and_token(client)

    response = client.post(
        "/v1/realtime/tool-call",
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "tool_name": "lookup_order",
            "arguments": {"order_id": "ORDER-REDACTED-001"},
        },
    )

    assert response.status_code == 401


def test_realtime_tool_call_endpoint_rejects_invalid_token(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    client, _event_repository = make_client()
    create_session_and_token(client)

    response = client.post(
        "/v1/realtime/tool-call",
        headers={"Authorization": "Bearer wrong-token"},
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "tool_name": "lookup_order",
            "arguments": {"order_id": "ORDER-REDACTED-001"},
        },
    )

    assert response.status_code == 403


def test_realtime_tool_call_endpoint_rejects_session_binding_mismatch(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    client, _event_repository = make_client()
    token = create_session_and_token(client)

    for field, value in (
        ("call_id", "call-other"),
        ("merchant_id", "merchant-other"),
    ):
        response = client.post(
            "/v1/realtime/tool-call",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "session_id": "session-123",
                "call_id": "call-123",
                "merchant_id": "merchant-123",
                "tool_name": "lookup_order",
                "arguments": {"order_id": "ORDER-REDACTED-001"},
                field: value,
            },
        )

        assert response.status_code == 403


def test_realtime_tool_call_endpoint_rejects_provider_binding_mismatch(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    store = InMemoryVoiceSessionStore()
    created = store.create_session(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        provider=RealtimeProviderName.OPENAI_REALTIME,
    )
    client = TestClient(create_app(realtime_session_store=store))

    response = client.post(
        "/v1/realtime/tool-call",
        headers={"Authorization": f"Bearer {created.tool_call_token}"},
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "tool_name": "lookup_order",
            "arguments": {"order_id": "ORDER-REDACTED-001"},
        },
    )

    assert response.status_code == 403


def test_realtime_tool_call_endpoint_rejects_unknown_tool(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    client, _event_repository = make_client()
    token = create_session_and_token(client)

    response = client.post(
        "/v1/realtime/tool-call",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "tool_name": "run_shell",
            "arguments": {},
        },
    )

    assert response.status_code == 400


def test_realtime_tool_call_endpoint_rejects_invalid_arguments(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    client, _event_repository = make_client()
    token = create_session_and_token(client)

    response = client.post(
        "/v1/realtime/tool-call",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "tool_name": "lookup_order",
            "arguments": {"order_id": ""},
        },
    )

    assert response.status_code == 422


def test_realtime_tool_call_endpoint_handoff_updates_state(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    store = InMemoryVoiceSessionStore()
    event_repository = InMemoryVoiceEventRepository()
    client = TestClient(
        create_app(
            realtime_session_store=store,
            realtime_event_repository=event_repository,
        )
    )
    token = create_session_and_token(client)

    response = client.post(
        "/v1/realtime/tool-call",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "tool_name": "handoff_to_human",
            "arguments": {
                "reason": "customer_requests_human",
                "summary": "Customer asked for a person.",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["handoff_required"] is True
    assert store.get_session("session-123").state == "handoff_pending"
