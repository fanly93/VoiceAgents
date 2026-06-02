# VoiceAgents Realtime Tool Error Semantics v1 Spec

Status: DRAFT / IN PROGRESS
Date: 2026-06-02
Branch: `feat/realtime-tool-error-semantics`

## Goal

Strengthen realtime tool-call stability and error semantics for the four approved backend tools:

- `lookup_order`
- `lookup_logistics`
- `query_product_knowledge`
- `handoff_to_human`

The realtime model and browser adapter should receive predictable safe tool responses, and backend logs should capture safe status semantics without storing raw arguments or secrets.

## Why Now

Realtime Voice Dev Diagnostics v1 now helps developers identify setup and provider failures before a session starts. The next reliability gap is what happens after a model requests a backend tool:

- unknown tools and invalid arguments currently return generic HTTP details,
- adapter exceptions can escape as server errors,
- `tool_status` in event logs is always `completed`,
- frontend/provider logic cannot distinguish completed tool results from safe tool failures with a stable response field.

## Scope

### Contract

Extend `RealtimeToolCallResponse` with:

- `tool_status`: `completed`, `failed`, or `handoff_required`
- `error_message`: safe string or `null`

Existing fields remain:

- `ok`
- `tool_name`
- `result`
- `safe_summary`
- `handoff_required`
- `handoff_reason`
- `error_code`

### Router Behavior

For successful tool calls:

- `tool_status=completed`
- `error_message=null`

For tool calls that return a safe business/tool failure from an adapter:

- `ok=false`
- `tool_status=failed` unless handoff is required
- `safe_summary` remains a user-safe sentence
- `error_code` is set
- `error_message` is safe and does not include raw arguments

For handoff tool calls:

- `tool_status=handoff_required`
- `handoff_required=true`

For adapter exceptions:

- do not leak exception text,
- return a safe failed response with `error_code=system_error`,
- `safe_summary` tells the user the tool had a temporary problem and a human should review if needed.

### API Error Responses

For request-level errors, return structured safe HTTP details:

- unknown tool: HTTP 400
- invalid arguments: HTTP 422
- invalid token/session binding: HTTP 403

Detail shape:

```json
{
  "error_code": "unknown_tool",
  "message": "Unknown realtime tool.",
  "tool_name": "run_shell"
}
```

Do not include raw arguments, Authorization headers, tool tokens, API keys, SDP, raw audio, or exception traces.

### Event Logging

`/v1/realtime/tool-call` must log:

- `tool_status` from the response,
- `error_code` / safe error semantics through `tool_result_summary`,
- no raw arguments.

## Non-Goals

- No new provider integration.
- No changes to report viewer or validation reports.
- No merchant-facing or support-workbench UI.
- No persistence schema migration.
- No retry framework.
- No timeout implementation unless needed for safe exception handling.

## Acceptance Criteria

1. `RealtimeToolCallResponse` includes `tool_status` and `error_message`.
2. Successful order/logistics/product knowledge calls return `tool_status=completed`.
3. Not-found order/logistics calls return safe failed responses with stable error semantics.
4. Low-confidence/no-answer product knowledge returns handoff-required semantics.
5. `handoff_to_human` returns `tool_status=handoff_required`.
6. Adapter exceptions return safe `system_error` tool responses without leaking exception text.
7. API request-level errors return structured details and never include raw arguments or secrets.
8. Tool-call event logs persist the response `tool_status`, not always `completed`.
9. Focused tests and full test suite pass.

