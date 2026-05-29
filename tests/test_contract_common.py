from voiceagents.contracts.common import HandoffMode, HandoffReason, ToolErrorCode


def test_tool_error_codes_match_contract_docs() -> None:
    assert ToolErrorCode.NOT_FOUND == "not_found"
    assert ToolErrorCode.INVALID_INPUT == "invalid_input"
    assert ToolErrorCode.PERMISSION_DENIED == "permission_denied"
    assert ToolErrorCode.SYSTEM_ERROR == "system_error"
    assert ToolErrorCode.NO_ANSWER == "no_answer"
    assert ToolErrorCode.LOW_CONFIDENCE == "low_confidence"


def test_handoff_modes_match_contract_docs() -> None:
    assert HandoffMode.LIVE_TRANSFER == "live_transfer"
    assert HandoffMode.CALLBACK == "callback"
    assert HandoffMode.TICKET == "ticket"


def test_handoff_reasons_match_handoff_rules() -> None:
    assert HandoffReason.NONE == "none"
    assert HandoffReason.LOW_ASR_CONFIDENCE == "low_asr_confidence"
    assert HandoffReason.ORDER_ID_UNCONFIRMED == "order_id_unconfirmed"
    assert HandoffReason.TOOL_ERROR == "tool_error"
    assert HandoffReason.RAG_LOW_CONFIDENCE == "rag_low_confidence"
    assert HandoffReason.REFUND_OR_RETURN_EXCEPTION == "refund_or_return_exception"
    assert HandoffReason.COMPLAINT_OR_ANGRY_CUSTOMER == "complaint_or_angry_customer"
    assert HandoffReason.UNSUPPORTED_INTENT == "unsupported_intent"
    assert HandoffReason.CUSTOMER_REQUESTS_HUMAN == "customer_requests_human"
    assert HandoffReason.POLICY_SENSITIVE == "policy_sensitive"

