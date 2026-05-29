from __future__ import annotations

from dataclasses import dataclass
from typing import Any


INTENTS = {
    "order_status",
    "logistics_tracking",
    "product_usage",
    "pre_sales_consultation",
    "return_exchange_refund",
    "complaint",
    "payment_discount_site_usage",
    "other",
}

TOOLS = {
    "none",
    "lookup_order",
    "lookup_logistics",
    "query_product_knowledge",
    "handoff_to_human",
    "multiple",
}

HANDOFF_REASONS = {
    "none",
    "low_asr_confidence",
    "order_id_unconfirmed",
    "tool_error",
    "rag_low_confidence",
    "refund_or_return_exception",
    "complaint_or_angry_customer",
    "unsupported_intent",
    "customer_requests_human",
    "policy_sensitive",
}

REQUIRED_STRING_FIELDS = (
    "call_id",
    "audio_file_ref",
    "language",
    "market",
    "customer_segment",
    "intent_primary",
    "intent_secondary",
    "tool_required",
    "handoff_reason",
    "human_agent_resolution",
    "expected_voice_response_summary",
    "privacy_notes",
)


@dataclass(frozen=True)
class ValidationIssue:
    call_id: str
    field: str
    message: str


def _has_value(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _call_id(row: dict[str, Any]) -> str:
    value = row.get("call_id")
    return value if _has_value(value) else "<missing call_id>"


def validate_call(row: dict[str, Any]) -> list[ValidationIssue]:
    call_id = _call_id(row)
    issues: list[ValidationIssue] = []

    for field in REQUIRED_STRING_FIELDS:
        if not _has_value(row.get(field)):
            issues.append(ValidationIssue(call_id, field, "required string is missing"))

    for field in ("requires_order_id", "order_id_spoken", "rag_answer_required", "should_handoff"):
        if not isinstance(row.get(field), bool):
            issues.append(ValidationIssue(call_id, field, "must be boolean"))

    confidence = row.get("order_id_confidence")
    if not isinstance(confidence, int | float) or confidence < 0 or confidence > 1:
        issues.append(ValidationIssue(call_id, "order_id_confidence", "must be a number from 0 to 1"))

    if row.get("intent_primary") not in INTENTS:
        issues.append(ValidationIssue(call_id, "intent_primary", f"must be one of: {', '.join(sorted(INTENTS))}"))

    if row.get("intent_secondary") not in INTENTS:
        issues.append(ValidationIssue(call_id, "intent_secondary", f"must be one of: {', '.join(sorted(INTENTS))}"))

    if row.get("tool_required") not in TOOLS:
        issues.append(ValidationIssue(call_id, "tool_required", f"must be one of: {', '.join(sorted(TOOLS))}"))

    if row.get("handoff_reason") not in HANDOFF_REASONS:
        issues.append(
            ValidationIssue(call_id, "handoff_reason", f"must be one of: {', '.join(sorted(HANDOFF_REASONS))}")
        )

    if row.get("should_handoff") is True and row.get("handoff_reason") == "none":
        issues.append(ValidationIssue(call_id, "handoff_reason", "handoff calls need a specific reason"))

    if row.get("should_handoff") is False and row.get("handoff_reason") != "none":
        issues.append(ValidationIssue(call_id, "handoff_reason", "non-handoff calls should use none"))

    if row.get("requires_order_id") is True and row.get("order_id_spoken") is False:
        issues.append(
            ValidationIssue(
                call_id,
                "order_id_spoken",
                "order-required calls must track whether the user spoke an order ID",
            )
        )

    if row.get("requires_order_id") is True and not _has_value(row.get("order_id_transcript")):
        issues.append(
            ValidationIssue(
                call_id,
                "order_id_transcript",
                "order-required calls need a redacted transcript or none/unknown marker",
            )
        )

    return issues


def validate_dataset(dataset: Any) -> list[ValidationIssue]:
    if isinstance(dataset, list):
        rows = dataset
    elif isinstance(dataset, dict):
        rows = dataset.get("calls")
    else:
        rows = None

    if not isinstance(rows, list):
        return [ValidationIssue("<dataset>", "calls", "dataset must be an array or an object with a calls array")]

    issues: list[ValidationIssue] = []
    for row in rows:
        if not isinstance(row, dict):
            issues.append(ValidationIssue("<dataset>", "calls", "each call must be an object"))
            continue
        issues.extend(validate_call(row))
    return issues

