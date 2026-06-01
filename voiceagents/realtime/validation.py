from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import secrets
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from voiceagents.realtime.contracts import RealtimeProviderName, ResponseMode
from voiceagents.realtime.event_log import BLOCKED_EVENT_KEYS, find_blocked_event_keys
from voiceagents.realtime.redaction import redact_mapping, redact_text


DEFAULT_VALIDATION_RUNS_PATH = Path(".voiceagents/validation-runs")
RUN_ID_RE = re.compile(r"^vrun-[0-9]{8}-[0-9]{6}-[0-9a-f]{8}$")
PROVIDER_ERROR_MARKERS = (
    "provider_error=",
    "event_log_error=",
    "data_channel_error",
    "OpenAI SDP exchange failed",
)
BLOCKED_REPORT_FIELD_NAMES = tuple(
    sorted(
        {
            *BLOCKED_EVENT_KEYS,
            "OPENAI_API_KEY",
            "Authorization",
            "arguments",
            "tool_arguments",
            "provider_raw_arguments",
        },
        key=len,
        reverse=True,
    )
)
BLOCKED_REPORT_TEXT_TOKENS = tuple(
    token
    for token in BLOCKED_REPORT_FIELD_NAMES
    if token not in {"audio", "arguments"}
)


class ValidationScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    suggested_prompt: str = Field(min_length=1)
    expected_tools: list[str]
    expected_handoff: bool
    manual_checks: list[str]


STANDARD_VALIDATION_SCENARIOS = [
    ValidationScenario(
        scenario_id="order_status",
        label="Order status lookup",
        description="Confirm the assistant can look up a realistic synthetic order status.",
        suggested_prompt="Please check the status of order ORD-20260601-1842.",
        expected_tools=["lookup_order"],
        expected_handoff=False,
        manual_checks=["heard_voice", "voice_quality_acceptable", "business_answer_acceptable"],
    ),
    ValidationScenario(
        scenario_id="logistics_tracking",
        label="Logistics tracking lookup",
        description="Confirm the assistant can look up a realistic synthetic logistics status.",
        suggested_prompt="Please check the shipping progress for order ORD-20260601-1842.",
        expected_tools=["lookup_logistics"],
        expected_handoff=False,
        manual_checks=["heard_voice", "voice_quality_acceptable", "business_answer_acceptable"],
    ),
    ValidationScenario(
        scenario_id="product_knowledge",
        label="Product knowledge consultation",
        description="Confirm product knowledge can answer a realistic wig care question.",
        suggested_prompt="How should I wash the LunaCare wig care kit product?",
        expected_tools=["query_product_knowledge"],
        expected_handoff=False,
        manual_checks=["heard_voice", "voice_quality_acceptable", "business_answer_acceptable"],
    ),
    ValidationScenario(
        scenario_id="knowledge_low_confidence_handoff",
        label="Knowledge miss handoff",
        description="Confirm unsupported product advice transfers to human support.",
        suggested_prompt="Can I use permanent hair dye on this wig and still keep the warranty?",
        expected_tools=["query_product_knowledge", "handoff_to_human"],
        expected_handoff=True,
        manual_checks=["heard_voice", "voice_quality_acceptable", "demo_ready"],
    ),
    ValidationScenario(
        scenario_id="customer_requested_human",
        label="User requested human",
        description="Confirm explicit human-agent requests create handoff context.",
        suggested_prompt="I want to speak with a human support agent.",
        expected_tools=["handoff_to_human"],
        expected_handoff=True,
        manual_checks=["heard_voice", "voice_quality_acceptable", "demo_ready"],
    ),
]


SCENARIOS_BY_ID = {scenario.scenario_id: scenario for scenario in STANDARD_VALIDATION_SCENARIOS}


class ValidationRunStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    call_id: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    provider: RealtimeProviderName
    response_mode: ResponseMode
    locale: str = Field(min_length=1)


class ValidationRunStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    scenario: ValidationScenario
    started_at: str = Field(min_length=1)
    summary_path: str = Field(min_length=1)
    report_path: str = Field(min_length=1)


class ValidationManualAssertions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heard_voice: bool = False
    voice_quality_acceptable: bool = False
    business_answer_acceptable: bool = False
    demo_ready: bool = False
    notes: str = ""


class ValidationRunFinishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_state: str = Field(min_length=1)
    transcript_text: str = ""
    assistant_response_text: str = ""
    tool_names: list[str] = Field(default_factory=list)
    handoff_reason: str | None = None
    provider_events: list[str] = Field(default_factory=list)
    latency_ms_values: list[int] = Field(default_factory=list)
    manual_assertions: ValidationManualAssertions


class ValidationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    passed: bool
    detail: str = Field(min_length=1)


class ValidationRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    status: Literal["pass", "fail"]
    started_at: str = Field(min_length=1)
    finished_at: str = Field(min_length=1)
    summary_path: str = Field(min_length=1)
    report_path: str = Field(min_length=1)
    checks: list[ValidationCheck]
    manual_assertions: ValidationManualAssertions
    transcript_text: str
    assistant_response_text: str
    tool_names: list[str]
    handoff_reason: str | None
    provider_events: list[str]
    latency_ms_values: list[int]


class ValidationRunFinishResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    status: Literal["pass", "fail"]
    summary_path: str = Field(min_length=1)
    report_path: str = Field(min_length=1)
    checks: list[ValidationCheck]


def evaluate_validation_checks(
    scenario: ValidationScenario,
    request: ValidationRunFinishRequest,
) -> list[ValidationCheck]:
    observed_tools = set(request.tool_names)
    expected_tools = set(scenario.expected_tools)
    handoff_observed = bool(request.handoff_reason and request.handoff_reason != "none")
    provider_error = any(
        marker in event
        for event in request.provider_events
        for marker in PROVIDER_ERROR_MARKERS
    )
    manual_voice = (
        request.manual_assertions.heard_voice
        and request.manual_assertions.voice_quality_acceptable
    )
    manual_business = (
        request.manual_assertions.demo_ready
        if scenario.expected_handoff
        else request.manual_assertions.business_answer_acceptable
    )
    assistant_required = not scenario.expected_handoff or bool(request.assistant_response_text.strip())

    return [
        ValidationCheck(
            name="scenario_known",
            passed=scenario.scenario_id in SCENARIOS_BY_ID,
            detail=f"scenario_id={scenario.scenario_id}",
        ),
        ValidationCheck(
            name="session_observed",
            passed=bool(request.session_state.strip()),
            detail=f"session_state={request.session_state}",
        ),
        ValidationCheck(
            name="expected_tools_observed",
            passed=expected_tools.issubset(observed_tools),
            detail=f"expected={sorted(expected_tools)} observed={sorted(observed_tools)}",
        ),
        ValidationCheck(
            name="expected_handoff_observed",
            passed=scenario.expected_handoff == handoff_observed,
            detail=f"expected={scenario.expected_handoff} observed={handoff_observed}",
        ),
        ValidationCheck(
            name="transcript_observed",
            passed=bool(request.transcript_text.strip()),
            detail="transcript present" if request.transcript_text.strip() else "transcript missing",
        ),
        ValidationCheck(
            name="assistant_response_observed",
            passed=assistant_required,
            detail="assistant response present or not required",
        ),
        ValidationCheck(
            name="provider_errors_absent",
            passed=not provider_error,
            detail="no provider error markers" if not provider_error else "provider error marker found",
        ),
        ValidationCheck(
            name="manual_voice_confirmed",
            passed=manual_voice,
            detail="manual voice checks passed" if manual_voice else "manual voice checks failed",
        ),
        ValidationCheck(
            name="manual_business_confirmed",
            passed=manual_business,
            detail="manual business/demo checks passed"
            if manual_business
            else "manual business/demo checks failed",
        ),
        ValidationCheck(
            name="blocked_secret_scan_passed",
            passed=True,
            detail="blocked secret scan pending file write",
        ),
    ]


class ValidationRunRepository:
    def __init__(self, root: str | Path = DEFAULT_VALIDATION_RUNS_PATH) -> None:
        self._root = Path(root)
        self._runs: dict[str, tuple[ValidationRunStartRequest, ValidationRunStartResponse]] = {}

    def start_run(self, request: ValidationRunStartRequest) -> ValidationRunStartResponse:
        scenario = SCENARIOS_BY_ID.get(request.scenario_id)
        if scenario is None:
            raise ValueError(f"Unknown validation scenario: {request.scenario_id}")

        run_id = _new_run_id()
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=False)
        started_at = datetime.now(timezone.utc).isoformat()
        response = ValidationRunStartResponse(
            run_id=run_id,
            scenario=scenario,
            started_at=started_at,
            summary_path=(run_dir / "summary.json").as_posix(),
            report_path=(run_dir / "report.md").as_posix(),
        )
        self._runs[run_id] = (request, response)
        return response

    def finish_run(
        self,
        run_id: str,
        request: ValidationRunFinishRequest,
    ) -> ValidationRunFinishResponse:
        start_request, start_response = self._runs.get(run_id, (None, None))  # type: ignore[assignment]
        if start_request is None or start_response is None:
            raise ValueError(f"Unknown validation run: {run_id}")

        scenario = SCENARIOS_BY_ID[start_request.scenario_id]
        run_dir = self._run_dir(run_id)
        summary_path = run_dir / "summary.json"
        report_path = run_dir / "report.md"
        redacted_payload = _redact_finish_request(request)
        checks = evaluate_validation_checks(scenario, request)
        finished_at = datetime.now(timezone.utc).isoformat()

        preliminary_summary = ValidationRunSummary(
            run_id=run_id,
            scenario_id=scenario.scenario_id,
            status="fail",
            started_at=start_response.started_at,
            finished_at=finished_at,
            summary_path=summary_path.as_posix(),
            report_path=report_path.as_posix(),
            checks=checks,
            manual_assertions=redacted_payload["manual_assertions"],
            transcript_text=redacted_payload["transcript_text"],
            assistant_response_text=redacted_payload["assistant_response_text"],
            tool_names=redacted_payload["tool_names"],
            handoff_reason=redacted_payload["handoff_reason"],
            provider_events=redacted_payload["provider_events"],
            latency_ms_values=redacted_payload["latency_ms_values"],
        )
        blocked_scan = _blocked_secret_scan(preliminary_summary.model_dump(mode="json"))
        checks = [
            check
            if check.name != "blocked_secret_scan_passed"
            else ValidationCheck(
                name="blocked_secret_scan_passed",
                passed=blocked_scan,
                detail="saved payload has no blocked tokens"
                if blocked_scan
                else "saved payload contains blocked tokens",
            )
            for check in checks
        ]
        status: Literal["pass", "fail"] = "pass" if all(check.passed for check in checks) else "fail"
        summary = preliminary_summary.model_copy(update={"checks": checks, "status": status})
        report = _render_report(summary)
        summary_path.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        report_path.write_text(report, encoding="utf-8")
        return ValidationRunFinishResponse(
            run_id=run_id,
            status=status,
            summary_path=summary_path.as_posix(),
            report_path=report_path.as_posix(),
            checks=checks,
        )

    def _run_dir(self, run_id: str) -> Path:
        if not RUN_ID_RE.fullmatch(run_id):
            raise ValueError("Invalid validation run id")
        root = self._root.resolve()
        run_dir = (root / run_id).resolve()
        if root != run_dir and root not in run_dir.parents:
            raise ValueError("Validation run path escaped root")
        return run_dir


def _new_run_id() -> str:
    now = datetime.now(timezone.utc)
    return f"vrun-{now:%Y%m%d}-{now:%H%M%S}-{secrets.token_hex(4)}"


def _redact_finish_request(request: ValidationRunFinishRequest) -> dict[str, object]:
    raw_payload = request.model_dump(mode="json")
    redacted = redact_mapping(raw_payload).value
    return _scrub_blocked_tokens(redacted)


def _scrub_blocked_tokens(value):
    if isinstance(value, str):
        if any(
            re.search(re.escape(token), value, flags=re.IGNORECASE)
            for token in BLOCKED_REPORT_TEXT_TOKENS
        ):
            return "[BLOCKED_REDACTED]"
        scrubbed = value
        for token in BLOCKED_REPORT_TEXT_TOKENS:
            scrubbed = re.sub(
                re.escape(token),
                "[BLOCKED_REDACTED]",
                scrubbed,
                flags=re.IGNORECASE,
            )
        return scrubbed
    if isinstance(value, list):
        return [_scrub_blocked_tokens(item) for item in value]
    if isinstance(value, dict):
        return {key: _scrub_blocked_tokens(nested) for key, nested in value.items()}
    return value


def _blocked_secret_scan(payload: dict[str, object]) -> bool:
    if find_blocked_event_keys(payload):
        return False
    serialized = json.dumps(payload, ensure_ascii=False)
    return not any(token in serialized for token in BLOCKED_REPORT_FIELD_NAMES)


def _render_report(summary: ValidationRunSummary) -> str:
    check_rows = "\n".join(
        f"| {check.name} | {'pass' if check.passed else 'fail'} | {check.detail} |"
        for check in summary.checks
    )
    notes = redact_text(summary.manual_assertions.notes).value
    return "\n".join(
        [
            "# VoiceAgents Validation Run",
            "",
            f"Run ID: {summary.run_id}",
            f"Scenario: {summary.scenario_id}",
            f"Status: {summary.status}",
            f"Started At: {summary.started_at}",
            f"Finished At: {summary.finished_at}",
            "",
            "## Checks",
            "",
            "| Check | Result | Detail |",
            "|---|---|---|",
            check_rows,
            "",
            "## Manual Assertions",
            "",
            f"- Heard voice: {summary.manual_assertions.heard_voice}",
            f"- Voice quality acceptable: {summary.manual_assertions.voice_quality_acceptable}",
            f"- Business answer acceptable: {summary.manual_assertions.business_answer_acceptable}",
            f"- Demo ready: {summary.manual_assertions.demo_ready}",
            f"- Notes: {notes}",
            "",
            "## Redacted Transcript",
            "",
            summary.transcript_text,
            "",
            "## Redacted Assistant Response",
            "",
            summary.assistant_response_text,
            "",
        ]
    )
