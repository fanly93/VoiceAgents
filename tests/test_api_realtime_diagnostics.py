from fastapi.testclient import TestClient

from voiceagents.api.app import create_app


LOCAL_ORIGIN = {"Origin": "http://127.0.0.1:8000"}


def test_realtime_dev_diagnostics_endpoint_returns_mock_pass(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(create_app())

    response = client.get("/v1/realtime/dev-diagnostics", headers=LOCAL_ORIGIN)

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "pass"
    assert body["provider"] == "mock"
    assert {check["name"] for check in body["checks"]} >= {
        "provider_supported",
        "provider_model",
        "transcript_logging",
        "client_secret_rate_limit",
    }


def test_realtime_dev_diagnostics_endpoint_reports_unsupported_provider(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "unknown_provider")
    client = TestClient(create_app())

    response = client.get("/v1/realtime/dev-diagnostics", headers=LOCAL_ORIGIN)

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "fail"
    assert body["provider"] == "unknown_provider"
    assert next(check for check in body["checks"] if check["name"] == "provider_supported")[
        "status"
    ] == "fail"


def test_realtime_dev_diagnostics_endpoint_reports_dashscope_supported(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "dashscope_realtime")
    client = TestClient(create_app())

    response = client.get("/v1/realtime/dev-diagnostics", headers=LOCAL_ORIGIN)

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "dashscope_realtime"
    assert next(check for check in body["checks"] if check["name"] == "provider_supported")[
        "status"
    ] == "pass"
    assert "openai_model" not in {check["name"] for check in body["checks"]}


def test_realtime_dev_diagnostics_endpoint_reports_openai_gate_and_key_without_leak(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "openai_realtime")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-should-not-render")
    monkeypatch.delenv("VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS", raising=False)
    client = TestClient(create_app())

    response = client.get("/v1/realtime/dev-diagnostics", headers=LOCAL_ORIGIN)

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "fail"
    assert next(check for check in body["checks"] if check["name"] == "openai_dev_gate")[
        "status"
    ] == "fail"
    assert next(check for check in body["checks"] if check["name"] == "openai_api_key")[
        "status"
    ] == "pass"
    assert "sk-secret-should-not-render" not in response.text


def test_realtime_dev_diagnostics_endpoint_reports_invalid_optional_config(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "mock")
    monkeypatch.setenv("VOICEAGENTS_TRANSCRIPT_LOGGING", "raw")
    monkeypatch.setenv("VOICEAGENTS_REALTIME_CLIENT_SECRET_RATE_LIMIT", "zero")
    client = TestClient(create_app())

    response = client.get("/v1/realtime/dev-diagnostics", headers=LOCAL_ORIGIN)

    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "warn"
    assert next(check for check in body["checks"] if check["name"] == "transcript_logging")[
        "status"
    ] == "warn"
    assert next(check for check in body["checks"] if check["name"] == "client_secret_rate_limit")[
        "status"
    ] == "warn"


def test_realtime_dev_diagnostics_endpoint_rejects_disallowed_origin(monkeypatch) -> None:
    monkeypatch.setenv("VOICEAGENTS_REALTIME_PROVIDER", "openai_realtime")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-should-not-render")
    client = TestClient(create_app())

    response = client.get(
        "/v1/realtime/dev-diagnostics",
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert "sk-secret-should-not-render" not in response.text
