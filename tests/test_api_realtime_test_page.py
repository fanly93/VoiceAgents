from pathlib import Path

from fastapi.testclient import TestClient

from voiceagents.api.app import create_app


STATIC_PAGE = Path("voiceagents/api/static/realtime-test.html")


def test_realtime_test_page_static_shell_contains_required_controls_and_panels() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert 'id="start-session"' in html
    assert 'id="stop-session"' in html
    assert 'id="mute-toggle"' in html
    assert 'id="response-mode"' in html
    assert 'id="session-state"' in html
    assert 'id="transcript"' in html
    assert 'id="assistant-response"' in html
    assert 'id="tool-calls"' in html
    assert 'id="handoff-state"' in html
    assert 'id="latency"' in html
    assert 'id="provider-events"' in html


def test_realtime_test_page_route_serves_static_page() -> None:
    client = TestClient(create_app())

    response = client.get("/realtime-test")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="start-session"' in response.text
