import voiceagents.adapters
import voiceagents.agent
import voiceagents.api
import voiceagents.contracts
import voiceagents.realtime


def test_backend_packages_are_importable() -> None:
    assert voiceagents.contracts.__name__ == "voiceagents.contracts"
    assert voiceagents.adapters.__name__ == "voiceagents.adapters"
    assert voiceagents.agent.__name__ == "voiceagents.agent"
    assert voiceagents.api.__name__ == "voiceagents.api"
    assert voiceagents.realtime.__name__ == "voiceagents.realtime"
