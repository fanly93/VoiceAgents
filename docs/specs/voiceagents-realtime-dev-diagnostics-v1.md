# VoiceAgents Realtime Dev Diagnostics v1 Spec

Status: IMPLEMENTED / READY FOR REVIEW
Date: 2026-06-02
Branch: `feat/realtime-dev-diagnostics`

## Goal

Add a local developer diagnostics surface for realtime voice validation so developers and testers can tell why a run will not start or why it failed before reaching the voice scenario.

This task combines the next two backend priorities:

- real voice validation troubleshooting,
- realtime run preflight checks.

It does not add report generation, public sharing, merchant-facing UI, support workbench UI, or new model/provider integration.

## Users

Primary users:

- backend developer running `/realtime-test`,
- tester validating OpenAI Realtime behavior locally.

## Problem

The current realtime MVP can run local mock smoke tests and real OpenAI Realtime browser tests, but failed real-mode runs are still hard to classify quickly.

Common failure classes include:

- provider set to an unsupported value,
- OpenAI realtime dev endpoint gate disabled,
- missing server-side `OPENAI_API_KEY`,
- invalid transcript logging mode,
- invalid rate-limit config,
- local API server not reachable,
- browser microphone / WebRTC / data-channel failure.

The system should expose safe diagnostics before a client-secret is minted and before OpenAI is called.

## Scope

### Backend Diagnostics Endpoint

Add:

```text
GET /v1/realtime/dev-diagnostics
```

The endpoint returns safe server-side diagnostics without:

- calling OpenAI,
- creating a realtime session,
- creating a `tool_call_token`,
- returning any secret values,
- writing event logs,
- writing validation artifacts.

Response fields:

- `overall_status`: `pass`, `warn`, or `fail`
- `provider`: current realtime provider string
- `checks`: ordered list of checks

Each check has:

- `name`
- `status`: `pass`, `warn`, or `fail`
- `summary`
- `detail`
- `remediation`

Required checks:

- `provider_supported`
- `openai_dev_gate` when provider is `openai_realtime`
- `openai_api_key` when provider is `openai_realtime`
- `openai_model`
- `openai_voice` when provider is `openai_realtime`
- `transcript_logging`
- `client_secret_rate_limit`

### Realtime Test Page Diagnostics

Add a minimal diagnostics control to `/realtime-test`:

- `Run Diagnostics` button,
- diagnostics panel,
- safe rendering of status/check names/summaries/remediation.

The page must not render:

- `OPENAI_API_KEY` value,
- client secret,
- tool token,
- Authorization header,
- SDP,
- raw audio.

Browser-side runtime failures should continue to append safe hints to Provider Events for:

- `getUserMedia` failure,
- OpenAI SDP exchange failure,
- data channel error/close,
- provider error,
- event log error.

### Local Diagnostics Script

Add a local script:

```bash
./.venv/bin/python scripts/diagnose_realtime_dev.py --base-url http://127.0.0.1:8000
```

The script checks:

- `/health`,
- `/v1/realtime/dev-diagnostics`,
- prints one-line check results,
- exits non-zero when `overall_status` is `fail`.

The script must not print secret values.

## Non-Goals

- No Validation Harness CLI.
- No report viewer/report output changes.
- No public sharing/auth.
- No merchant-facing frontend.
- No support workbench.
- No new provider implementation.
- No OpenAI network call during diagnostics.
- No fake microphone automation.

## Acceptance Criteria

1. `GET /v1/realtime/dev-diagnostics` returns `pass` in mock mode with safe checks.
2. The diagnostics endpoint returns `fail` for unsupported provider values without crashing the app.
3. OpenAI realtime mode fails diagnostics when the dev gate is disabled.
4. OpenAI realtime mode fails diagnostics when `OPENAI_API_KEY` is missing.
5. Invalid `VOICEAGENTS_TRANSCRIPT_LOGGING` and invalid `VOICEAGENTS_REALTIME_CLIENT_SECRET_RATE_LIMIT` are diagnosed with remediation.
6. `/realtime-test` includes and exercises the diagnostics button/panel without exposing secrets.
7. `scripts/diagnose_realtime_dev.py` exits `0` on pass/warn and exits `1` on fail.
8. Focused tests pass.

## Implementation Notes

Implemented on `feat/realtime-dev-diagnostics`.

Added:

- `voiceagents/realtime/diagnostics.py`
- `GET /v1/realtime/dev-diagnostics`
- `Run Diagnostics` on `/realtime-test`
- `scripts/diagnose_realtime_dev.py`

Focused validation:

```bash
./.venv/bin/python -m pytest tests/test_realtime_diagnostics.py tests/test_api_realtime_diagnostics.py tests/test_api_realtime_test_page.py tests/test_realtime_test_page_failure_modes.py tests/test_diagnose_realtime_dev_cli.py -v
```
