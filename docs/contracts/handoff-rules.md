# Handoff and Failure Rules

VoiceAgents MVP should bias toward safe handoff when the system is uncertain. A bad handoff is cheaper than a confident wrong answer in phone support.

## Mandatory Handoff Triggers

- ASR confidence is too low to understand the user's main request.
- Order number cannot be confirmed after repeat-back.
- A tool call fails with `permission_denied` or repeated `system_error`.
- RAG returns `low_confidence` or `no_answer`.
- The user asks for a human.
- The user is angry, complains, or threatens chargeback/legal escalation.
- The user asks for return/refund handling outside explicitly approved merchant policy.
- The request is outside supported MVP intents.

## Handoff Context

Every handoff should include:

- Call ID.
- Primary and secondary intents.
- Order ID candidate, if any.
- Confirmation status.
- Tools called and safe result summaries.
- RAG answer candidate, if any.
- Handoff reason.
- Suggested next step for the human agent.

## Failure Classification

The remaining 10% outside auto-resolution and normal handoff must be classified:

- `caller_hung_up`
- `invalid_or_spam_call`
- `asr_failure`
- `tool_failure`
- `handoff_failure`
- `unsupported_intent`
- `system_error`

