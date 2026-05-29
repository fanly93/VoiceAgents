from voiceagents.realtime.redaction import (
    BasicTextRedactor,
    RedactionResult,
    Redactor,
    redact_mapping,
    redact_text,
)


def test_redact_text_replaces_email_like_strings() -> None:
    result = redact_text("Please contact customer@example.com for details.")

    assert result == RedactionResult(
        value="Please contact [EMAIL_REDACTED] for details.",
        redaction_applied=True,
    )


def test_redact_text_replaces_phone_like_strings() -> None:
    result = redact_text("Call me at +1 (555) 123-4567 tomorrow.")

    assert result.value == "Call me at [PHONE_REDACTED] tomorrow."
    assert result.redaction_applied is True


def test_redact_text_replaces_order_like_ids() -> None:
    result = redact_text("I need help with order ORD-2026-ABC123.")

    assert result.value == "I need help with order [ORDER_REDACTED]."
    assert result.redaction_applied is True


def test_redact_text_replaces_redacted_order_like_ids_consistently() -> None:
    result = redact_text("Order ORDER-REDACTED-001 has been paid.")

    assert result.value == "Order [ORDER_REDACTED] has been paid."
    assert result.redaction_applied is True


def test_redact_text_does_not_treat_iso_timestamp_as_phone() -> None:
    timestamp = "2026-05-29T12:28:31.165404+00:00"

    result = redact_text(timestamp)

    assert result.value == timestamp
    assert result.redaction_applied is False


def test_redact_mapping_recursively_redacts_dicts_lists_and_strings() -> None:
    payload = {
        "email": "customer@example.com",
        "orders": ["ORDER-123456", {"note": "Phone: 555-123-4567"}],
        "count": 2,
    }

    result = redact_mapping(payload)

    assert result.value == {
        "email": "[EMAIL_REDACTED]",
        "orders": ["[ORDER_REDACTED]", {"note": "Phone: [PHONE_REDACTED]"}],
        "count": 2,
    }
    assert result.redaction_applied is True
    assert payload["email"] == "customer@example.com"


def test_redaction_applied_is_false_without_sensitive_information() -> None:
    result = redact_mapping({"message": "Order status is ready.", "items": ["safe"]})

    assert result.value == {"message": "Order status is ready.", "items": ["safe"]}
    assert result.redaction_applied is False


def test_basic_text_redactor_satisfies_redactor_protocol() -> None:
    redactor: Redactor = BasicTextRedactor()

    assert redactor.redact_text("safe text").redaction_applied is False
