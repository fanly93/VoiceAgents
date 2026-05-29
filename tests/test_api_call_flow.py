from fastapi.testclient import TestClient

from voiceagents.api.app import create_app


def test_call_simulation_endpoint_returns_deterministic_product_answer() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/calls/simulate",
        json={
            "call_id": "CALL-REDACTED",
            "merchant_id": "merchant_demo",
            "locale": "en-GB",
            "intent": "product_usage",
            "utterance": "How should I wash my wig?",
            "order_id_candidate": None,
            "order_id_confirmed": False,
            "asr_confidence": 0.91,
            "customer_requested_human": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["resolved"] is True
    assert body["handoff_required"] is False
    assert "cool water" in body["response_text"]

