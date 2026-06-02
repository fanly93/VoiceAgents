from pathlib import Path

from fastapi.testclient import TestClient

from voiceagents.api.app import create_app


STATIC_PAGE = Path("voiceagents/api/static/realtime-validation-reports.html")


def test_validation_reports_page_static_shell_contains_required_sections() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert 'id="run-list"' in html
    assert 'id="readiness-banner"' in html
    assert 'id="scenario-coverage"' in html
    assert 'id="business-proof"' in html
    assert 'id="audience-sections"' in html
    assert 'id="copy-summary"' in html
    assert 'id="copy-summary-button"' in html
    assert 'id="empty-state"' in html
    assert 'id="error-state"' in html
    assert "/v1/realtime/validation-report-runs" in html


def test_validation_reports_page_route_serves_static_page() -> None:
    client = TestClient(create_app())

    response = client.get("/realtime-validation-reports")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="run-list"' in response.text
