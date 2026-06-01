from fastapi.testclient import TestClient

from voiceagents.api.app import create_app
from voiceagents.realtime.validation import ValidationRunRepository


def make_client(tmp_path) -> TestClient:
    return TestClient(
        create_app(
            realtime_validation_repository=ValidationRunRepository(
                tmp_path / "validation-runs"
            )
        )
    )


def make_start_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "scenario_id": "order_status",
        "session_id": "session-123",
        "call_id": "call-123",
        "merchant_id": "merchant-demo",
        "provider": "mock",
        "response_mode": "text",
        "locale": "zh-CN",
    }
    payload.update(updates)
    return payload


def make_finish_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "session_state": "ended",
        "transcript_text": "Please check order ORD-20260601-1842.",
        "assistant_response_text": "Order ORD-20260601-1842 has been paid.",
        "tool_names": ["lookup_order"],
        "handoff_reason": None,
        "provider_events": ["data_channel=open"],
        "latency_ms_values": [140],
        "manual_assertions": {
            "heard_voice": True,
            "voice_quality_acceptable": True,
            "business_answer_acceptable": True,
            "demo_ready": True,
            "notes": "clear",
        },
    }
    payload.update(updates)
    return payload


def test_get_validation_scenarios_returns_fixed_catalog(tmp_path) -> None:
    client = make_client(tmp_path)

    response = client.get("/v1/realtime/validation-scenarios")

    assert response.status_code == 200
    body = response.json()
    assert [scenario["scenario_id"] for scenario in body] == [
        "order_status",
        "logistics_tracking",
        "product_knowledge",
        "knowledge_low_confidence_handoff",
        "customer_requested_human",
    ]
    assert body[0]["suggested_prompt"] == "Please check the status of order ORD-20260601-1842."


def test_start_validation_run_returns_server_generated_run_id(tmp_path) -> None:
    client = make_client(tmp_path)

    response = client.post("/v1/realtime/validation-runs", json=make_start_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"].startswith("vrun-")
    assert body["scenario"]["scenario_id"] == "order_status"
    assert body["summary_path"].endswith("/summary.json")
    assert body["report_path"].endswith("/report.md")


def test_start_validation_run_rejects_unknown_scenario(tmp_path) -> None:
    client = make_client(tmp_path)

    response = client.post(
        "/v1/realtime/validation-runs",
        json=make_start_payload(scenario_id="unknown"),
    )

    assert response.status_code in {400, 422}


def test_finish_validation_run_writes_summary_and_report(tmp_path) -> None:
    client = make_client(tmp_path)
    started = client.post("/v1/realtime/validation-runs", json=make_start_payload()).json()

    response = client.post(
        f"/v1/realtime/validation-runs/{started['run_id']}/finish",
        json=make_finish_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == started["run_id"]
    assert body["status"] == "pass"
    assert any(check["name"] == "expected_tools_observed" for check in body["checks"])
    assert (tmp_path / "validation-runs" / started["run_id"] / "summary.json").exists()
    assert (tmp_path / "validation-runs" / started["run_id"] / "report.md").exists()


def test_finish_validation_run_rejects_path_like_run_id(tmp_path) -> None:
    client = make_client(tmp_path)

    response = client.post(
        "/v1/realtime/validation-runs/../escape/finish",
        json=make_finish_payload(),
    )

    assert response.status_code in {400, 404, 422}


def test_validation_report_runs_endpoint_lists_saved_runs(tmp_path) -> None:
    client = make_client(tmp_path)
    started = client.post("/v1/realtime/validation-runs", json=make_start_payload()).json()
    client.post(
        f"/v1/realtime/validation-runs/{started['run_id']}/finish",
        json=make_finish_payload(),
    )

    response = client.get("/v1/realtime/validation-report-runs")

    assert response.status_code == 200
    body = response.json()
    assert [run["run_id"] for run in body] == [started["run_id"]]
    assert body[0]["scenario_label"] == "Order status lookup"
    assert body[0]["readiness"] == "ready_for_pilot"
    assert "summary_path" not in body[0]
    assert "report_path" not in body[0]
