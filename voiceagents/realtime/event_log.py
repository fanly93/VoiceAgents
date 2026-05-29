from typing import Protocol

from voiceagents.realtime.contracts import VoiceEvent


class VoiceEventRepository(Protocol):
    def append(self, event: VoiceEvent) -> None:
        raise NotImplementedError


class InMemoryVoiceEventRepository:
    def __init__(self) -> None:
        self.events: list[VoiceEvent] = []

    def append(self, event: VoiceEvent) -> None:
        self.events.append(event)
