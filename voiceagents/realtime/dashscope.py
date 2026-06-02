from collections.abc import Mapping
from dataclasses import dataclass


DEFAULT_DASHSCOPE_REALTIME_MODEL = "qwen3.5-omni-flash-realtime"
DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com"


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
