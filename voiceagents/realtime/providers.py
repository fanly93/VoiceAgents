from collections.abc import Iterable
from datetime import datetime, timezone
import json
from typing import Protocol
from urllib import error, request as urllib_request

from voiceagents.realtime.contracts import (
    RealtimeClientSecretRequest,
    RealtimeClientSecretResponse,
    RealtimeProviderName,
    RealtimeSessionConfig,
    RealtimeToolDefinition,
    ResponseMode,
    build_default_realtime_session_config,
)


OPENAI_CLIENT_SECRETS_URL = "https://api.openai.com/v1/realtime/client_secrets"
OPENAI_REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls"
DEFAULT_OPENAI_REALTIME_MODEL = "gpt-realtime-2"
DEFAULT_OPENAI_REALTIME_VOICE = "marin"
DEFAULT_OPENAI_INPUT_TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
DEFAULT_OPENAI_CLIENT_SECRET_TTL_SECONDS = 600


class RealtimeProviderError(RuntimeError):
    pass


class OpenAIJsonTransport(Protocol):
    def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        json_body: dict[str, object],
    ) -> dict[str, object]:
        raise NotImplementedError


class UrllibOpenAIJsonTransport:
    def post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        json_body: dict[str, object],
    ) -> dict[str, object]:
        body = json.dumps(json_body).encode("utf-8")
        http_request = urllib_request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib_request.urlopen(http_request, timeout=20) as response:
                response_body = response.read().decode("utf-8")
        except error.HTTPError as http_error:
            raise RealtimeProviderError(
                f"OpenAI Realtime client-secret request failed with status {http_error.code}"
            ) from http_error
        except error.URLError as url_error:
            raise RealtimeProviderError("OpenAI Realtime client-secret request failed") from url_error

        parsed_body = json.loads(response_body)
        if not isinstance(parsed_body, dict):
            raise RealtimeProviderError("OpenAI Realtime client-secret response was not an object")
        return parsed_body


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
        model: str | None = None,
        voice: str | None = None,
        transport: OpenAIJsonTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model or DEFAULT_OPENAI_REALTIME_MODEL
        self._voice = voice or DEFAULT_OPENAI_REALTIME_VOICE
        self._transport = transport or UrllibOpenAIJsonTransport()

    def create_client_secret(
        self,
        request: RealtimeClientSecretRequest,
    ) -> RealtimeClientSecretResponse:
        if not self._api_key:
            raise RealtimeProviderError("OPENAI_API_KEY is required for openai_realtime provider")

        session_config = build_default_realtime_session_config()
        response_body = self._transport.post_json(
            url=OPENAI_CLIENT_SECRETS_URL,
            headers=self._build_headers(request),
            json_body=self._build_client_secret_body(session_config, request),
        )
        client_secret, expires_at = self._parse_client_secret_response(response_body)
        return RealtimeClientSecretResponse(
            provider=RealtimeProviderName.OPENAI_REALTIME,
            session_id=request.session_id,
            call_id=request.call_id,
            client_secret=client_secret,
            tool_call_token="provider-credentials-only",
            connection_url=OPENAI_REALTIME_CALLS_URL,
            expires_at=expires_at,
            model=self._model,
            voice=self._voice,
            session_config=session_config,
        )

    def _build_headers(self, request: RealtimeClientSecretRequest) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if request.safety_subject_id:
            headers["OpenAI-Safety-Identifier"] = request.safety_subject_id
        return headers

    def _build_client_secret_body(
        self,
        session_config: RealtimeSessionConfig,
        request: RealtimeClientSecretRequest,
    ) -> dict[str, object]:
        return {
            "expires_after": {
                "anchor": "created_at",
                "seconds": DEFAULT_OPENAI_CLIENT_SECRET_TTL_SECONDS,
            },
            "session": {
                "type": "realtime",
                "model": self._model,
                "instructions": session_config.instructions,
                "output_modalities": _output_modalities(request.response_mode),
                "audio": {
                    "input": {
                        "transcription": {
                            "model": DEFAULT_OPENAI_INPUT_TRANSCRIPTION_MODEL,
                            "language": _locale_language(request.locale),
                        }
                    },
                    "output": {"voice": self._voice},
                },
                "tools": map_realtime_tools_to_openai_tools(session_config),
                "tool_choice": "auto",
            },
        }

    def _parse_client_secret_response(
        self,
        response_body: dict[str, object],
    ) -> tuple[str, str | None]:
        client_secret_body = response_body.get("client_secret")
        if isinstance(client_secret_body, dict):
            value = client_secret_body.get("value")
            expires_at = client_secret_body.get("expires_at")
        else:
            value = response_body.get("value")
            expires_at = response_body.get("expires_at")

        if not isinstance(value, str) or not value:
            raise RealtimeProviderError("OpenAI Realtime client-secret response missing value")

        return value, _normalize_openai_expires_at(expires_at)


def _normalize_openai_expires_at(expires_at: object) -> str | None:
    if expires_at is None:
        return None
    if isinstance(expires_at, str):
        return expires_at
    if isinstance(expires_at, int | float):
        return datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    raise RealtimeProviderError("OpenAI Realtime client-secret response has invalid expires_at")


def _locale_language(locale: str) -> str:
    language = locale.split("-", 1)[0].strip().lower()
    return language or "en"


def _output_modalities(response_mode: ResponseMode) -> list[str]:
    return ["audio"] if response_mode is ResponseMode.VOICE else ["text"]
