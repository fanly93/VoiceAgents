import pytest

from voiceagents.realtime.dashscope import (
    DEFAULT_DASHSCOPE_BASE_URL,
    DEFAULT_DASHSCOPE_REALTIME_MODEL,
    DashScopeRealtimeConfig,
)


def test_dashscope_config_uses_safe_defaults_without_key() -> None:
    config = DashScopeRealtimeConfig.from_env({})

    assert config.api_key is None
    assert config.has_api_key is False
    assert config.model == DEFAULT_DASHSCOPE_REALTIME_MODEL
    assert config.voice is None
    assert config.base_url == DEFAULT_DASHSCOPE_BASE_URL


def test_dashscope_config_reads_server_env_and_redacts_key() -> None:
    config = DashScopeRealtimeConfig.from_env(
        {
            "VOICEAGENTS_DASHSCOPE_API_KEY": "dashscope-secret",
            "VOICEAGENTS_DASHSCOPE_REALTIME_MODEL": "qwen3.5-omni-plus-realtime",
            "VOICEAGENTS_DASHSCOPE_REALTIME_VOICE": "longxiaochun",
            "VOICEAGENTS_DASHSCOPE_BASE_URL": "https://dashscope.aliyuncs.com/",
        }
    )

    assert config.has_api_key is True
    assert config.model == "qwen3.5-omni-plus-realtime"
    assert config.voice == "longxiaochun"
    assert config.base_url == "https://dashscope.aliyuncs.com"
    assert "dashscope-secret" not in config.safe_summary()


def test_dashscope_config_rejects_empty_model() -> None:
    with pytest.raises(ValueError, match="model"):
        DashScopeRealtimeConfig.from_env({"VOICEAGENTS_DASHSCOPE_REALTIME_MODEL": ""})
