from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import quote

from voiceagents.realtime.contracts import (
    ALLOWED_REALTIME_TOOL_NAMES,
    NormalizedRealtimeEventType,
    RealtimeClientSecretRequest,
    RealtimeClientSecretResponse,
    RealtimeConnectionMode,
    RealtimeEventIngestRequest,
    RealtimeProviderName,
    RealtimeSessionConfig,
    RealtimeToolDefinition,
    RealtimeToolCallRequest,
    RealtimeToolCallResponse,
    ResponseMode,
    VoiceSessionState,
    build_default_realtime_session_config,
)
from voiceagents.realtime.outbound import RealtimeBrowserProxyMessage


DEFAULT_DASHSCOPE_REALTIME_MODEL = "qwen3.5-omni-flash-realtime"
DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com"
DASHSCOPE_REALTIME_WS_PATH = "/api-ws/v1/realtime"
DASHSCOPE_PROXY_ROUTE_TEMPLATE = "/v1/realtime/dashscope/proxy/{session_id}"
DASHSCOPE_TRANSCRIPT_EVENT_MAP = {
    "dashscope.transcript.user.delta": (
        NormalizedRealtimeEventType.TRANSCRIPT_USER_DELTA,
        VoiceSessionState.TRANSCRIBING,
        "user",
    ),
    "dashscope.transcript.user.done": (
        NormalizedRealtimeEventType.TRANSCRIPT_USER_DONE,
        VoiceSessionState.THINKING,
        "user",
    ),
    "dashscope.transcript.assistant.delta": (
        NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DELTA,
        VoiceSessionState.SPEAKING,
        "assistant",
    ),
    "dashscope.transcript.assistant.done": (
        NormalizedRealtimeEventType.TRANSCRIPT_ASSISTANT_DONE,
        VoiceSessionState.LISTENING,
        "assistant",
    ),
}
ALLOWED_DASHSCOPE_PROXY_MESSAGE_TYPES = {"audio", "control", "tool_result"}
ALLOWED_DASHSCOPE_PROXY_MESSAGE_KEYS = {"type", "payload"}
BLOCKED_DASHSCOPE_PROXY_KEYS = {
    "api_key",
    "authorization",
    "client_secret",
    "dashscope_api_key",
    "raw_arguments",
    "sdp",
    "tool_call_token",
}


class RealtimeProviderError(RuntimeError):
    pass


class DashScopeEventError(ValueError):
    pass


@dataclass(frozen=True)
class DashScopeRealtimeConfig:
    api_key: str | None
    model: str
    voice: str | None
    base_url: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "DashScopeRealtimeConfig":
        model = env.get("VOICEAGENTS_DASHSCOPE_REALTIME_MODEL")
        normalized_model = model.strip() if model is not None else DEFAULT_DASHSCOPE_REALTIME_MODEL
        if not normalized_model:
            raise ValueError("DashScope realtime model must not be empty")

        base_url = env.get("VOICEAGENTS_DASHSCOPE_BASE_URL", DEFAULT_DASHSCOPE_BASE_URL)
        normalized_base_url = base_url.rstrip("/") or DEFAULT_DASHSCOPE_BASE_URL

        api_key = env.get("VOICEAGENTS_DASHSCOPE_API_KEY")
        normalized_api_key = api_key.strip() if api_key is not None else None
        return cls(
            api_key=normalized_api_key or None,
            model=normalized_model,
            voice=_optional_env_value(env, "VOICEAGENTS_DASHSCOPE_REALTIME_VOICE"),
            base_url=normalized_base_url,
        )

    @property
    def has_api_key(self) -> bool:
        return self.api_key is not None

    def safe_summary(self) -> str:
        key_status = "present" if self.has_api_key else "missing"
        return (
            f"DashScope realtime config: model={self.model}, "
            f"voice={self.voice or 'default'}, base_url={self.base_url}, api_key={key_status}"
        )


def _optional_env_value(env: Mapping[str, str], name: str) -> str | None:
    value = env.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class DashScopeRealtimeProvider:
    def __init__(self, config: DashScopeRealtimeConfig) -> None:
        self._config = config

    def create_client_secret(
        self,
        request: RealtimeClientSecretRequest,
    ) -> RealtimeClientSecretResponse:
        if not self._config.has_api_key:
            raise RealtimeProviderError(
                "DASHSCOPE_API_KEY is required for dashscope_realtime provider"
            )

        return RealtimeClientSecretResponse(
            provider=RealtimeProviderName.DASHSCOPE_REALTIME,
            session_id=request.session_id,
            call_id=request.call_id,
            client_secret=None,
            tool_call_token="provider-credentials-only",
            connection_url=DASHSCOPE_PROXY_ROUTE_TEMPLATE.format(session_id=request.session_id),
            connection_mode=RealtimeConnectionMode.SERVER_WEBSOCKET_PROXY,
            ephemeral_credential=None,
            expires_at=None,
            credential_expires_at=None,
            model=self._config.model,
            voice=self._config.voice,
            session_config=build_default_realtime_session_config(),
        )


class DashScopeRealtimeAdapter:
    def __init__(self, config: DashScopeRealtimeConfig) -> None:
        self._config = config

    def build_connection_url(self) -> str:
        base_url = self._config.base_url.rstrip("/")
        if base_url.startswith("https://"):
            ws_base_url = "wss://" + base_url.removeprefix("https://")
        elif base_url.startswith("http://"):
            ws_base_url = "ws://" + base_url.removeprefix("http://")
        elif base_url.startswith(("ws://", "wss://")):
            ws_base_url = base_url
        else:
            raise DashScopeEventError("DashScope base URL must include a supported scheme")
        model = quote(self._config.model, safe="")
        return f"{ws_base_url}{DASHSCOPE_REALTIME_WS_PATH}?model={model}"

    def build_headers(self) -> Mapping[str, str]:
        if self._config.api_key is None:
            raise DashScopeEventError("DashScope api key is required for outbound headers")
        return {"Authorization": f"Bearer {self._config.api_key}"}

    def safe_connection_summary(self) -> Mapping[str, object]:
        return {
            "provider": RealtimeProviderName.DASHSCOPE_REALTIME.value,
            "model": self._config.model,
            "voice": self._config.voice,
            "connection_mode": RealtimeConnectionMode.SERVER_WEBSOCKET_PROXY.value,
            "base_url": self._config.base_url.rstrip("/"),
            "api_key": "present" if self._config.has_api_key else "missing",
        }

    def build_session_update_message(
        self,
        session_config: RealtimeSessionConfig,
        *,
        response_mode: ResponseMode = ResponseMode.VOICE,
    ) -> Mapping[str, object]:
        modalities = ["text"] if response_mode is ResponseMode.TEXT else ["audio", "text"]
        session: dict[str, object] = {
            "modalities": modalities,
            "instructions": session_config.instructions,
            "input_audio_format": "pcm16",
            "output_audio_format": None if response_mode is ResponseMode.TEXT else "pcm16",
            "turn_detection": {"type": "server_vad"},
            "tools": _map_dashscope_tools(session_config.tools),
        }
        if response_mode is ResponseMode.VOICE and self._config.voice is not None:
            session["voice"] = self._config.voice
        return {"type": "session.update", "session": session}

    def map_browser_message(
        self,
        message: RealtimeBrowserProxyMessage,
    ) -> Mapping[str, object] | bytes | None:
        raise NotImplementedError

    def normalize_provider_event(
        self,
        payload: Mapping[str, object],
        *,
        session_id: str,
        call_id: str,
        merchant_id: str,
    ):
        return normalize_dashscope_event(
            payload,
            session_id=session_id,
            call_id=call_id,
            merchant_id=merchant_id,
        )

    def normalize_provider_tool_call(
        self,
        payload: Mapping[str, object],
        *,
        session_id: str,
        call_id: str,
        merchant_id: str,
    ) -> RealtimeToolCallRequest:
        return normalize_dashscope_tool_call(
            payload,
            session_id=session_id,
            call_id=call_id,
            merchant_id=merchant_id,
        )

    def build_tool_result_messages(
        self,
        response: RealtimeToolCallResponse,
        *,
        provider_call_id: str,
    ) -> list[Mapping[str, object]]:
        return [build_dashscope_tool_result_event(response, provider_call_id=provider_call_id)]


def normalize_dashscope_event(
    payload: Mapping[str, object],
    *,
    session_id: str,
    call_id: str,
    merchant_id: str,
) -> RealtimeEventIngestRequest:
    provider_event_type = _string_field(payload, "type")
    if provider_event_type == "dashscope.session.started":
        return _build_event(
            session_id=session_id,
            call_id=call_id,
            merchant_id=merchant_id,
            event_type=NormalizedRealtimeEventType.SESSION_CONNECTED,
            state=VoiceSessionState.LISTENING,
            provider_event_type=provider_event_type,
            provider_call_id=None,
        )
    if provider_event_type == "dashscope.session.finished":
        return _build_event(
            session_id=session_id,
            call_id=call_id,
            merchant_id=merchant_id,
            event_type=NormalizedRealtimeEventType.SESSION_ENDED,
            state=VoiceSessionState.ENDED,
            provider_event_type=provider_event_type,
            provider_call_id=None,
        )
    if provider_event_type == "dashscope.session.error":
        return _build_event(
            session_id=session_id,
            call_id=call_id,
            merchant_id=merchant_id,
            event_type=NormalizedRealtimeEventType.SESSION_ERROR,
            state=VoiceSessionState.ERROR,
            provider_event_type=provider_event_type,
            provider_call_id=None,
        )
    if provider_event_type in DASHSCOPE_TRANSCRIPT_EVENT_MAP:
        event_type, state, speaker = DASHSCOPE_TRANSCRIPT_EVENT_MAP[provider_event_type]
        return _build_event(
            session_id=session_id,
            call_id=call_id,
            merchant_id=merchant_id,
            event_type=event_type,
            state=state,
            provider_event_type=provider_event_type,
            provider_call_id=None,
            speaker=speaker,
            text=_string_field(payload, "text"),
        )
    raise DashScopeEventError(f"Unsupported DashScope event: {provider_event_type}")


def _map_dashscope_tools(tools: list[RealtimeToolDefinition]) -> list[dict[str, object]]:
    mapped_tools: list[dict[str, object]] = []
    for tool in tools:
        if tool.name not in ALLOWED_REALTIME_TOOL_NAMES:
            continue
        mapped_tools.append(
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_schema,
            }
        )
    return mapped_tools


def normalize_dashscope_tool_call(
    payload: Mapping[str, object],
    *,
    session_id: str,
    call_id: str,
    merchant_id: str,
) -> RealtimeToolCallRequest:
    provider_event_type = _string_field(payload, "type")
    if provider_event_type != "dashscope.tool_call.requested":
        raise DashScopeEventError(f"Unsupported DashScope tool event: {provider_event_type}")
    tool_name = _string_field(payload, "tool_name")
    if tool_name not in ALLOWED_REALTIME_TOOL_NAMES:
        raise DashScopeEventError(f"Unsupported DashScope tool: {tool_name}")
    arguments = payload.get("arguments")
    if not isinstance(arguments, dict):
        raise DashScopeEventError("DashScope tool call arguments must be an object")
    return RealtimeToolCallRequest(
        session_id=session_id,
        call_id=call_id,
        merchant_id=merchant_id,
        tool_name=tool_name,
        arguments=dict(arguments),
    )


def build_dashscope_tool_result_event(
    response: RealtimeToolCallResponse,
    *,
    provider_call_id: str,
) -> dict[str, object]:
    output: dict[str, object] = {
        "ok": response.ok,
        "safe_summary": response.safe_summary,
        "error_message": response.error_message,
        "error_code": response.error_code.value if response.error_code is not None else None,
        "handoff_required": response.handoff_required,
    }
    if response.ok:
        output["result"] = response.result
    return {
        "type": "dashscope.tool_result",
        "tool_call_id": provider_call_id,
        "tool_name": response.tool_name,
        "tool_status": response.tool_status.value,
        "output": output,
    }


def validate_dashscope_proxy_message(message: object) -> dict[str, object]:
    if not isinstance(message, dict):
        raise DashScopeEventError("DashScope proxy message must be an object")
    keys = set(message)
    if keys != ALLOWED_DASHSCOPE_PROXY_MESSAGE_KEYS:
        raise DashScopeEventError("DashScope proxy message has invalid top-level fields")
    message_type = message.get("type")
    if message_type not in ALLOWED_DASHSCOPE_PROXY_MESSAGE_TYPES:
        raise DashScopeEventError(f"Unsupported DashScope proxy message type: {message_type}")
    _reject_blocked_proxy_keys(message)
    payload = message.get("payload")
    if not isinstance(payload, dict):
        raise DashScopeEventError("DashScope proxy message payload must be an object")
    return {"type": message_type, "payload": dict(payload)}


def _reject_blocked_proxy_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in BLOCKED_DASHSCOPE_PROXY_KEYS:
                raise DashScopeEventError(f"DashScope proxy message contains blocked key: {key}")
            _reject_blocked_proxy_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_blocked_proxy_keys(child)


def _build_event(
    *,
    session_id: str,
    call_id: str,
    merchant_id: str,
    event_type: NormalizedRealtimeEventType,
    state: VoiceSessionState,
    provider_event_type: str,
    provider_call_id: str | None,
    speaker: str | None = None,
    text: str | None = None,
) -> RealtimeEventIngestRequest:
    return RealtimeEventIngestRequest(
        session_id=session_id,
        call_id=call_id,
        merchant_id=merchant_id,
        provider=RealtimeProviderName.DASHSCOPE_REALTIME,
        event_type=event_type,
        state=state,
        provider_event_type=provider_event_type,
        provider_call_id=provider_call_id,
        speaker=speaker,
        text=text,
    )


def _string_field(payload: Mapping[str, object], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        raise DashScopeEventError(f"DashScope event missing {name}")
    return value
