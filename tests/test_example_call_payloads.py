import json
from pathlib import Path

from fastapi.testclient import TestClient

from voiceagents.agent.models import CallFlowInput
from voiceagents.api.app import create_app


EXAMPLES_DIR = Path("examples/call-simulations")
EXPECTED_FIELDS = set(CallFlowInput.model_fields)


def _example_paths() -> list[Path]:
    return sorted(EXAMPLES_DIR.glob("*.json"))


def test_example_payloads_exist() -> None:
    assert {path.name for path in _example_paths()} == {
        "customer-requests-human.json",
        "logistics-tracking.json",
        "low-asr-confidence.json",
        "order-status.json",
        "product-usage.json",
    }


def test_example_payloads_match_call_flow_input_schema() -> None:
    for path in _example_paths():
        payload = json.loads(path.read_text())

        assert set(payload) == EXPECTED_FIELDS
        CallFlowInput.model_validate(payload)


def test_example_payloads_work_against_simulation_endpoint() -> None:
    client = TestClient(create_app())

    for path in _example_paths():
        payload = json.loads(path.read_text())
        response = client.post("/v1/calls/simulate", json=payload)

        assert response.status_code == 200, path.name
        body = response.json()
        assert isinstance(body["response_text"], str)
        assert body["tools_called"]

