from collections.abc import Mapping
from dataclasses import dataclass

from voiceagents.realtime.contracts import (
    RealtimeClientSecretRequest,
    RealtimeClientSecretResponse,
    RealtimeConnectionMode,
    RealtimeProviderName,
    build_default_realtime_session_config,
)


DEFAULT_DASHSCOPE_REALTIME_MODEL = "qwen3.5-omni-flash-realtime"
DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com"
DASHSCOPE_PROXY_ROUTE_TEMPLATE = "/v1/realtime/dashscope/proxy/{session_id}"


class RealtimeProviderError(RuntimeError):
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
