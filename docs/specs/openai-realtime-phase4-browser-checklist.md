# OpenAI Realtime Phase 4 Browser Checklist

This checklist records the fake-media/browser paths that must be exercised before moving to Phase 5 manual real-mode verification.

- microphone permission denial: Start should show an error, release any partial resources, and must not call the OpenAI SDP endpoint.
- client-secret failure: Start should leave no peer connection, no local tracks, no remote audio element, and no retained client secret.
- SDP exchange failure: Start should close the peer connection, stop local tracks, remove remote audio, and allow another Start attempt.
- data channel close/error: visible Session State should update to `data_channel_closed` or `data_channel_error`.
- Stop cleanup: Stop should close the data channel, close the peer connection, stop every local track, remove remote audio, and clear secret-bearing state.
- Mute: Mute should toggle local audio track `enabled` without ending the session or closing the peer connection.
- reconnect from a clean state: after Stop or failure, another Start should allocate fresh session IDs and fresh WebRTC resources.
