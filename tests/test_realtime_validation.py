import json
import re

import pytest
from pydantic import ValidationError

from voiceagents.realtime.contracts import RealtimeProviderName, ResponseMode
from voiceagents.realtime.validation import (
    STANDARD_VALIDATION_SCENARIOS,
    ValidationManualAssertions,
    ValidationRunFinishRequest,
    ValidationRunRepository,
    ValidationRunStartRequest,
    ValidationRunSummary,
    evaluate_validation_checks,
)


def make_start_request() -> ValidationRunStartRequest:
    return ValidationRunStartRequest(
        scenario_id="order_status",
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-demo",
        provider=RealtimeProviderName.MOCK,
        response_mode=ResponseMode.TEXT,
        locale="zh-CN",
    )


def make_finish_request(**updates: object) -> ValidationRunFinishRequest:
    payload = {
        "session_state": "ended",
        "transcript_text": "Please check order ORD-20260601-1842.",
        "assistant_response_text": "Order ORD-20260601-1842 has been paid.",
        "tool_names": ["lookup_order"],
        "handoff_reason": None,
        "provider_events": ["data_channel=open"],
        "latency_ms_values": [120, 260],
        "manual_assertions": {
            "heard_voice": True,
            "voice_quality_acceptable": True,
            "business_answer_acceptable": True,
            "demo_ready": True,
            "notes": "Voice was clear enough for pilot validation.",
        },
    }
    payload.update(updates)
    return ValidationRunFinishRequest.model_validate(payload)


def test_standard_validation_scenarios_are_fixed_and_realistic() -> None:
    scenario_ids = [scenario.scenario_id for scenario in STANDARD_VALIDATION_SCENARIOS]

    assert scenario_ids == [
        "order_status",
        "logistics_tracking",
        "product_knowledge",
        "knowledge_low_confidence_handoff",
        "customer_requested_human",
    ]
    assert STANDARD_VALIDATION_SCENARIOS[0].expected_tools == ["lookup_order"]
    assert STANDARD_VALIDATION_SCENARIOS[1].expected_tools == ["lookup_logistics"]
    assert STANDARD_VALIDATION_SCENARIOS[2].expected_tools == ["query_product_knowledge"]
    assert STANDARD_VALIDATION_SCENARIOS[3].expected_tools == [
        "query_product_knowledge",
        "handoff_to_human",
    ]
    assert STANDARD_VALIDATION_SCENARIOS[3].expected_handoff is True
    assert STANDARD_VALIDATION_SCENARIOS[4].expected_tools == ["handoff_to_human"]
    assert "ORD-20260601-1842" in STANDARD_VALIDATION_SCENARIOS[0].suggested_prompt


def test_validation_models_reject_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ValidationRunStartRequest.model_validate(
            {
                "scenario_id": "order_status",
                "session_id": "session-123",
                "call_id": "call-123",
                "merchant_id": "merchant-demo",
                "provider": "mock",
                "response_mode": "text",
                "locale": "zh-CN",
                "client_secret": "must-not-be-accepted",
            }
        )


def test_finish_request_captures_manual_and_observed_data() -> None:
    request = make_finish_request()

    assert request.tool_names == ["lookup_order"]
    assert request.manual_assertions.heard_voice is True
    assert request.latency_ms_values == [120, 260]


def test_summary_model_serializes_required_checks() -> None:
    summary = ValidationRunSummary(
        run_id="vrun-20260601-120000-abcdef12",
        scenario_id="order_status",
        status="pass",
        started_at="2026-06-01T12:00:00+00:00",
        finished_at="2026-06-01T12:01:00+00:00",
        summary_path=".voiceagents/validation-runs/vrun-20260601-120000-abcdef12/summary.json",
        report_path=".voiceagents/validation-runs/vrun-20260601-120000-abcdef12/report.md",
        checks=evaluate_validation_checks(STANDARD_VALIDATION_SCENARIOS[0], make_finish_request()),
        manual_assertions=ValidationManualAssertions(
            heard_voice=True,
            voice_quality_acceptable=True,
            business_answer_acceptable=True,
            demo_ready=True,
            notes="ok",
        ),
        transcript_text="Where is [ORDER_REDACTED]?",
        assistant_response_text="The order is paid.",
        tool_names=["lookup_order"],
        handoff_reason=None,
        provider_events=["data_channel=open"],
        latency_ms_values=[120],
    )

    payload = summary.model_dump(mode="json")
    check_names = {check["name"] for check in payload["checks"]}
    assert "expected_tools_observed" in check_names
    assert "blocked_secret_scan_passed" in check_names


def test_validation_repository_creates_safe_run_paths(tmp_path) -> None:
    repository = ValidationRunRepository(tmp_path / "validation-runs")

    started = repository.start_run(make_start_request())

    assert re.fullmatch(r"vrun-\d{8}-\d{6}-[0-9a-f]{8}", started.run_id)
    assert started.summary_path.endswith(f"{started.run_id}/summary.json")
    assert started.report_path.endswith(f"{started.run_id}/report.md")
    assert (tmp_path / "validation-runs" / started.run_id).is_dir()


def test_validation_summary_is_redacted_before_write(tmp_path) -> None:
    repository = ValidationRunRepository(tmp_path / "validation-runs")
    started = repository.start_run(make_start_request())

    finished = repository.finish_run(
        started.run_id,
        make_finish_request(
            transcript_text=(
                "Please check order ORD-20260601-1842 and call +1 (555) 123-4567."
            ),
            provider_events=["client_secret=should-not-save", "OpenAI SDP exchange failed"],
        ),
    )

    summary_text = (tmp_path / "validation-runs" / started.run_id / "summary.json").read_text(
        encoding="utf-8"
    )
    payload = json.loads(summary_text)
    assert payload["transcript_text"] == "Please check order [ORDER_REDACTED] and call [PHONE_REDACTED]."
    assert "client_secret" not in summary_text
    assert "should-not-save" not in summary_text
    assert "SDP" not in summary_text
    assert finished.checks[-1].name == "blocked_secret_scan_passed"


def test_validation_report_contains_redacted_status_and_checks(tmp_path) -> None:
    repository = ValidationRunRepository(tmp_path / "validation-runs")
    started = repository.start_run(make_start_request())

    repository.finish_run(started.run_id, make_finish_request())

    report_text = (tmp_path / "validation-runs" / started.run_id / "report.md").read_text(
        encoding="utf-8"
    )
    assert "# VoiceAgents Validation Run" in report_text
    assert "Status: pass" in report_text
    assert "expected_tools_observed" in report_text
    assert "ORD-20260601-1842" not in report_text


def test_validation_checks_fail_when_expected_tool_missing() -> None:
    checks = evaluate_validation_checks(
        STANDARD_VALIDATION_SCENARIOS[0],
        make_finish_request(tool_names=[]),
    )

    failed = {check.name for check in checks if not check.passed}
    assert "expected_tools_observed" in failed


def test_validation_checks_fail_when_provider_errors_are_observed() -> None:
    checks = evaluate_validation_checks(
        STANDARD_VALIDATION_SCENARIOS[0],
        make_finish_request(provider_events=["provider_error=bad gateway"]),
    )

    failed = {check.name for check in checks if not check.passed}
    assert "provider_errors_absent" in failed
