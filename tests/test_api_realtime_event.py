import json

from fastapi.testclient import TestClient

from voiceagents.api.app import create_app
from voiceagents.realtime.event_log import (
    InMemoryRealtimeTranscriptRepository,
    InMemoryVoiceEventRepository,
    JsonlVoiceEventRepository,
)
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore


def make_client(
    *,
    transcript_repository: InMemoryRealtimeTranscriptRepository | None = None,
    event_repository: InMemoryVoiceEventRepository | None = None,
) -> tuple[TestClient, InMemoryVoiceEventRepository]:
    event_repository = event_repository or InMemoryVoiceEventRepository()
    kwargs = {}
    if transcript_repository is not None:
        kwargs["realtime_transcript_repository"] = transcript_repository

    client = TestClient(
        create_app(
            realtime_session_store=InMemoryVoiceSessionStore(),
            realtime_event_repository=event_repository,
            **kwargs,
        )
    )
    return client, event_repository


def make_client_with_jsonl_event_repository(
    event_repository: JsonlVoiceEventRepository,
) -> TestClient:
    return TestClient(
        create_app(
            realtime_session_store=InMemoryVoiceSessionStore(),
            realtime_event_repository=event_repository,
        )
    )


def make_client_with_transcript_repository(
    transcript_repository: InMemoryRealtimeTranscriptRepository,
) -> tuple[TestClient, InMemoryVoiceEventRepository]:
    event_repository = InMemoryVoiceEventRepository()
    client = TestClient(
        create_app(
            realtime_session_store=InMemoryVoiceSessionStore(),
            realtime_event_repository=event_repository,
            realtime_transcript_repository=transcript_repository,
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


def make_transcript_event_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "session_id": "session-123",
        "call_id": "call-123",
        "merchant_id": "merchant-123",
        "provider": "mock",
        "event_type": "transcript.user.delta",
        "state": "transcribing",
        "speaker": "user",
        "turn_id": "turn-123",
        "sequence": 1,
        "text": "Where is ORDER-123456?",
        "provider_event_type": "conversation.item.input_audio_transcription.delta",
        "latency_ms": 120,
    }
    payload.update(updates)
    return payload


def test_realtime_event_endpoint_accepts_authenticated_event() -> None:
    client, event_repository = make_client()
    token = create_session_and_token(client)

    response = client.post(
        "/v1/realtime/event",
        headers={"Authorization": f"Bearer {token}"},
        json=make_transcript_event_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["event_id"]
    assert body["redaction_applied"] is True
    assert event_repository.events[-1].event_type == "transcript.user.delta"


def test_realtime_event_endpoint_rejects_missing_and_malformed_authorization() -> None:
    client, _event_repository = make_client()
    create_session_and_token(client)

    missing = client.post("/v1/realtime/event", json=make_transcript_event_payload())
    malformed = client.post(
        "/v1/realtime/event",
        headers={"Authorization": "Token wrong"},
        json=make_transcript_event_payload(),
    )

    assert missing.status_code == 401
    assert malformed.status_code == 401


def test_realtime_event_endpoint_checks_authorization_before_payload_validation() -> None:
    client, _event_repository = make_client()
    create_session_and_token(client)

    response = client.post(
        "/v1/realtime/event",
        json=make_transcript_event_payload(raw_audio="base64-audio"),
    )

    assert response.status_code == 401


def test_realtime_event_endpoint_rejects_invalid_token() -> None:
    client, _event_repository = make_client()
    create_session_and_token(client)

    response = client.post(
        "/v1/realtime/event",
        headers={"Authorization": "Bearer wrong-token"},
        json=make_transcript_event_payload(),
    )

    assert response.status_code == 403


def test_realtime_event_endpoint_rejects_session_binding_mismatch() -> None:
    client, _event_repository = make_client()
    token = create_session_and_token(client)

    for field, value in (
        ("call_id", "call-other"),
        ("merchant_id", "merchant-other"),
        ("provider", "openai_realtime"),
    ):
        response = client.post(
            "/v1/realtime/event",
            headers={"Authorization": f"Bearer {token}"},
            json=make_transcript_event_payload(**{field: value}),
        )

        assert response.status_code == 403


def test_realtime_event_endpoint_rejects_blocked_event_keys() -> None:
    client, event_repository = make_client()
    token = create_session_and_token(client)

    for blocked_payload in (
        make_transcript_event_payload(raw_audio="base64-audio"),
        make_transcript_event_payload(metadata={"sdp": "v=0"}),
        make_transcript_event_payload(client_secret="ephemeral-secret"),
    ):
        response = client.post(
            "/v1/realtime/event",
            headers={"Authorization": f"Bearer {token}"},
            json=blocked_payload,
        )

        assert response.status_code == 422

    assert event_repository.events[-1].event_type == "session_created"


def test_realtime_event_endpoint_rejects_nested_blocked_keys_before_validation() -> None:
    client, event_repository = make_client()
    token = create_session_and_token(client)
    payload = make_transcript_event_payload(metadata={"sdp": "v=0"})
    payload.pop("text")

    response = client.post(
        "/v1/realtime/event",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 422
    assert "sdp" in response.json()["detail"]
    assert event_repository.events[-1].event_type == "session_created"


def test_realtime_event_endpoint_returns_serializable_422_for_validation_errors() -> None:
    client, event_repository = make_client()
    token = create_session_and_token(client)

    response = client.post(
        "/v1/realtime/event",
        headers={"Authorization": f"Bearer {token}"},
        json=make_transcript_event_payload(
            event_type="session.error",
            state="error",
            speaker=None,
            turn_id=None,
            sequence=None,
            text=None,
            safe_summary="Provider error should not be accepted on session events.",
        ),
    )

    assert response.status_code == 422
    assert "safe_summary" in response.text
    assert event_repository.events[-1].event_type == "session_created"


def test_realtime_event_endpoint_uses_structured_transcript_logging_by_default(
    monkeypatch,
) -> None:
    monkeypatch.delenv("VOICEAGENTS_TRANSCRIPT_LOGGING", raising=False)
    transcript_repository = InMemoryRealtimeTranscriptRepository()
    client, event_repository = make_client_with_transcript_repository(transcript_repository)
    token = create_session_and_token(client)

    response = client.post(
        "/v1/realtime/event",
        headers={"Authorization": f"Bearer {token}"},
        json=make_transcript_event_payload(
            event_type="transcript.user.done",
            text="Email customer@example.com about ORDER-123456.",
        ),
    )

    assert response.status_code == 200
    assert transcript_repository.events == []
    assert event_repository.events[-1].transcript_text_redacted == (
        "Email [EMAIL_REDACTED] about [ORDER_REDACTED]."
    )


def test_realtime_event_endpoint_respects_transcript_logging_modes(monkeypatch) -> None:
    for mode, expected_structured_text, expected_transcript_count in (
        ("off", None, 0),
        ("structured", "Where is [ORDER_REDACTED]?", 0),
        ("transcript", "Where is [ORDER_REDACTED]?", 1),
    ):
        monkeypatch.setenv("VOICEAGENTS_TRANSCRIPT_LOGGING", mode)
        transcript_repository = InMemoryRealtimeTranscriptRepository()
        client, event_repository = make_client_with_transcript_repository(transcript_repository)
        token = create_session_and_token(client)

        response = client.post(
            "/v1/realtime/event",
            headers={"Authorization": f"Bearer {token}"},
            json=make_transcript_event_payload(
                event_type="transcript.user.done",
                text="Where is ORDER-123456?",
            ),
        )

        assert response.status_code == 200
        assert event_repository.events[-1].transcript_text_redacted == expected_structured_text
        assert len(transcript_repository.events) == expected_transcript_count


def test_realtime_event_endpoint_writes_transcript_done_events(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_TRANSCRIPT_LOGGING", "transcript")
    transcript_repository = InMemoryRealtimeTranscriptRepository()
    client, _event_repository = make_client_with_transcript_repository(transcript_repository)
    token = create_session_and_token(client)

    for event_type, speaker in (
        ("transcript.user.done", "user"),
        ("transcript.assistant.done", "assistant"),
    ):
        response = client.post(
            "/v1/realtime/event",
            headers={"Authorization": f"Bearer {token}"},
            json=make_transcript_event_payload(
                event_type=event_type,
                speaker=speaker,
                text="Email customer@example.com about ORDER-123456.",
            ),
        )

        assert response.status_code == 200

    assert [event.speaker for event in transcript_repository.events] == ["user", "assistant"]
    assert {event.event_type for event in transcript_repository.events} == {"transcript_done"}
    assert transcript_repository.events[0].turn_id == "turn-123"
    assert transcript_repository.events[0].sequence == 1
    assert transcript_repository.events[0].provider_event_type == (
        "conversation.item.input_audio_transcription.delta"
    )
    assert transcript_repository.events[0].text_redacted == (
        "Email [EMAIL_REDACTED] about [ORDER_REDACTED]."
    )


def test_realtime_event_endpoint_structured_jsonl_never_persists_raw_text(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("VOICEAGENTS_TRANSCRIPT_LOGGING", "structured")
    path = tmp_path / "events" / "realtime-events.jsonl"
    client = make_client_with_jsonl_event_repository(JsonlVoiceEventRepository(path))
    token = create_session_and_token(client)

    response = client.post(
        "/v1/realtime/event",
        headers={"Authorization": f"Bearer {token}"},
        json=make_transcript_event_payload(
            event_type="transcript.user.done",
            text="Email customer@example.com at +1 (555) 123-4567 about ORDER-123456.",
        ),
    )

    assert response.status_code == 200
    file_content = path.read_text(encoding="utf-8")
    payload = json.loads(file_content.splitlines()[-1])
    assert "text" not in payload
    assert payload["transcript_text_redacted"] == (
        "Email [EMAIL_REDACTED] at [PHONE_REDACTED] about [ORDER_REDACTED]."
    )
    assert "customer@example.com" not in file_content
    assert "+1 (555) 123-4567" not in file_content
    assert "ORDER-123456" not in file_content


def test_realtime_event_endpoint_logs_tool_events_without_raw_arguments(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("VOICEAGENTS_TRANSCRIPT_LOGGING", "structured")
    path = tmp_path / "events" / "realtime-events.jsonl"
    client = make_client_with_jsonl_event_repository(JsonlVoiceEventRepository(path))
    token = create_session_and_token(client)

    raw_arguments = client.post(
        "/v1/realtime/event",
        headers={"Authorization": f"Bearer {token}"},
        json=make_transcript_event_payload(
            event_type="tool_call.requested",
            state="tool_calling",
            speaker=None,
            turn_id=None,
            sequence=None,
            text=None,
            tool_name="lookup_order",
            provider_call_id="provider-call-123",
            tool_status="requested",
            safe_summary="Lookup requested for ORDER-123456.",
            arguments={"order_id": "ORDER-123456"},
        ),
    )
    safe_event = client.post(
        "/v1/realtime/event",
        headers={"Authorization": f"Bearer {token}"},
        json=make_transcript_event_payload(
            event_type="tool_call.result",
            state="tool_calling",
            speaker=None,
            turn_id=None,
            sequence=None,
            text=None,
            tool_name="lookup_order",
            provider_call_id="provider-call-123",
            tool_status="completed",
            safe_summary="Lookup completed for ORDER-123456.",
        ),
    )

    assert raw_arguments.status_code == 422
    assert safe_event.status_code == 200
    file_content = path.read_text(encoding="utf-8")
    payload = json.loads(file_content.splitlines()[-1])
    assert payload["tool_name"] == "lookup_order"
    assert payload["provider_call_id"] == "provider-call-123"
    assert payload["tool_status"] == "completed"
    assert payload["tool_result_summary"] == "Lookup completed for [ORDER_REDACTED]."
    assert "arguments" not in payload
    assert "ORDER-123456" not in file_content
