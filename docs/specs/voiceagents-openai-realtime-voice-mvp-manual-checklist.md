# OpenAI Realtime Voice MVP Manual Checklist

Use this checklist for Task 5.6 and Task 5.7 when a valid server-side `OPENAI_API_KEY` and a browser with microphone access are available.

## Real-Mode Setup

Run from an isolated `.venv` or conda environment:

```bash
VOICEAGENTS_REALTIME_PROVIDER=openai_realtime \
OPENAI_API_KEY=... \
VOICEAGENTS_OPENAI_REALTIME_MODEL=gpt-realtime-2 \
VOICEAGENTS_OPENAI_REALTIME_VOICE=marin \
VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true \
VOICEAGENTS_TRANSCRIPT_LOGGING=structured \
./.venv/bin/python -m uvicorn voiceagents.api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/realtime-test
```

## Three-Minute Voice Verification

- Grant microphone permission.
- Start a realtime session and confirm remote audio can play.
- Complete a 3 minute conversation without page reload.
- Trigger the in-scope real-mode tools for the run.
- Full unwaived acceptance requires all four tools: `lookup_order`, `lookup_logistics`, `query_product_knowledge`, and `handoff_to_human`.
- Confirm tool results show only safe summaries in the Tool Calls panel.
- Confirm handoff updates the Handoff panel.

## Log Safety Verification

Inspect `.voiceagents/events/realtime-events.jsonl` and, when `VOICEAGENTS_TRANSCRIPT_LOGGING=transcript`, `.voiceagents/transcripts/realtime-transcripts.jsonl`.

- Events include redacted session, transcript, tool requested, and tool result records.
- Transcript text is persisted only as redacted text.
- Tool events include safe summary, provider call id, status, latency when present, and no raw arguments.
- File content does not include `client_secret`, `tool_call_token`, Authorization headers, SDP, raw audio, `raw_audio`, `audio_bytes`, or unredacted transcript text.

## Browser Failure-Mode Verification

- Microphone permission denial shows an error and does not call the OpenAI SDP endpoint.
- Client-secret failure creates no peer connection, local stream, remote audio, or retained client secret.
- SDP exchange failure closes peer connection, data channel, local tracks, remote audio, and clears secret-bearing state.
- Data channel close/error updates Session State.
- Stop closes data channel, peer connection, remote audio, and local tracks.
- Mute toggles local audio track `enabled` without ending the session.
- After Stop or failure, Start reconnects from a clean state.

## PR Notes Template

```text
Manual OpenAI realtime verification: PASS/FAIL
Date:
Browser:
Duration:
Tools triggered:
Log safety checked:
Failure-mode checks:
Notes:
```

## Recorded Verification - 2026-06-01

```text
Manual OpenAI realtime verification: PARTIAL PASS
Date: 2026-06-01
Browser: User local Chrome
URL: http://127.0.0.1:8000/realtime-test
Provider/model: openai_realtime / gpt-realtime-2
Input: real browser microphone, user-read Chinese prompts
Duration: user-confirmed longer than 3 minutes
Mode behavior: Text mode returned text only; Voice mode returned audio; runtime Text/Voice switching worked
Mute behavior: Mute/Unmute toggled local audio without ending the session and emitted mute_state events
Tools triggered:
- query_product_knowledge: PASS, LunaCare wig washing knowledge returned
- handoff_to_human: PASS, low-confidence knowledge/order-id-unconfirmed flows transferred to human support
- lookup_order: WAIVED for post-fixture real-mode retest by user; covered by mock/API/pytest with ORD-20260601-1842
- lookup_logistics: WAIVED for post-fixture real-mode retest by user; covered by mock/API/pytest with ORD-20260601-1842
Log safety checked: PASS for the current structured JSONL sample; no client_secret, tool_call_token, Authorization, SDP, raw audio, or unredacted transcript observed
Failure-mode checks:
- Stop cleanup: PASS by manual flow
- Mute: PASS by manual flow
- Microphone permission denial: TODO or defer
- Client-secret failure: TODO or defer
- SDP exchange failure: TODO or defer
- Data channel close/error: TODO or defer
- Reconnect after failure: TODO or defer
Notes: This record intentionally distinguishes PASS, WAIVED, and TODO items so merge review can decide whether the remaining browser failure-mode checks block landing.
```

Latency note: the `/realtime-test` Latency panel currently displays the latest client-secret/start or tool/event relay timing. It is not an end-to-end voice response latency metric.
