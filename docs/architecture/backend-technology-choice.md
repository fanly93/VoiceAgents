# Backend Technology Choice

Status: APPROVED

## Decision

Use Python as the primary backend language for VoiceAgents.

Recommended production backend stack:

- FastAPI for HTTP APIs and webhook endpoints.
- Pydantic for request/response schemas and tool contracts.
- pytest for automated tests.
- Plain service modules for agent orchestration, tool calls, RAG calls, and handoff decisions.

## Rationale

VoiceAgents is primarily an AI orchestration product. The backend needs to coordinate:

- ASR/TTS providers.
- LLM and agent control loops.
- RAG retrieval and answer shaping.
- Order/logistics/refund tool calls.
- Offline evaluation and annotation workflows.
- Handoff decisions and support context generation.

Python has the strongest ecosystem and fastest iteration loop for these jobs.

## Why Not Other Primary Backends

Node/TypeScript is reasonable for realtime dashboards and frontend-heavy tooling, but it should not be the primary backend for the first VoiceAgents MVP because the main risk is AI/voice/RAG orchestration, not UI state.

Go or Rust may become useful later for low-latency media gateway components, but they would slow down the current MVP and evaluation phase.

Java/Kotlin is only worth considering if the existing company SaaS backend is already built on that stack and integration cost dominates AI iteration speed.

## Current Phase 0 Implementation

The Phase 0 validation tooling is implemented in Python:

- `voiceagents/call_evaluation.py`
- `scripts/validate_call_evaluations.py`
- `tests/`

This keeps the evaluation baseline aligned with the future backend language.

