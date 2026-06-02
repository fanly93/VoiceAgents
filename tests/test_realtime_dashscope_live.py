import asyncio
import os
from pathlib import Path

import pytest

from voiceagents.realtime.contracts import build_default_realtime_session_config
from voiceagents.realtime.dashscope import DashScopeRealtimeAdapter, DashScopeRealtimeConfig
from voiceagents.realtime.dashscope_transport import DashScopeRealtimeTransport
from voiceagents.realtime.outbound import RealtimeOutboundEventKind


ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
LIVE_TEST_FLAG = "VOICEAGENTS_RUN_DASHSCOPE_LIVE_TESTS"


def _load_dotenv_without_overriding() -> dict[str, str]:
    source = dict(os.environ)
    if not ENV_PATH.exists():
        return source
    for raw_line in ENV_PATH.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in source:
            continue
        source[key] = _strip_env_value(value.strip())
    return source


def _strip_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _dashscope_live_config() -> DashScopeRealtimeConfig:
    source = _load_dotenv_without_overriding()
    if source.get(LIVE_TEST_FLAG) != "true":
        pytest.skip(f"set {LIVE_TEST_FLAG}=true to run the DashScope live test")
    api_key = source.get("VOICEAGENTS_DASHSCOPE_API_KEY", "").strip()
    if not api_key or "replace" in api_key.lower() or "placeholder" in api_key.lower():
        pytest.skip("VOICEAGENTS_DASHSCOPE_API_KEY is required for the DashScope live test")
    return DashScopeRealtimeConfig.from_env(source)


@pytest.mark.anyio
async def test_dashscope_realtime_transport_connects_to_live_model() -> None:
    config = _dashscope_live_config()
    adapter = DashScopeRealtimeAdapter(config)
    transport = DashScopeRealtimeTransport(adapter)

    try:
        await asyncio.wait_for(transport.connect(), timeout=20)
        await asyncio.wait_for(
            transport.send_json(
                adapter.build_session_update_message(build_default_realtime_session_config())
            ),
            timeout=20,
        )
        event = await asyncio.wait_for(transport.receive(), timeout=30)
    finally:
        await transport.close()

    assert event.kind is RealtimeOutboundEventKind.JSON
    assert event.payload is not None
    event_type = event.payload.get("type")
    assert isinstance(event_type, str), "DashScope live event did not include a string type"
    assert config.api_key is not None
    contains_api_key = config.api_key in str(event.payload)
    assert contains_api_key is False
