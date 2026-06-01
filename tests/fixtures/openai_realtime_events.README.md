# OpenAI Realtime Event Fixtures

Source: https://developers.openai.com/api/reference/resources/realtime

retrieved 2026-05-31 from the official OpenAI Realtime API reference. These fixtures intentionally contain provider-specific event names and are used only to test browser/provider adapter normalization.

Relevant official event families captured here:

- `response.output_audio_transcript.delta` and `response.output_audio_transcript.done`
- `conversation.item.input_audio_transcription.segment`
- `conversation.item.done`
- `response.function_call_arguments.done`
- `conversation.item.create` with `function_call_output`
- `response.create`
- `response.done`
- `error`
