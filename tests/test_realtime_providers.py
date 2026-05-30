import pytest

from voiceagents.realtime.contracts import (
    ALLOWED_REALTIME_TOOL_NAMES,
    RealtimeClientSecretRequest,
    RealtimeProviderName,
    ResponseMode,
    build_default_realtime_session_config,
)
from voiceagents.realtime.providers import (
    MockRealtimeProvider,
    OpenAIRealtimeProvider,
    RealtimeProviderError,
    map_realtime_tools_to_openai_tools,
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


def test_default_realtime_tools_map_to_openai_function_tools() -> None:
    config = build_default_realtime_session_config()

    tools = map_realtime_tools_to_openai_tools(config)

    assert {tool["name"] for tool in tools} == ALLOWED_REALTIME_TOOL_NAMES
    assert all(set(tool) == {"type", "name", "description", "parameters"} for tool in tools)
    assert all(tool["type"] == "function" for tool in tools)
    assert {
        tool["name"]: tool["parameters"]
        for tool in tools
    } == {
        tool.name: tool.parameters_schema
        for tool in config.tools
    }
