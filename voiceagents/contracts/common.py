from enum import StrEnum


class ToolErrorCode(StrEnum):
    NOT_FOUND = "not_found"
    INVALID_INPUT = "invalid_input"
    PERMISSION_DENIED = "permission_denied"
    SYSTEM_ERROR = "system_error"
    NO_ANSWER = "no_answer"
    LOW_CONFIDENCE = "low_confidence"


class HandoffMode(StrEnum):
    LIVE_TRANSFER = "live_transfer"
    CALLBACK = "callback"
    TICKET = "ticket"


class HandoffReason(StrEnum):
    NONE = "none"
    LOW_ASR_CONFIDENCE = "low_asr_confidence"
    ORDER_ID_UNCONFIRMED = "order_id_unconfirmed"
    TOOL_ERROR = "tool_error"
    RAG_LOW_CONFIDENCE = "rag_low_confidence"
    REFUND_OR_RETURN_EXCEPTION = "refund_or_return_exception"
    COMPLAINT_OR_ANGRY_CUSTOMER = "complaint_or_angry_customer"
    UNSUPPORTED_INTENT = "unsupported_intent"
    CUSTOMER_REQUESTS_HUMAN = "customer_requests_human"
    POLICY_SENSITIVE = "policy_sensitive"

