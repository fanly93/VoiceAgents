# Pilot Validation Harness v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local `/realtime-test` validation harness that saves redacted per-run `summary.json` and `report.md` files for five standard realtime voice scenarios.

**Architecture:** Add provider-neutral validation contracts and a local repository under `voiceagents/realtime/`, expose local FastAPI endpoints from `voiceagents/api/app.py`, and extend the existing static `/realtime-test` page to start/finish validation runs. The backend owns run ID generation, path safety, redaction, check evaluation, and file writing.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, static HTML/JavaScript, existing Node/vm browser-JS test harness.

---

## File Structure

- Create `voiceagents/realtime/validation.py`: scenario definitions, Pydantic request/response models, validation result models, local repository, report rendering, blocked-secret scanning.
- Modify `voiceagents/api/app.py`: wire validation repository and add three local endpoints.
- Modify `voiceagents/api/static/realtime-test.html`: add validation controls, collect safe page observations, call start/finish endpoints.
- Create `tests/test_realtime_validation.py`: unit tests for scenarios, contracts, redaction, path safety, and report writing.
- Create `tests/test_api_realtime_validation.py`: API tests for scenarios, start, finish, unknown scenario, path-safe run handling.
- Modify `tests/test_api_realtime_test_page.py`: static HTML assertions for validation controls and forbidden secret rendering.
- Modify `tests/test_realtime_test_page_failure_modes.py` or create `tests/test_realtime_test_page_validation_flow.py`: Node/vm harness for browser validation start/finish lifecycle.
- Modify `README.md`: short local validation report usage section.
- Modify `OPENAI_REALTIME_VOICE_MVP_HANDOFF.md`: note the new validation harness after implementation.

---

### Task 1: Validation Contracts And Scenario Catalog

**Files:**
- Create: `voiceagents/realtime/validation.py`
- Create: `tests/test_realtime_validation.py`

- [ ] **Step 1: Write failing scenario catalog test**

```python
from voiceagents.realtime.validation import STANDARD_VALIDATION_SCENARIOS


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_realtime_validation.py::test_standard_validation_scenarios_are_fixed_and_realistic -v`

Expected: FAIL with `ModuleNotFoundError` or missing `STANDARD_VALIDATION_SCENARIOS`.

- [ ] **Step 3: Implement scenario model and catalog**

Create `voiceagents/realtime/validation.py` with:

```python
from pydantic import BaseModel, ConfigDict, Field


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
```

- [ ] **Step 4: Run scenario catalog test**

Run: `./.venv/bin/python -m pytest tests/test_realtime_validation.py::test_standard_validation_scenarios_are_fixed_and_realistic -v`

Expected: PASS.

- [ ] **Step 5: Write failing request/summary model test**

Add to `tests/test_realtime_validation.py`:

```python
import pytest
from pydantic import ValidationError

from voiceagents.realtime.contracts import RealtimeProviderName, ResponseMode
from voiceagents.realtime.validation import (
    ValidationManualAssertions,
    ValidationRunFinishRequest,
    ValidationRunObservation,
    ValidationRunStartRequest,
)


def test_validation_models_reject_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ValidationRunStartRequest.model_validate(
            {
                "scenario_id": "order_status",
                "session_id": "session-1",
                "call_id": "call-1",
                "merchant_id": "merchant_demo",
                "provider": "mock",
                "response_mode": "text",
                "locale": "zh-CN",
                "client_secret": "must-not-be-accepted",
            }
        )


def test_finish_request_captures_manual_and_observed_data() -> None:
    request = ValidationRunFinishRequest(
        session_state="ended",
        observation=ValidationRunObservation(
            transcript_text="User asked about order ORD-20260601-1842.",
            assistant_response_text="The order has been paid.",
            tool_names=["lookup_order"],
            handoff_reason=None,
            provider_events=["data_channel=open"],
            latency_ms_values=[120, 250],
        ),
        manual_assertions=ValidationManualAssertions(
            heard_voice=True,
            voice_quality_acceptable=True,
            business_answer_acceptable=True,
            demo_ready=True,
            notes="Voice was clear enough for a pilot review.",
        ),
    )

    assert request.observation.tool_names == ["lookup_order"]
    assert request.manual_assertions.heard_voice is True
```

- [ ] **Step 6: Run model test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_realtime_validation.py::test_validation_models_reject_extra_fields tests/test_realtime_validation.py::test_finish_request_captures_manual_and_observed_data -v`

Expected: FAIL because the models do not exist.

- [ ] **Step 7: Implement validation request/response models**

Add these models to `voiceagents/realtime/validation.py`:

```python
from voiceagents.realtime.contracts import RealtimeProviderName, ResponseMode


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

    heard_voice: bool
    voice_quality_acceptable: bool
    business_answer_acceptable: bool
    demo_ready: bool
    notes: str = ""


class ValidationRunObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcript_text: str = ""
    assistant_response_text: str = ""
    tool_names: list[str] = []
    handoff_reason: str | None = None
    provider_events: list[str] = []
    latency_ms_values: list[int] = []


class ValidationRunFinishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_state: str = Field(min_length=1)
    observation: ValidationRunObservation
    manual_assertions: ValidationManualAssertions
```

- [ ] **Step 8: Run validation model tests**

Run: `./.venv/bin/python -m pytest tests/test_realtime_validation.py -v`

Expected: PASS.

- [ ] **Step 9: Commit Task 1**

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: add realtime validation scenario contracts"
```

---

### Task 2: Local Validation Repository And Report Rendering

**Files:**
- Modify: `voiceagents/realtime/validation.py`
- Modify: `tests/test_realtime_validation.py`

- [ ] **Step 1: Write failing repository test**

Add to `tests/test_realtime_validation.py`:

```python
import json

from voiceagents.realtime.validation import LocalValidationRunRepository


def test_local_validation_repository_writes_redacted_summary_and_report(tmp_path) -> None:
    repository = LocalValidationRunRepository(root=tmp_path / "validation-runs")
    start = ValidationRunStartRequest(
        scenario_id="order_status",
        session_id="session-1",
        call_id="call-1",
        merchant_id="merchant_demo",
        provider="mock",
        response_mode="text",
        locale="zh-CN",
    )
    started = repository.start_run(start)

    finished = repository.finish_run(
        started.run_id,
        ValidationRunFinishRequest(
            session_state="ended",
            observation=ValidationRunObservation(
                transcript_text="My email is buyer@example.com and order ORD-20260601-1842.",
                assistant_response_text="Order ORD-20260601-1842 has been paid.",
                tool_names=["lookup_order"],
                handoff_reason=None,
                provider_events=["data_channel=open"],
                latency_ms_values=[2, 4],
            ),
            manual_assertions=ValidationManualAssertions(
                heard_voice=True,
                voice_quality_acceptable=True,
                business_answer_acceptable=True,
                demo_ready=True,
                notes="Send result to buyer@example.com",
            ),
        ),
    )

    summary = json.loads((tmp_path / "validation-runs" / started.run_id / "summary.json").read_text())
    report = (tmp_path / "validation-runs" / started.run_id / "report.md").read_text()

    assert finished.status == "pass"
    assert summary["scenario_id"] == "order_status"
    assert summary["checks"]["expected_tools_observed"]["passed"] is True
    assert (tmp_path / "validation-runs" / started.run_id / "start.json").exists()
    assert "[EMAIL_REDACTED]" in report
    assert "buyer@example.com" not in report
    assert "client_secret" not in report
    assert "tool_call_token" not in report
```

- [ ] **Step 2: Run repository test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_realtime_validation.py::test_local_validation_repository_writes_redacted_summary_and_report -v`

Expected: FAIL because `LocalValidationRunRepository` does not exist.

- [ ] **Step 3: Implement repository, run IDs, checks, and report rendering**

Add to `voiceagents/realtime/validation.py`:

```python
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets

from voiceagents.realtime.redaction import redact_text


DEFAULT_VALIDATION_RUNS_PATH = Path(".voiceagents/validation-runs")
BLOCKED_REPORT_TOKENS = (
    "OPENAI_API_KEY",
    "client_secret",
    "tool_call_token",
    "Authorization",
    "authorization",
    "sdp",
    "raw_audio",
    "audio_bytes",
)


class ValidationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    detail: str


class ValidationRunFinishResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    status: str = Field(pattern="^(pass|fail)$")
    summary_path: str = Field(min_length=1)
    report_path: str = Field(min_length=1)
    checks: dict[str, ValidationCheck]


class LocalValidationRunRepository:
    def __init__(self, root: str | Path = DEFAULT_VALIDATION_RUNS_PATH) -> None:
        self._root = Path(root)

    def start_run(self, request: ValidationRunStartRequest) -> ValidationRunStartResponse:
        scenario = get_validation_scenario(request.scenario_id)
        run_id = self._new_run_id()
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=False)
        started_at = datetime.now(timezone.utc).isoformat()
        start_payload = {
            "run_id": run_id,
            "started_at": started_at,
            "scenario": scenario.model_dump(mode="json"),
            "request": request.model_dump(mode="json"),
        }
        (run_dir / "start.json").write_text(
            json.dumps(start_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return ValidationRunStartResponse(
            run_id=run_id,
            scenario=scenario,
            started_at=started_at,
            summary_path=str(run_dir / "summary.json"),
            report_path=str(run_dir / "report.md"),
        )

    def finish_run(
        self,
        run_id: str,
        request: ValidationRunFinishRequest,
    ) -> ValidationRunFinishResponse:
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        start_payload = json.loads((run_dir / "start.json").read_text(encoding="utf-8"))
        scenario = ValidationScenario.model_validate(start_payload["scenario"])
        summary = build_validation_summary(run_id, scenario, request, run_dir)
        report = render_validation_report(summary)
        summary_path = run_dir / "summary.json"
        report_path = run_dir / "report.md"
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report_path.write_text(report, encoding="utf-8")
        checks = {
            key: ValidationCheck.model_validate(value)
            for key, value in summary["checks"].items()
        }
        return ValidationRunFinishResponse(
            run_id=run_id,
            status=summary["status"],
            summary_path=str(summary_path),
            report_path=str(report_path),
            checks=checks,
        )

    def _new_run_id(self) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"vrun-{stamp}-{secrets.token_hex(4)}"

    def _run_dir(self, run_id: str) -> Path:
        if not re.fullmatch(r"vrun-[0-9]{8}-[0-9]{6}-[a-f0-9]{8}", run_id):
            raise ValueError("invalid validation run id")
        resolved = (self._root / run_id).resolve()
        root = self._root.resolve()
        if root != resolved and root not in resolved.parents:
            raise ValueError("validation run path escaped root")
        return resolved
```

Implement `get_validation_scenario()`, `build_validation_summary()`, `render_validation_report()`, and redaction helpers in the same file. Keep all text fields redacted before writing.

- [ ] **Step 4: Run repository tests**

Run: `./.venv/bin/python -m pytest tests/test_realtime_validation.py -v`

Expected: PASS.

- [ ] **Step 5: Write failing path safety test**

Add:

```python
def test_local_validation_repository_rejects_invalid_run_id(tmp_path) -> None:
    repository = LocalValidationRunRepository(root=tmp_path / "validation-runs")

    with pytest.raises(ValueError):
        repository.finish_run(
            "../outside",
            ValidationRunFinishRequest(
                session_state="ended",
                observation=ValidationRunObservation(),
                manual_assertions=ValidationManualAssertions(
                    heard_voice=False,
                    voice_quality_acceptable=False,
                    business_answer_acceptable=False,
                    demo_ready=False,
                    notes="",
                ),
            ),
        )
```

- [ ] **Step 6: Run path safety test**

Run: `./.venv/bin/python -m pytest tests/test_realtime_validation.py::test_local_validation_repository_rejects_invalid_run_id -v`

Expected: PASS.

- [ ] **Step 7: Commit Task 2**

```bash
git add voiceagents/realtime/validation.py tests/test_realtime_validation.py
git commit -m "feat: write local realtime validation reports"
```

---

### Task 3: Validation API Endpoints

**Files:**
- Modify: `voiceagents/api/app.py`
- Create: `tests/test_api_realtime_validation.py`

- [ ] **Step 1: Write failing scenario endpoint test**

```python
from fastapi.testclient import TestClient

from voiceagents.api.app import create_app


def test_validation_scenarios_endpoint_returns_fixed_scenarios() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/realtime/validation-scenarios")

    assert response.status_code == 200
    scenario_ids = [item["scenario_id"] for item in response.json()["scenarios"]]
    assert scenario_ids == [
        "order_status",
        "logistics_tracking",
        "product_knowledge",
        "knowledge_low_confidence_handoff",
        "customer_requested_human",
    ]
```

- [ ] **Step 2: Run endpoint test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_api_realtime_validation.py::test_validation_scenarios_endpoint_returns_fixed_scenarios -v`

Expected: FAIL with 404.

- [ ] **Step 3: Wire repository and scenarios endpoint**

Modify `create_app()` to initialize `LocalValidationRunRepository` and add:

```python
from voiceagents.realtime.validation import (
    LocalValidationRunRepository,
    STANDARD_VALIDATION_SCENARIOS,
    ValidationRunFinishRequest,
    ValidationRunFinishResponse,
    ValidationRunStartRequest,
    ValidationRunStartResponse,
)


def create_app(
    *,
    realtime_session_store: InMemoryVoiceSessionStore | None = None,
    realtime_event_repository: VoiceEventRepository | None = None,
    realtime_transcript_repository: RealtimeTranscriptRepository | None = None,
    realtime_validation_repository: LocalValidationRunRepository | None = None,
) -> FastAPI:
    app = FastAPI(title="VoiceAgents")
    validation_repository = realtime_validation_repository or LocalValidationRunRepository()
    app.state.realtime_validation_repository = validation_repository
```

Then add the scenario route inside `create_app()`:

```python
@app.get("/v1/realtime/validation-scenarios")
def list_validation_scenarios() -> dict[str, object]:
    return {"scenarios": [scenario.model_dump(mode="json") for scenario in STANDARD_VALIDATION_SCENARIOS]}
```

- [ ] **Step 4: Run scenario endpoint test**

Run: `./.venv/bin/python -m pytest tests/test_api_realtime_validation.py::test_validation_scenarios_endpoint_returns_fixed_scenarios -v`

Expected: PASS.

- [ ] **Step 5: Write failing start/finish endpoint tests**

Add:

```python
def test_validation_run_start_and_finish_write_report(tmp_path) -> None:
    client = TestClient(create_app(realtime_validation_repository=LocalValidationRunRepository(tmp_path)))

    started = client.post(
        "/v1/realtime/validation-runs",
        json={
            "scenario_id": "order_status",
            "session_id": "session-1",
            "call_id": "call-1",
            "merchant_id": "merchant_demo",
            "provider": "mock",
            "response_mode": "text",
            "locale": "zh-CN",
        },
    )

    assert started.status_code == 200
    run_id = started.json()["run_id"]

    finished = client.post(
        f"/v1/realtime/validation-runs/{run_id}/finish",
        json={
            "session_state": "ended",
            "observation": {
                "transcript_text": "Where is order ORD-20260601-1842?",
                "assistant_response_text": "The order has been paid.",
                "tool_names": ["lookup_order"],
                "handoff_reason": None,
                "provider_events": ["data_channel=open"],
                "latency_ms_values": [3],
            },
            "manual_assertions": {
                "heard_voice": True,
                "voice_quality_acceptable": True,
                "business_answer_acceptable": True,
                "demo_ready": True,
                "notes": "Good enough for validation.",
            },
        },
    )

    assert finished.status_code == 200
    assert finished.json()["status"] == "pass"
```

- [ ] **Step 6: Run start/finish test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_api_realtime_validation.py::test_validation_run_start_and_finish_write_report -v`

Expected: FAIL because endpoints are missing.

- [ ] **Step 7: Implement start and finish endpoints**

Add:

```python
@app.post("/v1/realtime/validation-runs")
def start_validation_run(request: ValidationRunStartRequest) -> ValidationRunStartResponse:
    return app.state.realtime_validation_repository.start_run(request)


@app.post("/v1/realtime/validation-runs/{run_id}/finish")
def finish_validation_run(
    run_id: str,
    request: ValidationRunFinishRequest,
) -> ValidationRunFinishResponse:
    try:
        return app.state.realtime_validation_repository.finish_run(run_id, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
```

- [ ] **Step 8: Run API validation tests**

Run: `./.venv/bin/python -m pytest tests/test_api_realtime_validation.py -v`

Expected: PASS.

- [ ] **Step 9: Commit Task 3**

```bash
git add voiceagents/api/app.py tests/test_api_realtime_validation.py
git commit -m "feat: expose realtime validation run endpoints"
```

---

### Task 4: `/realtime-test` Validation Controls

**Files:**
- Modify: `voiceagents/api/static/realtime-test.html`
- Modify: `tests/test_api_realtime_test_page.py`
- Create: `tests/test_realtime_test_page_validation_flow.py`

- [ ] **Step 1: Write failing static control test**

Add to `tests/test_api_realtime_test_page.py`:

```python
def test_realtime_test_page_contains_validation_run_controls() -> None:
    html = STATIC_PAGE.read_text(encoding="utf-8")

    assert 'id="validation-scenario"' in html
    assert 'id="start-validation-run"' in html
    assert 'id="finish-validation-run"' in html
    assert 'id="validation-run-id"' in html
    assert 'id="validation-report"' in html
    assert 'id="manual-heard-voice"' in html
    assert 'id="manual-voice-quality"' in html
    assert 'id="manual-business-answer"' in html
    assert 'id="manual-demo-ready"' in html
```

- [ ] **Step 2: Run static control test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py::test_realtime_test_page_contains_validation_run_controls -v`

Expected: FAIL because controls are missing.

- [ ] **Step 3: Add minimal validation UI**

Add a section near the toolbar:

```html
<section>
  <h2>Validation Run</h2>
  <div class="toolbar">
    <select id="validation-scenario" aria-label="Validation scenario"></select>
    <button id="start-validation-run" type="button">Start Validation Run</button>
    <button id="finish-validation-run" type="button">Finish Run</button>
  </div>
  <label><input id="manual-heard-voice" type="checkbox" /> Heard voice</label>
  <label><input id="manual-voice-quality" type="checkbox" /> Voice quality acceptable</label>
  <label><input id="manual-business-answer" type="checkbox" /> Business answer acceptable</label>
  <label><input id="manual-demo-ready" type="checkbox" /> Demo ready</label>
  <textarea id="manual-validation-notes" aria-label="Validation notes"></textarea>
  <div id="validation-run-id" data-panel>none</div>
  <div id="validation-report" data-panel></div>
</section>
```

- [ ] **Step 4: Run static control test**

Run: `./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py::test_realtime_test_page_contains_validation_run_controls -v`

Expected: PASS.

- [ ] **Step 5: Write failing JS flow test**

Create `tests/test_realtime_test_page_validation_flow.py` using the Node/vm pattern from `tests/test_realtime_test_page_failure_modes.py`. Assert:

```javascript
assert(fetchCalls.some((call) => call.url === "/v1/realtime/validation-scenarios"), "loads scenarios");
assert(fetchCalls.some((call) => call.url === "/v1/realtime/validation-runs"), "starts run");
assert(fetchCalls.some((call) => call.url.includes("/v1/realtime/validation-runs/vrun-")), "finishes run");
assert(element("validation-run-id").textContent.includes("vrun-"), "renders run id");
assert(element("validation-report").textContent.includes("report.md"), "renders report path");
```

- [ ] **Step 6: Run JS flow test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_realtime_test_page_validation_flow.py -v`

Expected: FAIL because validation JS is missing.

- [ ] **Step 7: Implement validation JS lifecycle**

Add state:

```javascript
validationRunId: null,
validationScenario: null,
validationToolNames: [],
validationProviderEvents: [],
validationLatencyValues: [],
```

Update existing render/relay paths to append safe observations to the validation arrays. Add:

```javascript
async function loadValidationScenarios() {
  const response = await fetch("/v1/realtime/validation-scenarios");
  if (!response.ok) {
    appendPanel("validation-report", `validation_scenarios_error=${response.status}`);
    return;
  }
  const payload = await response.json();
  const select = el("validation-scenario");
  select.textContent = "";
  for (const scenario of payload.scenarios) {
    const option = document.createElement("option");
    option.value = scenario.scenario_id;
    option.textContent = scenario.label;
    option.dataset.suggestedPrompt = scenario.suggested_prompt;
    select.appendChild(option);
  }
}

async function startValidationRun() {
  const scenarioId = el("validation-scenario").value;
  const response = await fetch("/v1/realtime/validation-runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      scenario_id: scenarioId,
      session_id: state.sessionId || newId("session"),
      call_id: state.callId || newId("call"),
      merchant_id: "merchant_demo",
      provider: state.provider || "mock",
      response_mode: el("response-mode").value,
      locale: navigator.language || "zh-CN",
    }),
  });
  if (!response.ok) {
    appendPanel("validation-report", `validation_start_error=${response.status}`);
    return;
  }
  const payload = await response.json();
  state.validationRunId = payload.run_id;
  state.validationScenario = payload.scenario;
  state.validationToolNames = [];
  state.validationProviderEvents = [];
  state.validationLatencyValues = [];
  writePanel("validation-run-id", payload.run_id);
}

function collectValidationObservation() {
  return {
    transcript_text: el("transcript").textContent || "",
    assistant_response_text: el("assistant-response").textContent || "",
    tool_names: state.validationToolNames,
    handoff_reason: el("handoff-state").textContent === "none" ? null : el("handoff-state").textContent,
    provider_events: state.validationProviderEvents,
    latency_ms_values: state.validationLatencyValues,
  };
}

function collectManualAssertions() {
  return {
    heard_voice: el("manual-heard-voice").checked,
    voice_quality_acceptable: el("manual-voice-quality").checked,
    business_answer_acceptable: el("manual-business-answer").checked,
    demo_ready: el("manual-demo-ready").checked,
    notes: el("manual-validation-notes").value || "",
  };
}

async function finishValidationRun() {
  if (!state.validationRunId) {
    appendPanel("validation-report", "validation_run_missing");
    return;
  }
  const response = await fetch(`/v1/realtime/validation-runs/${state.validationRunId}/finish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_state: el("session-state").textContent || "unknown",
      observation: collectValidationObservation(),
      manual_assertions: collectManualAssertions(),
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    appendPanel("validation-report", `validation_finish_error=${response.status}`);
    return;
  }
  writePanel("validation-report", `${payload.status}\n${payload.summary_path}\n${payload.report_path}`);
}
```

Use `textContent` from existing panels as observations. Never include `clientSecret` or `toolCallToken` in validation requests.

- [ ] **Step 8: Run page tests**

Run: `./.venv/bin/python -m pytest tests/test_api_realtime_test_page.py tests/test_realtime_test_page_validation_flow.py -v`

Expected: PASS.

- [ ] **Step 9: Commit Task 4**

```bash
git add voiceagents/api/static/realtime-test.html tests/test_api_realtime_test_page.py tests/test_realtime_test_page_validation_flow.py
git commit -m "feat: add realtime validation controls"
```

---

### Task 5: Documentation And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `OPENAI_REALTIME_VOICE_MVP_HANDOFF.md`
- Modify: `docs/specs/voiceagents-pilot-validation-harness-v1.md`

- [ ] **Step 1: Write README usage section**

Add a short section under Realtime Browser Test:

```markdown
## Pilot Validation Runs

The `/realtime-test` page can save local validation run reports for five standard scenarios. Reports are written under `.voiceagents/validation-runs/<run_id>/` and are gitignored.

Use `Start Validation Run`, run the realtime session, fill the manual checkboxes, then use `Finish Run`.
```

- [ ] **Step 2: Update handoff**

Add a short note that Pilot Validation Harness v1 exists, where reports are saved, and that reports remain local-only.

- [ ] **Step 3: Run focused tests**

Run:

```bash
./.venv/bin/python -m pytest \
  tests/test_realtime_validation.py \
  tests/test_api_realtime_validation.py \
  tests/test_api_realtime_test_page.py \
  tests/test_realtime_test_page_validation_flow.py -v
```

Expected: all selected tests pass.

- [ ] **Step 4: Run full tests**

Run: `./.venv/bin/python -m pytest`

Expected: all tests pass.

- [ ] **Step 5: Check docs and whitespace**

Run:

```bash
git diff --check
rg -n "client_secret|tool_call_token|OPENAI_API_KEY" docs/specs/voiceagents-pilot-validation-harness-v1.md docs/superpowers/plans/2026-06-01-pilot-validation-harness-v1.md README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md
```

Expected:

- `git diff --check` exits 0.
- `rg` only finds forbidden-token names in explicit safety requirement lists, not in examples of saved output.
- Manual placeholder scan finds no unfinished instructions or copy-paste placeholders.

- [ ] **Step 6: Commit Task 5**

```bash
git add README.md OPENAI_REALTIME_VOICE_MVP_HANDOFF.md docs/specs/voiceagents-pilot-validation-harness-v1.md
git commit -m "docs: document realtime validation runs"
```

---

## Self-Review

Spec coverage:

- Five scenarios: Task 1.
- Local summary/report persistence: Task 2.
- API endpoints: Task 3.
- `/realtime-test` controls: Task 4.
- Redaction and blocked-secret scan: Task 2 and Task 5.
- Tests at model, API, page, browser-JS, and full-suite levels: Tasks 1-5.

Placeholder scan:

- This plan does not use placeholder markers or unfinished implementation instructions.

Type consistency:

- `ValidationRunStartRequest`, `ValidationRunFinishRequest`, `ValidationManualAssertions`, `ValidationRunObservation`, and `ValidationRunFinishResponse` are introduced in Task 1 and reused unchanged in Tasks 2-4.
- `run_id` is always generated by the backend and follows `vrun-YYYYMMDD-HHMMSS-<8 lowercase hex chars>`.

Execution handoff:

Plan complete and saved to `docs/superpowers/plans/2026-06-01-pilot-validation-harness-v1.md`.

Two execution options:

1. Subagent-Driven (recommended): dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution: execute tasks in this session using executing-plans, batch execution with checkpoints.
