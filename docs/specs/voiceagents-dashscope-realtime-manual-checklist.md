# VoiceAgents DashScope Realtime Manual Checklist

Status: DRAFT / REAL PROVIDER PYTEST SMOKE AVAILABLE

Use this checklist only after the fake-transport proxy tests pass. Do not commit real provider credentials, raw audio, SDP, Authorization headers, tool-call tokens, or unredacted transcripts.

## Automated Evidence First

Run the fake-provider boundary tests:

```bash
./.venv/bin/python -m pytest tests/test_realtime_outbound_contracts.py tests/test_realtime_dashscope_adapter.py tests/test_realtime_dashscope_transport.py tests/test_api_realtime_dashscope_proxy.py -v
```

Expected result:

- `dashscope_realtime` client-secret metadata uses `server_websocket_proxy`.
- `/v1/realtime/dashscope/proxy/{session_id}` requires a session-bound token.
- Browser-to-proxy envelopes reject secret-bearing keys.
- Fake upstream events normalize to safe VoiceAgents events.
- The real outbound transport is fake-client tested and does not open network sockets unless the live-test flag is explicitly enabled.
- `/realtime-test` loads the DashScope browser adapter and does not relay DashScope provider events to `/v1/realtime/event`.
- `tests/test_realtime_dashscope_live.py` skips by default and calls real DashScope only when the live-test flag and API key are configured.

## Required Local Env

```bash
./.venv/bin/python -m pip install websockets
VOICEAGENTS_REALTIME_PROVIDER=dashscope_realtime
VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true
VOICEAGENTS_DASHSCOPE_API_KEY=...
VOICEAGENTS_DASHSCOPE_REALTIME_MODEL=qwen3.5-omni-flash-realtime
VOICEAGENTS_DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com
VOICEAGENTS_TRANSCRIPT_LOGGING=structured
VOICEAGENTS_RUN_DASHSCOPE_LIVE_TESTS=true
```

Optional:

```bash
VOICEAGENTS_DASHSCOPE_REALTIME_VOICE=...
```

If the local environment uses a SOCKS proxy, install proxy support for the optional WebSocket client:

```bash
./.venv/bin/python -m pip install python-socks
```

Run the real model smoke test:

```bash
./.venv/bin/python -m pytest tests/test_realtime_dashscope_live.py -q
```

## Manual Scope

Current implementation exposes the browser-safe local proxy boundary, fake upstream relay, server-side DashScope protocol mapping, lazy optional `websockets` outbound transport, provider tool-call result relay, and `/realtime-test` DashScope browser adapter wiring. Default automated tests use fake clients and must not open network connections; the live pytest smoke is opt-in.

Manual validation should confirm:

- `/v1/realtime/client-secret` returns provider `dashscope_realtime`, model `qwen3.5-omni-flash-realtime`, connection mode `server_websocket_proxy`, and a local proxy URL.
- `/v1/realtime/client-secret` rejects DashScope requests unless `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true` is set on the local server.
- The response does not include `DASHSCOPE_API_KEY`, Authorization headers, SDP, raw audio, or client secrets.
- `/realtime-test` shows provider, model, connection mode, and safe DashScope proxy status.
- Missing, wrong, or expired proxy token attempts are rejected.
- One real voice interaction produces safe transcript/assistant events on the page.
- One real provider tool call routes through the backend and sends a safe tool result back to DashScope.
- Tool-call results use safe `tool_status` and `error_message` semantics.
- Browser state, DOM, logs, validation report text, and committed files do not contain API keys, Authorization headers, tool-call tokens, raw audio, SDP, raw tool arguments, or raw provider payload dumps.

## Stop Conditions

Stop and file a follow-up task if any of these happen:

- a real provider key appears in browser state, DOM, logs, screenshots, reports, or committed files;
- proxy envelope validation needs provider-specific fields that conflict with the current safety rules;
- DashScope requires a client-side credential or browser-direct connection mode;
- real outbound transport requires network behavior that cannot be fake-tested through the transport interface.
