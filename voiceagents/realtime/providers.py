from collections.abc import Iterable
from typing import Protocol

from voiceagents.realtime.contracts import (
    RealtimeClientSecretRequest,
    RealtimeClientSecretResponse,
    RealtimeProviderName,
    RealtimeSessionConfig,
    RealtimeToolDefinition,
    build_default_realtime_session_config,
)


class RealtimeProviderError(RuntimeError):
    pass


def map_realtime_tools_to_openai_tools(
    config_or_tools: RealtimeSessionConfig | Iterable[RealtimeToolDefinition],
) -> list[dict[str, object]]:
    tools = config_or_tools.tools if isinstance(config_or_tools, RealtimeSessionConfig) else config_or_tools
    return [
        {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters_schema,
        }
        for tool in tools
    ]


class RealtimeProvider(Protocol):
    def create_client_secret(
        self,
        request: RealtimeClientSecretRequest,
    ) -> RealtimeClientSecretResponse:
        raise NotImplementedError


class MockRealtimeProvider:
    def create_client_secret(
        self,
        request: RealtimeClientSecretRequest,
    ) -> RealtimeClientSecretResponse:
        return RealtimeClientSecretResponse(
            provider=RealtimeProviderName.MOCK,
            session_id=request.session_id,
            call_id=request.call_id,
            client_secret=f"mock-client-secret-{request.session_id}",
            tool_call_token=f"mock-tool-call-token-{request.session_id}",
            connection_url="https://example.invalid/realtime/mock",
            expires_at=None,
            model="mock-realtime",
            voice="mock-voice" if request.response_mode == "voice" else None,
            session_config=build_default_realtime_session_config(),
        )


class OpenAIRealtimeProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        voice: str | None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._voice = voice

    def create_client_secret(
        self,
        request: RealtimeClientSecretRequest,
    ) -> RealtimeClientSecretResponse:
        if not self._api_key:
            raise RealtimeProviderError("OPENAI_API_KEY is required for openai_realtime provider")

        raise RealtimeProviderError(
            "OpenAI Realtime client-secret creation is not wired in this task yet"
        )
