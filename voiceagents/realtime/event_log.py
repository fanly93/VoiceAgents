import json
from pathlib import Path
from typing import Protocol

from voiceagents.realtime.contracts import VoiceEvent
from voiceagents.realtime.redaction import Redactor, redact_mapping


DEFAULT_EVENT_LOG_PATH = Path(".voiceagents/events/realtime-events.jsonl")
BLOCKED_EVENT_KEYS = frozenset(
    {
        "raw_audio",
        "audio",
        "audio_bytes",
        "client_secret",
        "tool_call_token",
        "authorization",
    }
)


class VoiceEventRepository(Protocol):
    def append(self, event: VoiceEvent) -> None:
        raise NotImplementedError


class InMemoryVoiceEventRepository:
    def __init__(self) -> None:
        self.events: list[VoiceEvent] = []

    def append(self, event: VoiceEvent) -> None:
        self.events.append(event)


class JsonlVoiceEventRepository:
    def __init__(
        self,
        path: str | Path = DEFAULT_EVENT_LOG_PATH,
        *,
        redactor: Redactor | None = None,
    ) -> None:
        self._path = Path(path)
        self._redactor = redactor

    def append(self, event: VoiceEvent) -> None:
        payload = event.model_dump(mode="json")
        sanitized = _sanitize_mapping(payload)
        redaction_result = (
            self._redactor.redact_mapping(sanitized)
            if self._redactor is not None
            else redact_mapping(sanitized)
        )
        redacted_payload = redaction_result.value
        redacted_payload["redaction_applied"] = (
            bool(redacted_payload.get("redaction_applied")) or redaction_result.redaction_applied
        )

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(redacted_payload, sort_keys=True) + "\n")


def _sanitize_mapping(data: dict[str, object]) -> dict[str, object]:
    sanitized: dict[str, object] = {}
    for key, value in data.items():
        normalized_key = key.lower().replace("-", "_")
        if normalized_key in BLOCKED_EVENT_KEYS:
            continue
        sanitized[key] = _sanitize_value(value)
    return sanitized


def _sanitize_value(value: object) -> object:
    if isinstance(value, dict):
        return _sanitize_mapping(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value
