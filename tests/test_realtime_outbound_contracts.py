import pytest
from pydantic import ValidationError

from voiceagents.realtime.outbound import (
    RealtimeBrowserProxyMessage,
    RealtimeBrowserProxyMessageType,
    RealtimeOutboundEvent,
    RealtimeOutboundEventKind,
    RealtimeSafeProviderError,
)


def test_outbound_event_shapes_separate_json_audio_close_and_error() -> None:
    json_event = RealtimeOutboundEvent(
        kind=RealtimeOutboundEventKind.JSON,
        payload={"type": "session.created"},
    )
    audio_event = RealtimeOutboundEvent(
        kind=RealtimeOutboundEventKind.AUDIO,
        audio=b"pcm16-bytes",
    )
    close_event = RealtimeOutboundEvent(
        kind=RealtimeOutboundEventKind.CLOSE,
        close_code=1000,
        safe_summary="provider closed normally",
    )
    error_event = RealtimeOutboundEvent(
        kind=RealtimeOutboundEventKind.ERROR,
        safe_error=RealtimeSafeProviderError(
            code="provider_error",
            safe_summary="provider connection failed",
            provider_event_type="error",
        ),
    )

    assert json_event.payload == {"type": "session.created"}
    assert audio_event.audio == b"pcm16-bytes"
    assert close_event.close_code == 1000
    assert error_event.safe_error is not None
    assert "pcm16-bytes" not in json_event.model_dump_json()


def test_outbound_event_rejects_mismatched_payload_shapes() -> None:
    with pytest.raises(ValidationError, match="payload is required"):
        RealtimeOutboundEvent(kind=RealtimeOutboundEventKind.JSON)

    with pytest.raises(ValidationError, match="audio is required"):
        RealtimeOutboundEvent(kind=RealtimeOutboundEventKind.AUDIO, payload={"type": "audio"})

    with pytest.raises(ValidationError, match="safe_error is required"):
        RealtimeOutboundEvent(kind=RealtimeOutboundEventKind.ERROR, payload={"type": "error"})


def test_browser_proxy_message_accepts_safe_envelopes() -> None:
    message = RealtimeBrowserProxyMessage(
        type=RealtimeBrowserProxyMessageType.CONTROL,
        payload={"action": "start"},
    )

    assert message.type is RealtimeBrowserProxyMessageType.CONTROL
    assert message.payload == {"action": "start"}


def test_browser_proxy_message_rejects_extra_fields_and_blocked_keys() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RealtimeBrowserProxyMessage(
            type=RealtimeBrowserProxyMessageType.CONTROL,
            payload={"action": "start"},
            authorization="Bearer provider-secret",
        )

    with pytest.raises(ValidationError, match="authorization"):
        RealtimeBrowserProxyMessage(
            type=RealtimeBrowserProxyMessageType.AUDIO,
            payload={"frame": {"authorization": "Bearer provider-secret"}},
        )

    with pytest.raises(ValidationError, match="raw_audio"):
        RealtimeBrowserProxyMessage(
            type=RealtimeBrowserProxyMessageType.AUDIO,
            payload={"raw_audio": "base64-provider-audio"},
        )


def test_safe_provider_error_does_not_expose_secrets_or_raw_payloads() -> None:
    error = RealtimeSafeProviderError(
        code="auth_failed",
        safe_summary="DashScope rejected the outbound connection",
        provider_event_type="error",
    )

    assert error.code == "auth_failed"
    assert "Authorization" not in error.model_dump_json()

    with pytest.raises(ValidationError, match="safe_summary"):
        RealtimeSafeProviderError(
            code="auth_failed",
            safe_summary="Authorization: Bearer provider-secret",
            provider_event_type="error",
        )

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RealtimeSafeProviderError(
            code="auth_failed",
            safe_summary="DashScope rejected the outbound connection",
            provider_event_type="error",
            raw_payload={"api_key": "provider-secret"},
        )
