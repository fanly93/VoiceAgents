import pytest

from voiceagents.adapters.logistics import MockLogisticsAdapter
from voiceagents.adapters.handoff import MockHandoffAdapter
from voiceagents.adapters.knowledge import MockKnowledgeAdapter
from voiceagents.adapters.order import MockOrderAdapter
from voiceagents.contracts.common import HandoffReason
from voiceagents.realtime.contracts import RealtimeProviderName, RealtimeToolCallRequest
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore
from voiceagents.realtime.tool_router import (
    InvalidToolCallTokenError,
    InvalidToolArgumentsError,
    LookupOrderArguments,
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
        arguments={"order_id": "ORD-20260601-1842"},
    )


def make_router_with_adapters(store: InMemoryVoiceSessionStore) -> RealtimeToolRouter:
    return RealtimeToolRouter(
        session_store=store,
        order_adapter=MockOrderAdapter(),
        logistics_adapter=MockLogisticsAdapter(),
        knowledge_adapter=MockKnowledgeAdapter(),
        handoff_adapter=MockHandoffAdapter(),
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


def test_tool_router_rejects_session_binding_mismatch() -> None:
    store, token = make_store_with_session()
    router = RealtimeToolRouter(session_store=store)

    with pytest.raises(InvalidToolCallTokenError):
        router.validate_request(
            make_tool_call_request().model_copy(update={"call_id": "call-other"}),
            token,
            provider=RealtimeProviderName.MOCK,
        )
    with pytest.raises(InvalidToolCallTokenError):
        router.validate_request(
            make_tool_call_request().model_copy(update={"merchant_id": "merchant-other"}),
            token,
            provider=RealtimeProviderName.MOCK,
        )
    with pytest.raises(InvalidToolCallTokenError):
        router.validate_request(
            make_tool_call_request(),
            token,
            provider=RealtimeProviderName.OPENAI_REALTIME,
        )


def test_tool_router_validates_tool_arguments() -> None:
    store, _token = make_store_with_session()
    router = RealtimeToolRouter(session_store=store)

    arguments = router.validate_arguments(make_tool_call_request())

    assert isinstance(arguments, LookupOrderArguments)
    assert arguments.order_id == "ORD-20260601-1842"


def test_tool_router_rejects_invalid_tool_arguments() -> None:
    store, _token = make_store_with_session()
    router = RealtimeToolRouter(session_store=store)

    with pytest.raises(InvalidToolArgumentsError):
        router.validate_arguments(
            RealtimeToolCallRequest(
                session_id="session-123",
                call_id="call-123",
                merchant_id="merchant-123",
                tool_name="lookup_order",
                arguments={"order_id": ""},
            )
        )


def test_tool_router_rejects_extra_tool_arguments() -> None:
    store, _token = make_store_with_session()
    router = RealtimeToolRouter(session_store=store)

    with pytest.raises(InvalidToolArgumentsError):
        router.validate_arguments(
            RealtimeToolCallRequest(
                session_id="session-123",
                call_id="call-123",
                merchant_id="merchant-123",
                tool_name="lookup_order",
                arguments={"order_id": "ORD-20260601-1842", "python_module": "os"},
            )
        )


def test_tool_router_routes_order_lookup() -> None:
    store, token = make_store_with_session()
    router = make_router_with_adapters(store)

    response = router.execute(make_tool_call_request(), tool_call_token=token)

    assert response.ok is True
    assert response.tool_name == "lookup_order"
    assert response.result == {"order_status": "paid"}
    assert response.safe_summary == "Order ORD-20260601-1842 has been paid."
    assert response.handoff_required is False
    assert response.handoff_reason is HandoffReason.NONE


def test_tool_router_routes_logistics_lookup() -> None:
    store, token = make_store_with_session()
    router = make_router_with_adapters(store)

    response = router.execute(
        RealtimeToolCallRequest(
            session_id="session-123",
            call_id="call-123",
            merchant_id="merchant-123",
            tool_name="lookup_logistics",
            arguments={"order_id": "ORD-20260601-1842"},
        ),
        tool_call_token=token,
    )

    assert response.ok is True
    assert response.tool_name == "lookup_logistics"
    assert response.result["status"] == "in_transit"
    assert response.handoff_required is False
    assert response.handoff_reason is HandoffReason.NONE


def test_tool_router_routes_product_knowledge() -> None:
    store, token = make_store_with_session()
    router = make_router_with_adapters(store)

    response = router.execute(
        RealtimeToolCallRequest(
            session_id="session-123",
            call_id="call-123",
            merchant_id="merchant-123",
            tool_name="query_product_knowledge",
            arguments={"query": "LunaCare 假发护理套装应该怎么清洗假发？", "locale": "zh-CN"},
        ),
        tool_call_token=token,
    )

    assert response.ok is True
    assert response.tool_name == "query_product_knowledge"
    assert "cool water" in response.safe_summary
    assert response.handoff_required is False
    assert response.handoff_reason is HandoffReason.NONE


def test_tool_router_routes_handoff_to_human_and_marks_session() -> None:
    store, token = make_store_with_session()
    router = make_router_with_adapters(store)

    response = router.execute(
        RealtimeToolCallRequest(
            session_id="session-123",
            call_id="call-123",
            merchant_id="merchant-123",
            tool_name="handoff_to_human",
            arguments={
                "reason": "customer_requests_human",
                "summary": "Customer asked to speak with a person.",
            },
        ),
        tool_call_token=token,
    )

    assert response.ok is True
    assert response.handoff_required is True
    assert response.handoff_reason is HandoffReason.CUSTOMER_REQUESTS_HUMAN
    assert response.result["handoff_id"] == "HANDOFF-REDACTED"
    assert store.get_session("session-123").handoff_reason is HandoffReason.CUSTOMER_REQUESTS_HUMAN
