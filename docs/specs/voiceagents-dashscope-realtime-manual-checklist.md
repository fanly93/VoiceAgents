# VoiceAgents DashScope Realtime Manual Checklist

Status: DRAFT / REAL PROVIDER OUTBOUND DEFERRED

Use this checklist only after the fake-transport proxy tests pass. Do not commit real provider credentials, raw audio, SDP, Authorization headers, tool-call tokens, or unredacted transcripts.

## Automated Evidence First

Run the fake-provider boundary tests:

```bash
./.venv/bin/python -m pytest tests/test_api_realtime_dashscope_proxy.py tests/test_realtime_dashscope_adapter.py -v
```

Expected result:

- `dashscope_realtime` client-secret metadata uses `server_websocket_proxy`.
- `/v1/realtime/dashscope/proxy/{session_id}` requires a session-bound token.
- Browser-to-proxy envelopes reject secret-bearing keys.
- Fake upstream events normalize to safe VoiceAgents events.
- No automated test calls real DashScope.

## Required Local Env

```bash
VOICEAGENTS_REALTIME_PROVIDER=dashscope_realtime
VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true
VOICEAGENTS_DASHSCOPE_API_KEY=...
VOICEAGENTS_DASHSCOPE_REALTIME_MODEL=qwen3.5-omni-flash-realtime
VOICEAGENTS_DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com
VOICEAGENTS_TRANSCRIPT_LOGGING=structured
```

Optional:

```bash
VOICEAGENTS_DASHSCOPE_REALTIME_VOICE=...
```

## Manual Scope

Current implementation exposes the browser-safe local proxy boundary and fake upstream relay. The real outbound DashScope WebSocket client dependency remains deferred until provider protocol details are verified manually.

Manual validation should confirm:

- `/v1/realtime/client-secret` returns provider `dashscope_realtime`, model `qwen3.5-omni-flash-realtime`, connection mode `server_websocket_proxy`, and a local proxy URL.
- `/v1/realtime/client-secret` rejects DashScope requests unless `VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true` is set on the local server.
- The response does not include `DASHSCOPE_API_KEY`, Authorization headers, SDP, raw audio, or client secrets.
- `/realtime-test` shows provider, model, connection mode, and safe DashScope proxy status.
- Missing, wrong, or expired proxy token attempts are rejected.
- Tool-call results use safe `tool_status` and `error_message` semantics.

## Stop Conditions

Stop and file a follow-up task if any of these happen:

- a real provider key appears in browser state, DOM, logs, screenshots, reports, or committed files;
- proxy envelope validation needs provider-specific fields that conflict with the current safety rules;
- DashScope requires a client-side credential or browser-direct connection mode;
- real outbound transport needs a new dependency or protocol loop beyond the fake-tested proxy interface.
