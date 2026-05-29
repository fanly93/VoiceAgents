import pytest

from voiceagents.realtime.contracts import (
    ALLOWED_REALTIME_TOOL_NAMES,
    RealtimeClientSecretRequest,
    RealtimeProviderName,
    ResponseMode,
)
from voiceagents.realtime.providers import (
    MockRealtimeProvider,
    OpenAIRealtimeProvider,
    RealtimeProviderError,
)


def make_client_secret_request(response_mode: ResponseMode = ResponseMode.TEXT) -> RealtimeClientSecretRequest:
    return RealtimeClientSecretRequest(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        response_mode=response_mode,
        locale="en-US",
        safety_subject_id="subject_hash_123",
    )


def test_mock_realtime_provider_returns_deterministic_credentials() -> None:
    provider = MockRealtimeProvider()

    response = provider.create_client_secret(make_client_secret_request())

    assert response.provider is RealtimeProviderName.MOCK
    assert response.client_secret == "mock-client-secret-session-123"
    assert response.tool_call_token == "mock-tool-call-token-session-123"
    assert response.model == "mock-realtime"
    assert {tool.name for tool in response.session_config.tools} == ALLOWED_REALTIME_TOOL_NAMES


def test_mock_realtime_provider_sets_voice_only_for_voice_mode() -> None:
    provider = MockRealtimeProvider()

    text_response = provider.create_client_secret(make_client_secret_request(ResponseMode.TEXT))
    voice_response = provider.create_client_secret(make_client_secret_request(ResponseMode.VOICE))

    assert text_response.voice is None
    assert voice_response.voice == "mock-voice"


def test_openai_realtime_provider_fails_without_api_key() -> None:
    provider = OpenAIRealtimeProvider(api_key=None, model="gpt-realtime", voice="alloy")

    with pytest.raises(RealtimeProviderError, match="OPENAI_API_KEY"):
        provider.create_client_secret(make_client_secret_request())
