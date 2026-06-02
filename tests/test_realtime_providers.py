import pytest

from voiceagents.realtime.contracts import (
    ALLOWED_REALTIME_TOOL_NAMES,
    RealtimeConnectionMode,
    RealtimeClientSecretRequest,
    RealtimeProviderMode,
    RealtimeProviderName,
    ResponseMode,
    build_default_realtime_session_config,
)
from voiceagents.realtime.providers import (
    MockRealtimeProvider,
    OpenAIRealtimeProvider,
    RealtimeProviderError,
    get_realtime_provider_capabilities,
    map_realtime_tools_to_openai_tools,
)


class CapturingOpenAITransport:
    def __init__(self, response_body: dict[str, object] | None = None) -> None:
        self.response_body = response_body or {
            "client_secret": {
                "value": "openai-ephemeral-secret",
                "expires_at": "2026-05-31T12:00:00Z",
            }
        }
        self.calls: list[dict[str, object]] = []

    def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        json_body: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append({"url": url, "headers": headers, "json_body": json_body})
        return self.response_body


def make_client_secret_request(response_mode: ResponseMode = ResponseMode.TEXT) -> RealtimeClientSecretRequest:
    return RealtimeClientSecretRequest(
        session_id="session-123",
        call_id="call-123",
        merchant_id="merchant-123",
        response_mode=response_mode,
        locale="en-US",
        safety_subject_id="subject_hash_123",
    )


def test_realtime_provider_capabilities_include_supported_providers() -> None:
    capabilities = get_realtime_provider_capabilities()

    assert set(capabilities) == {
        RealtimeProviderName.MOCK,
        RealtimeProviderName.OPENAI_REALTIME,
        RealtimeProviderName.DASHSCOPE_REALTIME,
    }
    assert capabilities[RealtimeProviderName.OPENAI_REALTIME].supported_connection_modes == [
        RealtimeConnectionMode.BROWSER_WEBRTC_EPHEMERAL
    ]
    assert capabilities[RealtimeProviderName.DASHSCOPE_REALTIME].supported_provider_modes == [
        RealtimeProviderMode.NATIVE_REALTIME
    ]
    assert capabilities[RealtimeProviderName.DASHSCOPE_REALTIME].default_model == (
        "qwen3.5-omni-flash-realtime"
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


def test_openai_realtime_provider_posts_client_secret_request_to_openai() -> None:
    transport = CapturingOpenAITransport()
    provider = OpenAIRealtimeProvider(api_key="server-api-key", transport=transport)

    provider.create_client_secret(make_client_secret_request(ResponseMode.VOICE))

    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call["url"] == "https://api.openai.com/v1/realtime/client_secrets"
    assert call["headers"] == {
        "Authorization": "Bearer server-api-key",
        "Content-Type": "application/json",
        "OpenAI-Safety-Identifier": "subject_hash_123",
    }
    body = call["json_body"]
    assert body["expires_after"] == {"anchor": "created_at", "seconds": 600}
    session = body["session"]
    assert session["type"] == "realtime"
    assert session["model"] == "gpt-realtime-2"
    assert session["output_modalities"] == ["audio"]
    assert session["audio"]["output"]["voice"] == "marin"
    assert session["audio"]["input"]["transcription"] == {
        "model": "gpt-4o-mini-transcribe",
        "language": "en",
    }
    assert {tool["name"] for tool in session["tools"]} == ALLOWED_REALTIME_TOOL_NAMES
    assert session["tool_choice"] == "auto"


def test_openai_realtime_provider_sets_text_output_modality_for_text_mode() -> None:
    transport = CapturingOpenAITransport()
    provider = OpenAIRealtimeProvider(api_key="server-api-key", transport=transport)

    provider.create_client_secret(make_client_secret_request(ResponseMode.TEXT))

    session = transport.calls[0]["json_body"]["session"]
    assert session["output_modalities"] == ["text"]


def test_openai_realtime_provider_omits_safety_identifier_when_absent() -> None:
    transport = CapturingOpenAITransport()
    provider = OpenAIRealtimeProvider(api_key="server-api-key", transport=transport)
    request = make_client_secret_request()
    request.safety_subject_id = None

    provider.create_client_secret(request)

    assert "OpenAI-Safety-Identifier" not in transport.calls[0]["headers"]


def test_openai_realtime_provider_maps_client_secret_response() -> None:
    transport = CapturingOpenAITransport(
        {
            "client_secret": {
                "value": "openai-ephemeral-secret",
                "expires_at": "2026-05-31T12:00:00Z",
            }
        }
    )
    provider = OpenAIRealtimeProvider(
        api_key="server-api-key",
        model="gpt-realtime-custom",
        voice="cedar",
        transport=transport,
    )

    response = provider.create_client_secret(make_client_secret_request(ResponseMode.VOICE))

    assert response.provider is RealtimeProviderName.OPENAI_REALTIME
    assert response.session_id == "session-123"
    assert response.call_id == "call-123"
    assert response.client_secret == "openai-ephemeral-secret"
    assert response.expires_at == "2026-05-31T12:00:00Z"
    assert response.connection_url == "https://api.openai.com/v1/realtime/calls"
    assert response.model == "gpt-realtime-custom"
    assert response.voice == "cedar"
    assert response.tool_call_token == "provider-credentials-only"
    assert {tool.name for tool in response.session_config.tools} == ALLOWED_REALTIME_TOOL_NAMES
