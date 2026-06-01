from voiceagents.call_evaluation import validate_dataset


def valid_call() -> dict:
    return {
        "call_id": "test-001",
        "audio_file_ref": "secure-audio-store://redacted/test-001",
        "language": "en",
        "market": "Europe",
        "customer_segment": "older_wig_customer",
        "intent_primary": "logistics_tracking",
        "intent_secondary": "order_status",
        "requires_order_id": True,
        "order_id_spoken": True,
        "order_id_transcript": "ORD-20260601-1842",
        "order_id_confidence": 0.9,
        "tool_required": "multiple",
        "rag_answer_required": False,
        "should_handoff": False,
        "handoff_reason": "none",
        "human_agent_resolution": "Agent provided logistics status.",
        "expected_voice_response_summary": "Confirm order and provide tracking status.",
        "privacy_notes": "No real customer data.",
    }


def test_accepts_valid_dataset() -> None:
    assert validate_dataset({"calls": [valid_call()]}) == []


def test_requires_specific_reason_for_handoff_calls() -> None:
    call = valid_call() | {"should_handoff": True, "handoff_reason": "none"}

    issues = validate_dataset({"calls": [call]})

    assert any(issue.field == "handoff_reason" for issue in issues)


def test_rejects_confidence_outside_zero_to_one() -> None:
    call = valid_call() | {"order_id_confidence": 1.7}

    issues = validate_dataset({"calls": [call]})

    assert any(issue.field == "order_id_confidence" for issue in issues)


def test_rejects_unknown_intents() -> None:
    call = valid_call() | {"intent_primary": "unknown_intent"}

    issues = validate_dataset({"calls": [call]})

    assert any(issue.field == "intent_primary" for issue in issues)
