from voiceagents.realtime.contracts import (
    RealtimeClientSecretRequest,
    RealtimeClientSecretResponse,
    RealtimeProviderName,
    RealtimeSessionConfig,
    RealtimeToolDefinition,
    ResponseMode,
    VoiceSessionState,
)


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
