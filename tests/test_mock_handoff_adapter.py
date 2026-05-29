from voiceagents.adapters.handoff import MockHandoffAdapter
from voiceagents.contracts.common import HandoffMode, HandoffReason
from voiceagents.contracts.handoff import HandoffRequest


def test_valid_handoff_returns_live_transfer() -> None:
    adapter = MockHandoffAdapter()

    response = adapter.handoff(
        HandoffRequest(
            call_id="CALL-REDACTED",
            merchant_id="merchant_demo",
            intent_primary="logistics_tracking",
            order_id_candidate="ORDER-REDACTED",
            summary="Customer wants tracking information.",
            tools_called=["lookup_logistics"],
            handoff_reason=HandoffReason.ORDER_ID_UNCONFIRMED,
            recommended_next_step="Ask customer to repeat the order number.",
        )
    )

    assert response.ok is True
    assert response.handoff_id == "HANDOFF-REDACTED"
    assert response.mode == HandoffMode.LIVE_TRANSFER

