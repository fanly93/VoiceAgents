from voiceagents.realtime.contracts import (
    ALLOWED_REALTIME_TOOL_NAMES,
    DEFAULT_REALTIME_INSTRUCTIONS,
    DEFAULT_TRANSCRIPT_LOGGING_MODE,
    NormalizedRealtimeEventType,
    RealtimeClientSecretRequest,
    RealtimeClientSecretResponse,
    RealtimeEventIngestRequest,
    RealtimeEventIngestResponse,
    RealtimeProviderName,
    RealtimeSessionConfig,
    RealtimeTranscriptEvent,
    RealtimeTranscriptEventType,
    RealtimeToolCallRequest,
    RealtimeToolCallResponse,
    RealtimeToolDefinition,
    ResponseMode,
    TranscriptLoggingMode,
    VoiceEvent,
    VoiceSessionState,
    build_default_realtime_session_config,
)
from voiceagents.contracts.common import HandoffReason, ToolErrorCode


def test_voice_session_states_match_spec() -> None:
    assert VoiceSessionState.IDLE == "idle"
    assert VoiceSessionState.LISTENING == "listening"
    assert VoiceSessionState.TRANSCRIBING == "transcribing"
    assert VoiceSessionState.THINKING == "thinking"
    assert VoiceSessionState.TOOL_CALLING == "tool_calling"
    assert VoiceSessionState.SPEAKING == "speaking"
    assert VoiceSessionState.HANDOFF_PENDING == "handoff_pending"
    assert VoiceSessionState.ENDED == "ended"
    assert VoiceSessionState.ERROR == "error"


def test_response_modes_match_spec() -> None:
    assert ResponseMode.TEXT == "text"
    assert ResponseMode.VOICE == "voice"


def test_realtime_provider_names_match_spec() -> None:
    assert RealtimeProviderName.MOCK == "mock"
    assert RealtimeProviderName.OPENAI_REALTIME == "openai_realtime"


def test_normalized_realtime_event_types_match_spec() -> None:
    assert {event.value for event in NormalizedRealtimeEventType} == {
        "session.connecting",
        "session.connected",
        "session.ended",
        "session.error",
        "transcript.user.delta",
        "transcript.user.done",
        "transcript.assistant.delta",
        "transcript.assistant.done",
        "tool_call.requested",
        "tool_call.result",
        "handoff.requested",
        "response.done",
    }


def test_realtime_event_ingest_request_accepts_transcript_event() -> None:
    request = RealtimeEventIngestRequest(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        provider=RealtimeProviderName.OPENAI_REALTIME,
        event_type=NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DELTA,
        state=VoiceSessionState.TRANSCRIBING,
        provider_event_type="response.output_audio_transcript.delta",
        speaker="assistant",
        turn_id="turn-123",
        sequence=1,
        text="Where is ORDER-123456?",
        latency_ms=120,
    )

    assert request.text == "Where is ORDER-123456?"
    assert request.speaker == "assistant"


def test_realtime_event_ingest_request_accepts_safe_tool_event() -> None:
    request = RealtimeEventIngestRequest(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        provider=RealtimeProviderName.OPENAI_REALTIME,
        event_type=NormalizedRealtimeEventType.TOOL_CALL_REQUESTED,
        state=VoiceSessionState.TOOL_CALLING,
        provider_event_type="response.function_call_arguments.done",
        tool_name="lookup_order",
        provider_call_id="provider-call-123",
        tool_status="requested",
        safe_summary="Order lookup requested for [ORDER_REDACTED].",
        latency_ms=120,
    )

    assert request.tool_name == "lookup_order"
    assert request.safe_summary == "Order lookup requested for [ORDER_REDACTED]."


def test_realtime_event_ingest_request_rejects_extra_and_raw_argument_fields() -> None:
    for forbidden_field in ("unknown_field", "arguments", "tool_arguments"):
        try:
            RealtimeEventIngestRequest(
                session_id="session-123",
                call_id="call-123",
                merchant_id="merchant-123",
                provider=RealtimeProviderName.OPENAI_REALTIME,
                event_type=NormalizedRealtimeEventType.TOOL_CALL_REQUESTED,
                state=VoiceSessionState.TOOL_CALLING,
                tool_name="lookup_order",
                provider_call_id="provider-call-123",
                tool_status="requested",
                safe_summary="Order lookup requested.",
                **{forbidden_field: {"order_id": "ORDER-123456"}},
            )
        except ValueError as error:
            assert forbidden_field in str(error)
        else:
            raise AssertionError(f"{forbidden_field} should not be accepted")


def test_realtime_event_ingest_request_rejects_mixed_transcript_and_tool_fields() -> None:
    for transcript_field in (
        {"text": "raw tool args should not be here"},
        {"turn_id": "turn-123"},
        {"sequence": 1},
    ):
        try:
            RealtimeEventIngestRequest(
                session_id="session-123",
                call_id="call-123",
                merchant_id="merchant-123",
                provider=RealtimeProviderName.OPENAI_REALTIME,
                event_type=NormalizedRealtimeEventType.TOOL_CALL_REQUESTED,
                state=VoiceSessionState.TOOL_CALLING,
                tool_name="lookup_order",
                provider_call_id="provider-call-123",
                tool_status="requested",
                safe_summary="Order lookup requested.",
                **transcript_field,
            )
        except ValueError as error:
            assert next(iter(transcript_field)) in str(error)
        else:
            raise AssertionError(f"tool events must reject {transcript_field}")

    try:
        RealtimeEventIngestRequest(
            session_id="session-123",
            call_id="call-123",
            merchant_id="merchant-123",
            provider=RealtimeProviderName.OPENAI_REALTIME,
            event_type=NormalizedRealtimeEventType.TRANSCRIPT_USER_DELTA,
            state=VoiceSessionState.TRANSCRIBING,
            speaker="user",
            text="Where is my order?",
            tool_name="lookup_order",
        )
    except ValueError as error:
        assert "tool_name" in str(error)
    else:
        raise AssertionError("transcript events must reject tool fields")


def test_realtime_event_ingest_request_rejects_transcript_speaker_mismatch() -> None:
    for event_type, speaker in (
        (NormalizedRealtimeEventType.TRANSCRIPT_USER_DELTA, "assistant"),
        (NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DONE, "user"),
    ):
        try:
            RealtimeEventIngestRequest(
                session_id="session-123",
                call_id="call-123",
                merchant_id="merchant-123",
                provider=RealtimeProviderName.OPENAI_REALTIME,
                event_type=event_type,
                state=VoiceSessionState.TRANSCRIBING,
                speaker=speaker,
                text="Where is my order?",
            )
        except ValueError as error:
            assert "speaker" in str(error)
        else:
            raise AssertionError(f"{event_type} should reject speaker={speaker}")


def test_realtime_event_ingest_response_contains_event_id_and_redaction_flag() -> None:
    response = RealtimeEventIngestResponse(
        ok=True,
        event_id="event-123",
        redaction_applied=True,
    )

    assert response.ok is True
    assert response.event_id == "event-123"
    assert response.redaction_applied is True


def test_realtime_transcript_event_contains_redacted_transcript_shape() -> None:
    event = RealtimeTranscriptEvent(
        event_id="event-123",
        timestamp="2026-05-30T00:00:00Z",
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        speaker="user",
        event_type=RealtimeTranscriptEventType.TRANSCRIPT_DONE,
        turn_id="turn-123",
        sequence=1,
        text_redacted="Where is [ORDER_REDACTED]?",
        provider=RealtimeProviderName.OPENAI_REALTIME,
        provider_event_type="conversation.item.input_audio_transcription.completed",
        redaction_applied=True,
    )

    assert event.speaker == "user"
    assert event.event_type is RealtimeTranscriptEventType.TRANSCRIPT_DONE
    assert event.text_redacted == "Where is [ORDER_REDACTED]?"


def test_realtime_transcript_event_rejects_empty_text_and_unknown_speaker() -> None:
    for field_update in (
        {"text_redacted": ""},
        {"speaker": "system"},
    ):
        payload = {
            "event_id": "event-123",
            "timestamp": "2026-05-30T00:00:00Z",
            "session_id": "session-123",
            "call_id": "call-123",
            "merchant_id": "merchant-123",
            "speaker": "user",
            "event_type": RealtimeTranscriptEventType.TRANSCRIPT_DELTA,
            "turn_id": "turn-123",
            "sequence": 1,
            "text_redacted": "Where is [ORDER_REDACTED]?",
            "provider": RealtimeProviderName.OPENAI_REALTIME,
            "provider_event_type": "response.output_audio_transcript.delta",
            "redaction_applied": True,
        } | field_update
        try:
            RealtimeTranscriptEvent(**payload)
        except ValueError as error:
            assert next(iter(field_update)) in str(error)
        else:
            raise AssertionError(f"{field_update} should fail validation")


def test_transcript_logging_modes_match_spec_with_structured_default() -> None:
    assert TranscriptLoggingMode.OFF == "off"
    assert TranscriptLoggingMode.STRUCTURED == "structured"
    assert TranscriptLoggingMode.TRANSCRIPT == "transcript"
    assert DEFAULT_TRANSCRIPT_LOGGING_MODE is TranscriptLoggingMode.STRUCTURED


def test_client_secret_request_accepts_valid_values() -> None:
    request = RealtimeClientSecretRequest(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        response_mode=ResponseMode.TEXT,
        locale="en-US",
        safety_subject_id="subject_hash_123",
    )

    assert request.session_id == "session-123"
    assert request.response_mode is ResponseMode.TEXT


def test_client_secret_request_rejects_empty_ids() -> None:
    try:
        RealtimeClientSecretRequest(
            session_id="",
            call_id="call-123",
            merchant_id="merchant-123",
            response_mode=ResponseMode.TEXT,
            locale="en-US",
        )
    except ValueError as error:
        assert "session_id" in str(error)
    else:
        raise AssertionError("empty session_id should fail validation")


def test_client_secret_request_rejects_raw_safety_subject_id() -> None:
    for safety_subject_id in ("customer@example.com", "+1 555 123 4567", "Jane Customer"):
        try:
            RealtimeClientSecretRequest(
                session_id="session-123",
                call_id="call-123",
                merchant_id="merchant-123",
                response_mode=ResponseMode.TEXT,
                locale="en-US",
                safety_subject_id=safety_subject_id,
            )
        except ValueError as error:
            assert "safety_subject_id" in str(error)
        else:
            raise AssertionError(f"{safety_subject_id} should fail validation")


def test_client_secret_response_contains_session_config_and_relay_token() -> None:
    response = RealtimeClientSecretResponse(
        provider=RealtimeProviderName.MOCK,
        session_id="session-123",
        call_id="call-123",
        client_secret="mock-client-secret",
        tool_call_token="mock-tool-token",
        connection_url="https://example.invalid/realtime",
        expires_at="2026-05-29T09:00:00Z",
        model="mock-realtime",
        voice="alloy",
        session_config=RealtimeSessionConfig(
            instructions="Use approved support tools only.",
            tools=[
                RealtimeToolDefinition(
                    name="lookup_order",
                    description="Look up an order.",
                    parameters_schema={
                        "type": "object",
                        "properties": {"order_id": {"type": "string"}},
                        "required": ["order_id"],
                    },
                )
            ],
        ),
    )

    assert response.tool_call_token == "mock-tool-token"
    assert response.session_config.tools[0].name == "lookup_order"


def test_tool_call_request_contains_no_body_token() -> None:
    request = RealtimeToolCallRequest(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        tool_name="lookup_order",
        arguments={"order_id": "ORD-20260601-1842"},
    )

    assert request.tool_name == "lookup_order"
    assert "tool_call_token" not in request.model_fields_set


def test_tool_call_request_rejects_body_token() -> None:
    try:
        RealtimeToolCallRequest(
            session_id="session-123",
            call_id="call-123",
            merchant_id="merchant-123",
            tool_name="lookup_order",
            arguments={"order_id": "ORD-20260601-1842"},
            tool_call_token="must-not-be-in-body",
        )
    except ValueError as error:
        assert "tool_call_token" in str(error)
    else:
        raise AssertionError("tool_call_token must not be accepted in request body")


def test_tool_call_response_contains_safe_output_shape() -> None:
    response = RealtimeToolCallResponse(
        ok=False,
        tool_name="lookup_order",
        result={},
        safe_summary="Order was not found.",
        handoff_required=True,
        handoff_reason=HandoffReason.TOOL_ERROR,
        error_code=ToolErrorCode.NOT_FOUND,
    )

    assert response.handoff_required is True
    assert response.error_code is ToolErrorCode.NOT_FOUND


def test_default_session_config_contains_only_allowed_tools() -> None:
    config = build_default_realtime_session_config()
    tool_names = {tool.name for tool in config.tools}

    assert tool_names == ALLOWED_REALTIME_TOOL_NAMES
    assert config.model_dump()["tools"][0]["parameters_schema"]["type"] == "object"


def test_default_session_instructions_encode_clarification_and_policy_rules() -> None:
    instructions = DEFAULT_REALTIME_INSTRUCTIONS

    assert "one clarification question" in instructions
    assert "low_asr_confidence" in instructions
    assert "order_id_unconfirmed" in instructions
    assert "Do not approve refunds" in instructions


def test_voice_event_contains_redacted_structured_fields() -> None:
    event = VoiceEvent(
        event_id="event-123",
        timestamp="2026-05-29T09:00:00Z",
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        state=VoiceSessionState.TOOL_CALLING,
        event_type="tool_call",
        transcript_text_redacted="My order is [ORDER_REDACTED].",
        response_text_redacted=None,
        tool_name="lookup_order",
        tool_arguments_redacted={"order_id": "[ORDER_REDACTED]"},
        tool_result_summary="Order is paid.",
        handoff_reason=None,
        latency_ms=120,
        provider=RealtimeProviderName.MOCK,
        provider_event_type="response.function_call_arguments.done",
        provider_call_id="provider-call-123",
        tool_status="completed",
        redaction_applied=True,
    )

    assert event.state is VoiceSessionState.TOOL_CALLING
    assert event.tool_arguments_redacted == {"order_id": "[ORDER_REDACTED]"}
    assert event.provider_call_id == "provider-call-123"
    assert event.tool_status == "completed"


def test_voice_event_rejects_raw_audio_extra_field() -> None:
    try:
        VoiceEvent(
            event_id="event-123",
            timestamp="2026-05-29T09:00:00Z",
            session_id="session-123",
            call_id="call-123",
            merchant_id="merchant-123",
            state=VoiceSessionState.LISTENING,
            event_type="audio",
            transcript_text_redacted=None,
            response_text_redacted=None,
            tool_name=None,
            tool_arguments_redacted=None,
            tool_result_summary=None,
            handoff_reason=None,
            latency_ms=None,
            provider=RealtimeProviderName.MOCK,
            provider_event_type=None,
            provider_call_id=None,
            tool_status=None,
            redaction_applied=False,
            raw_audio=b"not-allowed",
        )
    except ValueError as error:
        assert "raw_audio" in str(error)
    else:
        raise AssertionError("VoiceEvent must reject raw_audio")
