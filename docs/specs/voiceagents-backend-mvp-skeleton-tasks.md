# VoiceAgents Backend MVP Skeleton Tasks

Status: DRAFT
Source specs:

- `docs/roadmap/no-recording-data-plan.md`
- `docs/contracts/mvp-tool-contracts.md`
- `docs/contracts/handoff-rules.md`
- `docs/architecture/backend-technology-choice.md`

Goal: implement a mockable Python backend skeleton for the VoiceAgents phone-channel MVP without depending on real recordings, production telephony, or real merchant APIs.

Architecture: FastAPI exposes a small HTTP API. Pydantic models define tool contracts and call-flow inputs/outputs. Mock adapters implement order, logistics, RAG, and handoff tools. A deterministic call-flow service decides whether to answer, call tools, or hand off.

Tech stack: Python 3.11+, FastAPI, Pydantic, pytest.

Rules:

- Each task is single-purpose and intended to be separately commit-able.
- Each task has explicit inputs and outputs.
- Each task should include or preserve a focused test.
- Do not introduce real ASR, TTS, telephony, production merchant APIs, or real customer data.
- Keep real-call recording evaluation deferred.

---

## Phase 1: Backend Project Baseline

### Task 1.1: Add Backend Runtime Dependencies

Purpose: declare the minimal Python dependencies for a FastAPI backend skeleton.

Inputs:

- Existing `pyproject.toml`
- Approved backend stack from `docs/architecture/backend-technology-choice.md`

Outputs:

- `pyproject.toml` includes runtime dependencies: `fastapi`, `pydantic`, `uvicorn`
- `pyproject.toml` keeps pytest configuration

Steps:

1. Modify `pyproject.toml`.
2. Add dependency list under `[project]`.
3. Run `python3 -m pytest`.
4. Commit.

Validation:

```bash
python3 -m pytest
```

Expected output: existing tests pass.

Suggested commit:

```bash
git add pyproject.toml
git commit -m "chore: add backend runtime dependencies"
```

### Task 1.2: Create Backend Package Boundaries

Purpose: create empty modules that establish the backend structure without behavior.

Inputs:

- Existing `voiceagents/` package

Outputs:

- `voiceagents/contracts/__init__.py`
- `voiceagents/adapters/__init__.py`
- `voiceagents/agent/__init__.py`
- `voiceagents/api/__init__.py`

Steps:

1. Create the package directories.
2. Add empty `__init__.py` files.
3. Run `python3 -m pytest`.
4. Commit.

Validation:

```bash
python3 -m pytest
```

Expected output: existing tests pass.

Suggested commit:

```bash
git add voiceagents/contracts voiceagents/adapters voiceagents/agent voiceagents/api
git commit -m "chore: create backend package boundaries"
```

### Task 1.3: Add Backend Smoke Test Placeholder

Purpose: prove the package imports cleanly before adding behavior.

Inputs:

- `voiceagents/api/__init__.py`

Outputs:

- `tests/test_backend_package.py`

Steps:

1. Add a test that imports `voiceagents.contracts`, `voiceagents.adapters`, `voiceagents.agent`, and `voiceagents.api`.
2. Run only this test.
3. Run full pytest.
4. Commit.

Validation:

```bash
python3 -m pytest tests/test_backend_package.py
python3 -m pytest
```

Expected output: all tests pass.

Suggested commit:

```bash
git add tests/test_backend_package.py
git commit -m "test: add backend package import smoke test"
```

---

## Phase 2: Pydantic Tool Contracts

### Task 2.1: Add Shared Contract Types

Purpose: define shared enums used by all tool contracts.

Inputs:

- `docs/contracts/mvp-tool-contracts.md`
- `docs/contracts/handoff-rules.md`

Outputs:

- `voiceagents/contracts/common.py`
- `tests/test_contract_common.py`

Required model outputs:

- `ToolErrorCode`: `not_found`, `invalid_input`, `permission_denied`, `system_error`, `no_answer`, `low_confidence`
- `HandoffMode`: `live_transfer`, `callback`, `ticket`
- `HandoffReason`: values from `docs/contracts/handoff-rules.md`

Steps:

1. Write tests that import the enum values.
2. Run the tests and confirm they fail before implementation.
3. Implement the enums in `voiceagents/contracts/common.py`.
4. Run the focused tests.
5. Commit.

Validation:

```bash
python3 -m pytest tests/test_contract_common.py
```

Expected output: enum tests pass.

Suggested commit:

```bash
git add voiceagents/contracts/common.py tests/test_contract_common.py
git commit -m "feat: add shared contract enums"
```

### Task 2.2: Add Order Lookup Contract

Purpose: encode the approved `lookup_order` input/output shape.

Inputs:

- Contract section `lookup_order` in `docs/contracts/mvp-tool-contracts.md`

Outputs:

- `voiceagents/contracts/order.py`
- `tests/test_order_contract.py`

Required input model:

- `merchant_id: str`
- `order_id: str`

Required output model:

- `ok: bool`
- `order_exists: bool`
- `status: str | None`
- `user_summary: str`
- `safe_fields: dict[str, str]`
- `error_code: ToolErrorCode | None`

Steps:

1. Write a test that constructs a successful order response.
2. Write a test that constructs a `not_found` response.
3. Run tests and confirm failure before implementation.
4. Implement Pydantic models.
5. Run focused tests.
6. Commit.

Validation:

```bash
python3 -m pytest tests/test_order_contract.py
```

Expected output: success and error response tests pass.

Suggested commit:

```bash
git add voiceagents/contracts/order.py tests/test_order_contract.py
git commit -m "feat: add order lookup contract"
```

### Task 2.3: Add Logistics Lookup Contract

Purpose: encode the approved `lookup_logistics` input/output shape.

Inputs:

- Contract section `lookup_logistics` in `docs/contracts/mvp-tool-contracts.md`

Outputs:

- `voiceagents/contracts/logistics.py`
- `tests/test_logistics_contract.py`

Required input model:

- `merchant_id: str`
- `order_id: str`

Required output model:

- `ok: bool`
- `status: str | None`
- `latest_event: str | None`
- `estimated_delivery: str | None`
- `carrier: str | None`
- `user_summary: str`
- `error_code: ToolErrorCode | None`

Steps:

1. Write a test that constructs an in-transit response.
2. Write a test that constructs a `system_error` response.
3. Run tests and confirm failure before implementation.
4. Implement Pydantic models.
5. Run focused tests.
6. Commit.

Validation:

```bash
python3 -m pytest tests/test_logistics_contract.py
```

Expected output: success and error response tests pass.

Suggested commit:

```bash
git add voiceagents/contracts/logistics.py tests/test_logistics_contract.py
git commit -m "feat: add logistics lookup contract"
```

### Task 2.4: Add Product Knowledge Contract

Purpose: encode the approved `query_product_knowledge` input/output shape.

Inputs:

- Contract section `query_product_knowledge` in `docs/contracts/mvp-tool-contracts.md`

Outputs:

- `voiceagents/contracts/knowledge.py`
- `tests/test_knowledge_contract.py`

Required input model:

- `merchant_id: str`
- `locale: str`
- `query: str`

Required output model:

- `ok: bool`
- `short_answer: str`
- `citations: list[str]`
- `confidence: float`
- `handoff_recommended: bool`
- `error_code: ToolErrorCode | None`

Steps:

1. Write a test that accepts a high-confidence RAG answer.
2. Write a test that rejects confidence outside 0-1.
3. Run tests and confirm failure before implementation.
4. Implement Pydantic models.
5. Run focused tests.
6. Commit.

Validation:

```bash
python3 -m pytest tests/test_knowledge_contract.py
```

Expected output: confidence validation works.

Suggested commit:

```bash
git add voiceagents/contracts/knowledge.py tests/test_knowledge_contract.py
git commit -m "feat: add product knowledge contract"
```

### Task 2.5: Add Handoff Contract

Purpose: encode the approved `handoff_to_human` input/output shape.

Inputs:

- Contract section `handoff_to_human` in `docs/contracts/mvp-tool-contracts.md`
- Handoff context fields from `docs/contracts/handoff-rules.md`

Outputs:

- `voiceagents/contracts/handoff.py`
- `tests/test_handoff_contract.py`

Required input model:

- `call_id: str`
- `merchant_id: str`
- `intent_primary: str`
- `order_id_candidate: str | None`
- `summary: str`
- `tools_called: list[str]`
- `handoff_reason: HandoffReason`
- `recommended_next_step: str`

Required output model:

- `ok: bool`
- `handoff_id: str`
- `mode: HandoffMode`

Steps:

1. Write a test that constructs a live transfer request.
2. Write a test that requires a non-empty summary.
3. Run tests and confirm failure before implementation.
4. Implement Pydantic models.
5. Run focused tests.
6. Commit.

Validation:

```bash
python3 -m pytest tests/test_handoff_contract.py
```

Expected output: handoff models validate required fields.

Suggested commit:

```bash
git add voiceagents/contracts/handoff.py tests/test_handoff_contract.py
git commit -m "feat: add human handoff contract"
```

---

## Phase 3: Mock Tool Adapters

### Task 3.1: Add Mock Order Adapter

Purpose: provide a deterministic in-memory order lookup for tests and local demos.

Inputs:

- `LookupOrderRequest`
- `LookupOrderResponse`
- Redacted sample order ID: `ORDER-REDACTED-001`

Outputs:

- `voiceagents/adapters/order.py`
- `tests/test_mock_order_adapter.py`

Behavior:

- Known order returns `ok=True`, `order_exists=True`.
- Unknown order returns `ok=False`, `order_exists=False`, `error_code=not_found`.

Steps:

1. Write known-order and unknown-order tests.
2. Run tests and confirm failure before implementation.
3. Implement `MockOrderAdapter.lookup_order`.
4. Run focused tests.
5. Commit.

Validation:

```bash
python3 -m pytest tests/test_mock_order_adapter.py
```

Expected output: both adapter paths pass.

Suggested commit:

```bash
git add voiceagents/adapters/order.py tests/test_mock_order_adapter.py
git commit -m "feat: add mock order adapter"
```

### Task 3.2: Add Mock Logistics Adapter

Purpose: provide deterministic logistics responses for tests and local demos.

Inputs:

- `LookupLogisticsRequest`
- `LookupLogisticsResponse`
- Redacted sample order ID: `ORDER-REDACTED-001`

Outputs:

- `voiceagents/adapters/logistics.py`
- `tests/test_mock_logistics_adapter.py`

Behavior:

- Known order returns `ok=True`, `status=in_transit`.
- Unknown order returns `ok=False`, `error_code=not_found`.

Steps:

1. Write known-order and unknown-order tests.
2. Run tests and confirm failure before implementation.
3. Implement `MockLogisticsAdapter.lookup_logistics`.
4. Run focused tests.
5. Commit.

Validation:

```bash
python3 -m pytest tests/test_mock_logistics_adapter.py
```

Expected output: both adapter paths pass.

Suggested commit:

```bash
git add voiceagents/adapters/logistics.py tests/test_mock_logistics_adapter.py
git commit -m "feat: add mock logistics adapter"
```

### Task 3.3: Add Mock Knowledge Adapter

Purpose: provide deterministic product knowledge responses for product usage tests.

Inputs:

- `ProductKnowledgeRequest`
- `ProductKnowledgeResponse`
- Query text, merchant ID, locale

Outputs:

- `voiceagents/adapters/knowledge.py`
- `tests/test_mock_knowledge_adapter.py`

Behavior:

- Query containing `wash` returns wig-care answer with confidence above 0.8.
- Unknown query returns `ok=False`, `error_code=no_answer`, `handoff_recommended=True`.

Steps:

1. Write known-query and unknown-query tests.
2. Run tests and confirm failure before implementation.
3. Implement `MockKnowledgeAdapter.query`.
4. Run focused tests.
5. Commit.

Validation:

```bash
python3 -m pytest tests/test_mock_knowledge_adapter.py
```

Expected output: answer and no-answer paths pass.

Suggested commit:

```bash
git add voiceagents/adapters/knowledge.py tests/test_mock_knowledge_adapter.py
git commit -m "feat: add mock knowledge adapter"
```

### Task 3.4: Add Mock Handoff Adapter

Purpose: return a deterministic handoff ID and mode for handoff tests.

Inputs:

- `HandoffRequest`

Outputs:

- `voiceagents/adapters/handoff.py`
- `tests/test_mock_handoff_adapter.py`

Behavior:

- Valid request returns `ok=True`, `handoff_id=HANDOFF-REDACTED`, `mode=live_transfer`.

Steps:

1. Write a test for a valid handoff request.
2. Run test and confirm failure before implementation.
3. Implement `MockHandoffAdapter.handoff`.
4. Run focused test.
5. Commit.

Validation:

```bash
python3 -m pytest tests/test_mock_handoff_adapter.py
```

Expected output: handoff adapter test passes.

Suggested commit:

```bash
git add voiceagents/adapters/handoff.py tests/test_mock_handoff_adapter.py
git commit -m "feat: add mock handoff adapter"
```

---

## Phase 4: MVP Call-Flow State Machine

### Task 4.1: Add Call-Flow Input and Output Models

Purpose: define the single input/output boundary for the MVP call-flow service.

Inputs:

- Handoff rules from `docs/contracts/handoff-rules.md`
- Tool contracts from Phase 2

Outputs:

- `voiceagents/agent/models.py`
- `tests/test_call_flow_models.py`

Required input model:

- `call_id: str`
- `merchant_id: str`
- `locale: str`
- `intent: str`
- `utterance: str`
- `order_id_candidate: str | None`
- `order_id_confirmed: bool`
- `asr_confidence: float`
- `customer_requested_human: bool`

Required output model:

- `resolved: bool`
- `response_text: str`
- `tools_called: list[str]`
- `handoff_required: bool`
- `handoff_reason: str`
- `handoff_id: str | None`

Steps:

1. Write tests for valid input and output models.
2. Write a test rejecting `asr_confidence > 1`.
3. Run tests and confirm failure before implementation.
4. Implement Pydantic models.
5. Run focused tests.
6. Commit.

Validation:

```bash
python3 -m pytest tests/test_call_flow_models.py
```

Expected output: call-flow models validate.

Suggested commit:

```bash
git add voiceagents/agent/models.py tests/test_call_flow_models.py
git commit -m "feat: add call flow models"
```

### Task 4.2: Add Low ASR Confidence Handoff Path

Purpose: hand off immediately when ASR confidence is too low.

Inputs:

- `CallFlowInput` with `asr_confidence < 0.6`
- `MockHandoffAdapter`

Outputs:

- `voiceagents/agent/service.py`
- `tests/test_call_flow_low_confidence.py`

Behavior:

- `handoff_required=True`
- `handoff_reason=low_asr_confidence`
- `resolved=False`
- `handoff_id` is set

Steps:

1. Write a test for low ASR confidence.
2. Run test and confirm failure before implementation.
3. Implement minimal `CallFlowService.handle`.
4. Run focused test.
5. Commit.

Validation:

```bash
python3 -m pytest tests/test_call_flow_low_confidence.py
```

Expected output: low-confidence calls hand off.

Suggested commit:

```bash
git add voiceagents/agent/service.py tests/test_call_flow_low_confidence.py
git commit -m "feat: hand off low confidence calls"
```

### Task 4.3: Add Order Status Success Path

Purpose: resolve confirmed order-status calls through the order adapter.

Inputs:

- `intent=order_status`
- `order_id_candidate=ORDER-REDACTED-001`
- `order_id_confirmed=True`
- `asr_confidence >= 0.6`

Outputs:

- Updated `voiceagents/agent/service.py`
- `tests/test_call_flow_order_status.py`

Behavior:

- Calls `lookup_order`
- `resolved=True`
- `handoff_required=False`
- `response_text` includes safe order summary

Steps:

1. Write order-status success test.
2. Run test and confirm failure before implementation.
3. Implement order-status branch.
4. Run focused test.
5. Commit.

Validation:

```bash
python3 -m pytest tests/test_call_flow_order_status.py
```

Expected output: confirmed known order is resolved.

Suggested commit:

```bash
git add voiceagents/agent/service.py tests/test_call_flow_order_status.py
git commit -m "feat: resolve order status calls"
```

### Task 4.4: Add Logistics Success Path

Purpose: resolve confirmed logistics calls through the logistics adapter.

Inputs:

- `intent=logistics_tracking`
- `order_id_candidate=ORDER-REDACTED-001`
- `order_id_confirmed=True`
- `asr_confidence >= 0.6`

Outputs:

- Updated `voiceagents/agent/service.py`
- `tests/test_call_flow_logistics.py`

Behavior:

- Calls `lookup_logistics`
- `resolved=True`
- `handoff_required=False`
- `response_text` includes safe logistics summary

Steps:

1. Write logistics success test.
2. Run test and confirm failure before implementation.
3. Implement logistics branch.
4. Run focused test.
5. Commit.

Validation:

```bash
python3 -m pytest tests/test_call_flow_logistics.py
```

Expected output: confirmed known logistics request is resolved.

Suggested commit:

```bash
git add voiceagents/agent/service.py tests/test_call_flow_logistics.py
git commit -m "feat: resolve logistics tracking calls"
```

### Task 4.5: Add Product Knowledge Success and No-Answer Handoff Paths

Purpose: answer known product questions and hand off unknown product questions.

Inputs:

- `intent=product_usage`
- `utterance` containing known query such as `How should I wash my wig?`
- Unknown product query

Outputs:

- Updated `voiceagents/agent/service.py`
- `tests/test_call_flow_product_knowledge.py`

Behavior:

- Known query resolves with concise answer.
- Unknown query hands off with `handoff_reason=rag_low_confidence`.

Steps:

1. Write known product question test.
2. Write unknown product question handoff test.
3. Run tests and confirm failure before implementation.
4. Implement product knowledge branch.
5. Run focused tests.
6. Commit.

Validation:

```bash
python3 -m pytest tests/test_call_flow_product_knowledge.py
```

Expected output: both product knowledge paths pass.

Suggested commit:

```bash
git add voiceagents/agent/service.py tests/test_call_flow_product_knowledge.py
git commit -m "feat: handle product knowledge calls"
```

### Task 4.6: Add Mandatory Handoff Paths

Purpose: encode explicit handoff triggers that do not require tool calls.

Inputs:

- `customer_requested_human=True`
- `intent=complaint`
- `intent=return_exchange_refund`
- Unsupported intent

Outputs:

- Updated `voiceagents/agent/service.py`
- `tests/test_call_flow_handoff_rules.py`

Behavior:

- Customer human request uses `customer_requests_human`.
- Complaint uses `complaint_or_angry_customer`.
- Return/refund uses `refund_or_return_exception`.
- Unsupported intent uses `unsupported_intent`.

Steps:

1. Write four handoff-rule tests.
2. Run tests and confirm failure before implementation.
3. Implement explicit handoff branches.
4. Run focused tests.
5. Commit.

Validation:

```bash
python3 -m pytest tests/test_call_flow_handoff_rules.py
```

Expected output: mandatory handoff paths pass.

Suggested commit:

```bash
git add voiceagents/agent/service.py tests/test_call_flow_handoff_rules.py
git commit -m "feat: add mandatory handoff rules"
```

---

## Phase 5: FastAPI Service Shell

### Task 5.1: Add FastAPI App Factory

Purpose: create a minimal app object without routes.

Inputs:

- FastAPI dependency from Phase 1

Outputs:

- `voiceagents/api/app.py`
- `tests/test_api_app.py`

Behavior:

- `create_app()` returns a FastAPI app.
- `GET /health` returns `{"status": "ok"}`.

Steps:

1. Write health endpoint test using FastAPI `TestClient`.
2. Run test and confirm failure before implementation.
3. Implement `create_app` and `/health`.
4. Run focused test.
5. Commit.

Validation:

```bash
python3 -m pytest tests/test_api_app.py
```

Expected output: health endpoint returns 200.

Suggested commit:

```bash
git add voiceagents/api/app.py tests/test_api_app.py
git commit -m "feat: add FastAPI app shell"
```

### Task 5.2: Add Call-Flow Simulation Endpoint

Purpose: expose the deterministic call-flow service over HTTP for local testing.

Inputs:

- `CallFlowInput`
- `CallFlowOutput`
- `CallFlowService`

Outputs:

- Updated `voiceagents/api/app.py`
- `tests/test_api_call_flow.py`

Endpoint:

- `POST /v1/calls/simulate`

Behavior:

- Accepts call-flow JSON input.
- Returns call-flow JSON output.
- Uses mock adapters only.

Steps:

1. Write API test for a product usage request.
2. Run test and confirm failure before implementation.
3. Add endpoint.
4. Run focused test.
5. Commit.

Validation:

```bash
python3 -m pytest tests/test_api_call_flow.py
```

Expected output: simulation endpoint returns deterministic response.

Suggested commit:

```bash
git add voiceagents/api/app.py tests/test_api_call_flow.py
git commit -m "feat: add call simulation endpoint"
```

### Task 5.3: Add API Entrypoint Module

Purpose: provide a standard import target for local uvicorn.

Inputs:

- `voiceagents/api/app.py`

Outputs:

- `voiceagents/api/main.py`
- `tests/test_api_main.py`

Behavior:

- `voiceagents.api.main:app` exists and is importable.

Steps:

1. Write import test.
2. Run test and confirm failure before implementation.
3. Implement `app = create_app()`.
4. Run focused test.
5. Commit.

Validation:

```bash
python3 -m pytest tests/test_api_main.py
```

Expected output: app import succeeds.

Suggested commit:

```bash
git add voiceagents/api/main.py tests/test_api_main.py
git commit -m "feat: add API entrypoint"
```

### Task 5.4: Document Local Backend Usage

Purpose: document how to run and test the backend skeleton.

Inputs:

- Existing `README.md`
- API modules from Phase 5

Outputs:

- Updated `README.md`

Required content:

- Install dependency guidance.
- Test command.
- Validation command.
- Uvicorn command: `uvicorn voiceagents.api.main:app --reload`
- Example `POST /v1/calls/simulate` payload.

Steps:

1. Update README.
2. Run `python3 -m pytest`.
3. Run sample validator.
4. Commit.

Validation:

```bash
python3 -m pytest
python3 scripts/validate_call_evaluations.py data/call-evaluations/sample.json
```

Expected output: all tests and sample validation pass.

Suggested commit:

```bash
git add README.md
git commit -m "docs: document backend skeleton usage"
```

---

## Phase 6: Review, Quality Gate, and Handoff

### Task 6.1: Add Architecture Notes for the Backend Skeleton

Purpose: document the implemented module boundaries for future maintainers.

Inputs:

- Implemented modules from Phases 1-5
- Existing `docs/architecture/backend-technology-choice.md`

Outputs:

- `docs/architecture/backend-mvp-skeleton.md`

Required content:

- Module map.
- Request flow from API to service to adapters.
- Explicit non-goals: no production telephony, no real merchant APIs, no real recordings.

Steps:

1. Add architecture note.
2. Run `python3 -m pytest`.
3. Commit.

Validation:

```bash
python3 -m pytest
```

Expected output: all tests pass.

Suggested commit:

```bash
git add docs/architecture/backend-mvp-skeleton.md
git commit -m "docs: add backend skeleton architecture notes"
```

### Task 6.2: Run Full Verification

Purpose: create a clean final verification point before review.

Inputs:

- Completed Phases 1-6.1

Outputs:

- Terminal evidence for final review

Steps:

1. Run full tests.
2. Run evaluation validator.
3. Check git status.
4. Commit any remaining docs or metadata changes if needed.

Validation:

```bash
python3 -m pytest
python3 scripts/validate_call_evaluations.py data/call-evaluations/sample.json
git status --short --branch
```

Expected output:

- All tests pass.
- Sample validation passes.
- No unexpected untracked files.

Suggested commit:

```bash
git add .
git commit -m "chore: finalize backend skeleton verification"
```

Only run the commit if there are actual remaining changes.

### Task 6.3: Run gstack Review

Purpose: review the completed implementation before pushing or opening further work.

Inputs:

- Completed implementation commits
- This task plan

Outputs:

- Review findings or approval

Steps:

1. Invoke `$gstack-review` on the final diff.
2. Address any findings in separate commits.
3. Re-run full verification.
4. Push to `origin/main` only after review findings are resolved.

Validation:

```bash
python3 -m pytest
python3 scripts/validate_call_evaluations.py data/call-evaluations/sample.json
git status --short --branch
```

Expected output: tests pass, validator passes, branch is ready to push.

Suggested commit:

```bash
git commit -m "fix: address backend skeleton review findings"
```

Only run this commit if review produces code or doc changes.

---

## Phase 7: Local E2E Examples and Smoke Runner

Purpose: make the implemented backend skeleton easy to run locally and verify through representative end-to-end HTTP calls before any voice-model phase begins.

### Phase 7 In Scope

- Add reusable JSON request examples for `POST /v1/calls/simulate`.
- Add a local smoke script that calls `/health` and `/v1/calls/simulate`.
- Document how to start the API and run the examples.
- Add tests that keep example payloads compatible with `CallFlowInput` and the current API schema.

### Phase 7 Out of Scope

- No voice-model integration spec.
- No OpenAI, ASR, TTS, or realtime voice provider dependency.
- No telephony provider integration.
- No phone-number provisioning or inbound/outbound calling.
- No audio file input, audio file output, or recording processing.
- No production merchant API integration.
- No real customer data, raw recordings, or PII.

### Task 7.1: Add Call Simulation Request Examples

Purpose: provide checked-in payloads that represent the main MVP call-flow paths.

Inputs:

- Existing `CallFlowInput` model
- Current mock adapter behavior

Outputs:

- `examples/call-simulations/product-usage.json`
- `examples/call-simulations/order-status.json`
- `examples/call-simulations/logistics-tracking.json`
- `examples/call-simulations/customer-requests-human.json`
- `examples/call-simulations/low-asr-confidence.json`

Validation:

```bash
python3 -m pytest tests/test_example_call_payloads.py
```

Expected output: all example payloads validate against `CallFlowInput` and return HTTP 200 from the simulation endpoint.

Suggested commit:

```bash
git add examples/call-simulations tests/test_example_call_payloads.py
git commit -m "test: validate call simulation examples"
```

### Task 7.2: Add Local API Smoke Script

Purpose: provide a repeatable local command that verifies a running API server.

Inputs:

- Running FastAPI server
- Example request payloads from Task 7.1

Outputs:

- `scripts/smoke_api.py`

Validation:

```bash
python3 scripts/smoke_api.py --base-url http://127.0.0.1:8000
```

Expected output: `/health` passes and each example call returns a successful JSON response.

Suggested commit:

```bash
git add scripts/smoke_api.py
git commit -m "chore: add local API smoke script"
```

### Task 7.3: Document Local E2E Usage

Purpose: make local backend verification discoverable from the project README.

Inputs:

- Existing `README.md`
- Example request payloads
- Smoke script

Outputs:

- Updated `README.md`

Required content:

- API startup command.
- Example payload directory.
- Smoke script command.
- Explicit note that this phase does not include voice-model, ASR, TTS, telephony, or audio-file processing.

Validation:

```bash
python3 -m pytest
python3 scripts/validate_call_evaluations.py data/call-evaluations/sample.json
```

Expected output: all tests pass and sample validation passes.

Suggested commit:

```bash
git add README.md
git commit -m "docs: document local API smoke testing"
```

### Task 7.4: Run Final Verification

Purpose: confirm the example and smoke-script phase did not change backend behavior.

Inputs:

- Completed Phase 7.1-7.3

Outputs:

- Terminal verification evidence

Validation:

```bash
python3 -m pytest
python3 scripts/validate_call_evaluations.py data/call-evaluations/sample.json
git status --short --branch
```

Expected output: tests pass, sample validation passes, and no unexpected files remain.

---

## Self-Review

Spec coverage:

- Python backend stack: Phase 1 and Phase 5.
- Pydantic tool contracts: Phase 2.
- Mock order/logistics/RAG/handoff adapters: Phase 3.
- MVP call-flow state machine: Phase 4.
- Unit tests for success, low confidence, tool error, and handoff paths: Phases 3-5.
- Real recordings remain deferred: Phase 6 architecture notes and source roadmap.

Known non-goals:

- No real ASR/TTS.
- No production telephony.
- No real merchant API credentials.
- No raw recordings or PII.
- No dashboard UI.
