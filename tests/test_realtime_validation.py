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
    build_validation_run_report,
    derive_validation_report_readiness,
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


def make_summary(**updates: object) -> ValidationRunSummary:
    payload = {
        "run_id": "vrun-20260601-120000-abcdef12",
        "scenario_id": "order_status",
        "status": "pass",
        "started_at": "2026-06-01T12:00:00+00:00",
        "finished_at": "2026-06-01T12:01:00+00:00",
        "summary_path": ".voiceagents/validation-runs/vrun-20260601-120000-abcdef12/summary.json",
        "report_path": ".voiceagents/validation-runs/vrun-20260601-120000-abcdef12/report.md",
        "checks": evaluate_validation_checks(STANDARD_VALIDATION_SCENARIOS[0], make_finish_request()),
        "manual_assertions": {
            "heard_voice": True,
            "voice_quality_acceptable": True,
            "business_answer_acceptable": True,
            "demo_ready": True,
            "notes": "clear enough",
        },
        "transcript_text": "Where is [ORDER_REDACTED]?",
        "assistant_response_text": "The order is paid.",
        "tool_names": ["lookup_order"],
        "handoff_reason": None,
        "provider_events": ["data_channel=open"],
        "latency_ms_values": [120],
    }
    payload.update(updates)
    return ValidationRunSummary.model_validate(payload)


def with_check(
    summary: ValidationRunSummary,
    check_name: str,
    *,
    passed: bool,
    detail: str,
) -> ValidationRunSummary:
    checks = [
        check.model_copy(update={"passed": passed, "detail": detail})
        if check.name == check_name
        else check
        for check in summary.checks
    ]
    status = "pass" if all(check.passed for check in checks) else "fail"
    return summary.model_copy(update={"checks": checks, "status": status})


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


def test_readiness_is_ready_for_pilot_when_summary_passes() -> None:
    summary = make_summary()

    readiness = derive_validation_report_readiness(summary)

    assert readiness == "ready_for_pilot"


def test_readiness_needs_another_validation_for_non_critical_failure() -> None:
    summary = with_check(
        make_summary(),
        "manual_business_confirmed",
        passed=False,
        detail="manual business/demo checks failed",
    )

    readiness = derive_validation_report_readiness(summary)

    assert readiness == "needs_another_validation"


def test_readiness_is_blocked_when_provider_errors_are_observed() -> None:
    summary = with_check(
        make_summary(),
        "provider_errors_absent",
        passed=False,
        detail="provider error marker found",
    )

    readiness = derive_validation_report_readiness(summary)

    assert readiness == "blocked"


def test_readiness_is_blocked_when_blocked_secret_scan_fails() -> None:
    summary = with_check(
        make_summary(),
        "blocked_secret_scan_passed",
        passed=False,
        detail="saved payload contains blocked tokens",
    )

    readiness = derive_validation_report_readiness(summary)

    assert readiness == "blocked"


def test_report_view_contains_decision_summary_for_boss_audience() -> None:
    report = build_validation_run_report(make_summary())

    assert report.run_id == "vrun-20260601-120000-abcdef12"
    assert report.scenario.scenario_id == "order_status"
    assert report.scenario.label == "Order status lookup"
    assert report.readiness == "ready_for_pilot"
    assert report.decision_summary.label == "可以继续推进试点"
    assert report.decision_summary.next_action
    assert "老板" in {section.audience for section in report.audience_sections}
    assert any("业务回答" in bullet for bullet in report.business_proof)
    assert any(check.name == "expected_tools_observed" for check in report.checks)
    assert report.warnings == []


def test_report_view_adds_warnings_for_failed_checks() -> None:
    summary = with_check(
        make_summary(),
        "manual_business_confirmed",
        passed=False,
        detail="manual business/demo checks failed",
    )

    report = build_validation_run_report(summary)

    assert report.readiness == "needs_another_validation"
    assert report.warnings == [
        "manual_business_confirmed: manual business/demo checks failed"
    ]


def test_report_view_copy_summary_is_chinese_first_and_forwardable() -> None:
    report = build_validation_run_report(make_summary())

    assert report.copy_summary.text.startswith("试点演示验证结果：")
    assert "订单状态查询" in report.copy_summary.text
    assert "可以继续推进试点" in report.copy_summary.text
    assert "证据：" in report.copy_summary.text
    assert "下一步：" in report.copy_summary.text


def test_report_view_does_not_expose_absolute_local_paths() -> None:
    summary = make_summary(
        summary_path="/Users/tanglin/VibeCoding/VoiceAgents/.voiceagents/validation-runs/vrun-20260601-120000-abcdef12/summary.json",
        report_path="/Users/tanglin/VibeCoding/VoiceAgents/.voiceagents/validation-runs/vrun-20260601-120000-abcdef12/report.md",
    )

    report_payload = build_validation_run_report(summary).model_dump(mode="json")

    assert "/Users/" not in json.dumps(report_payload, ensure_ascii=False)
    assert "summary_path" not in report_payload
    assert "report_path" not in report_payload


def test_list_saved_runs_returns_empty_when_root_is_missing(tmp_path) -> None:
    repository = ValidationRunRepository(tmp_path / "missing-validation-runs")

    assert repository.list_saved_runs() == []


def test_list_saved_runs_returns_newest_first_without_paths(tmp_path) -> None:
    root = tmp_path / "validation-runs"
    older = make_summary(
        run_id="vrun-20260601-120000-abcdef12",
        finished_at="2026-06-01T12:01:00+00:00",
    )
    newer = make_summary(
        run_id="vrun-20260601-130000-bcdefa23",
        finished_at="2026-06-01T13:01:00+00:00",
    )
    for summary in [older, newer]:
        run_dir = root / summary.run_id
        run_dir.mkdir(parents=True)
        (run_dir / "summary.json").write_text(
            json.dumps(summary.model_dump(mode="json")),
            encoding="utf-8",
        )
    (root / "notes").mkdir()

    runs = ValidationRunRepository(root).list_saved_runs()

    assert [run.run_id for run in runs] == [
        "vrun-20260601-130000-bcdefa23",
        "vrun-20260601-120000-abcdef12",
    ]
    assert runs[0].scenario_label == "Order status lookup"
    assert runs[0].readiness == "ready_for_pilot"
    assert "path" not in runs[0].model_dump(mode="json")


def test_list_saved_runs_skips_malformed_summaries(tmp_path) -> None:
    root = tmp_path / "validation-runs"
    valid = make_summary(run_id="vrun-20260601-120000-abcdef12")
    valid_dir = root / valid.run_id
    bad_dir = root / "vrun-20260601-130000-bcdefa23"
    valid_dir.mkdir(parents=True)
    bad_dir.mkdir(parents=True)
    (valid_dir / "summary.json").write_text(
        json.dumps(valid.model_dump(mode="json")),
        encoding="utf-8",
    )
    (bad_dir / "summary.json").write_text("{not-json", encoding="utf-8")

    runs = ValidationRunRepository(root).list_saved_runs()

    assert [run.run_id for run in runs] == ["vrun-20260601-120000-abcdef12"]


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


def test_validation_summary_preserves_safe_audio_event_names(tmp_path) -> None:
    repository = ValidationRunRepository(tmp_path / "validation-runs")
    started = repository.start_run(make_start_request())

    finished = repository.finish_run(
        started.run_id,
        make_finish_request(provider_events=["response.output_audio_transcript.done"]),
    )

    summary_text = (tmp_path / "validation-runs" / started.run_id / "summary.json").read_text(
        encoding="utf-8"
    )
    assert "response.output_audio_transcript.done" in summary_text
    assert finished.status == "pass"
    assert all(check.passed for check in finished.checks)


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


def test_validation_checks_fail_when_session_was_not_observed() -> None:
    checks = evaluate_validation_checks(
        STANDARD_VALIDATION_SCENARIOS[0],
        make_finish_request(session_state="idle"),
    )

    failed = {check.name for check in checks if not check.passed}
    assert "session_observed" in failed


def test_validation_checks_fail_when_provider_errors_are_observed() -> None:
    checks = evaluate_validation_checks(
        STANDARD_VALIDATION_SCENARIOS[0],
        make_finish_request(provider_events=["provider_error=bad gateway"]),
    )

    failed = {check.name for check in checks if not check.passed}
    assert "provider_errors_absent" in failed
