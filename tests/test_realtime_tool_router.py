import pytest

from voiceagents.realtime.contracts import RealtimeToolCallRequest
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore
from voiceagents.realtime.tool_router import (
    InvalidToolCallTokenError,
    RealtimeToolRouter,
    UnknownRealtimeToolError,
)


def make_store_with_session() -> tuple[InMemoryVoiceSessionStore, str]:
    store = InMemoryVoiceSessionStore()
    created = store.create_session(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
    )
    return store, created.tool_call_token


def make_tool_call_request(tool_name: str = "lookup_order") -> RealtimeToolCallRequest:
    return RealtimeToolCallRequest(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        tool_name=tool_name,
        arguments={"order_id": "ORDER-REDACTED-001"},
    )


def test_tool_router_accepts_allowed_tool_with_valid_token() -> None:
    store, token = make_store_with_session()
    router = RealtimeToolRouter(session_store=store)

    router.validate_request(make_tool_call_request(), token)


def test_tool_router_rejects_unknown_tool() -> None:
    store, token = make_store_with_session()
    router = RealtimeToolRouter(session_store=store)

    with pytest.raises(UnknownRealtimeToolError):
        router.validate_request(make_tool_call_request("run_shell"), token)


def test_tool_router_rejects_invalid_token() -> None:
    store, _token = make_store_with_session()
    router = RealtimeToolRouter(session_store=store)

    with pytest.raises(InvalidToolCallTokenError):
        router.validate_request(make_tool_call_request(), "wrong-token")
