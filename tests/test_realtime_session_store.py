from datetime import datetime, timedelta, timezone

import pytest

from voiceagents.contracts.common import HandoffReason
from voiceagents.realtime.contracts import RealtimeProviderName, VoiceSessionState
from voiceagents.realtime.session_store import (
    DEFAULT_TOOL_CALL_TOKEN_TTL_SECONDS,
    InMemoryVoiceSessionStore,
    VoiceSessionNotFound,
)


def test_create_session_returns_plaintext_token_once_and_stores_hash() -> None:
    store = InMemoryVoiceSessionStore()
    now = datetime(2026, 5, 29, 9, 0, tzinfo=timezone.utc)

    created = store.create_session(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        now=now,
    )

    assert len(created.tool_call_token) >= 32
    assert created.session.token_hash != created.tool_call_token
    assert created.session.provider is RealtimeProviderName.MOCK
    assert created.session.token_expires_at == now + timedelta(
        seconds=DEFAULT_TOOL_CALL_TOKEN_TTL_SECONDS
    )
    assert store.verify_tool_call_token(
        "session-123",
        created.tool_call_token,
        now=now,
    )


def test_verify_tool_call_token_rejects_wrong_expired_or_ended_token() -> None:
    store = InMemoryVoiceSessionStore()
    now = datetime(2026, 5, 29, 9, 0, tzinfo=timezone.utc)
    created = store.create_session(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        now=now,
    )

    assert not store.verify_tool_call_token("session-123", "wrong-token", now=now)
    assert not store.verify_tool_call_token(
        "session-123",
        created.tool_call_token,
        now=now + timedelta(seconds=DEFAULT_TOOL_CALL_TOKEN_TTL_SECONDS),
    )

    store.end_session("session-123", ended_at=now + timedelta(seconds=1))

    assert not store.verify_tool_call_token(
        "session-123",
        created.tool_call_token,
        now=now + timedelta(seconds=2),
    )


def test_verify_session_token_binding_checks_call_merchant_and_provider() -> None:
    store = InMemoryVoiceSessionStore()
    created = store.create_session(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        provider=RealtimeProviderName.MOCK,
    )

    assert store.verify_session_token_binding(
        "session-123",
        created.tool_call_token,
        call_id="call-123",
        merchant_id="merchant-123",
        provider=RealtimeProviderName.MOCK,
    )
    assert not store.verify_session_token_binding(
        "session-123",
        created.tool_call_token,
        call_id="call-other",
        merchant_id="merchant-123",
        provider=RealtimeProviderName.MOCK,
    )
    assert not store.verify_session_token_binding(
        "session-123",
        created.tool_call_token,
        call_id="call-123",
        merchant_id="merchant-other",
        provider=RealtimeProviderName.MOCK,
    )
    assert not store.verify_session_token_binding(
        "session-123",
        created.tool_call_token,
        call_id="call-123",
        merchant_id="merchant-123",
        provider=RealtimeProviderName.OPENAI_REALTIME,
    )


def test_update_session_state_and_append_runtime_data() -> None:
    store = InMemoryVoiceSessionStore()
    store.create_session(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
    )

    store.update_state("session-123", VoiceSessionState.LISTENING)
    store.append_transcript("session-123", "user", "Where is my order?")
    store.append_tool_call("session-123", "lookup_order", "Order is paid.")

    session = store.get_session("session-123")
    assert session.state is VoiceSessionState.LISTENING
    assert session.transcripts[0].role == "user"
    assert session.tool_calls[0].tool_name == "lookup_order"


def test_mark_handoff_sets_handoff_state() -> None:
    store = InMemoryVoiceSessionStore()
    store.create_session(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
    )

    session = store.mark_handoff(
        "session-123",
        HandoffReason.CUSTOMER_REQUESTS_HUMAN,
        "HND-20260601-0007",
    )

    assert session.state is VoiceSessionState.HANDOFF_PENDING
    assert session.handoff_reason is HandoffReason.CUSTOMER_REQUESTS_HUMAN
    assert session.handoff_id == "HND-20260601-0007"


def test_missing_session_raises_typed_error() -> None:
    store = InMemoryVoiceSessionStore()

    with pytest.raises(VoiceSessionNotFound):
        store.get_session("missing-session")
