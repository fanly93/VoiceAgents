# Plan Without Pilot Call Recordings

Status: ACTIVE

Pilot call recordings are not available yet. VoiceAgents should not block on them, but the project must separate what can move forward from what requires real call data.

## Continue Now

- Keep Python as the primary backend language.
- Maintain the call evaluation schema and synthetic redacted sample corpus.
- Define MVP tool contracts for order lookup, logistics lookup, RAG retrieval, and human handoff.
- Build mock adapters for tool contracts in the next implementation phase.
- Design the phone-agent state machine around explicit handoff rules.
- Prepare privacy-safe import instructions for future recordings.

## Defer Until Recordings Exist

- Real ASR accuracy evaluation.
- Real order-number recognition benchmarks.
- Real intent distribution measurement.
- Real customer dissatisfaction or complaint classification.
- Real handoff-rate estimate.

## Next Spec Recommendation

The next spec should not depend on recordings. It should implement a mockable Python backend skeleton:

- FastAPI service shell.
- Pydantic schemas for the approved tool contracts.
- Mock order/logistics/RAG/handoff adapters.
- Agent state machine for the MVP call flow.
- Unit tests for success, low confidence, tool error, and handoff paths.

This lets engineering proceed while preserving the decision that real-call evaluation remains required before production pilot launch.

