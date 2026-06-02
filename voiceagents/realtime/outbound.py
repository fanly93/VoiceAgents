from collections.abc import Mapping
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from voiceagents.realtime.contracts import (
    RealtimeEventIngestRequest,
    RealtimeSessionConfig,
    RealtimeToolCallRequest,
    RealtimeToolCallResponse,
)


class RealtimeOutboundEventKind(StrEnum):
    JSON = "json"
    AUDIO = "audio"
    CLOSE = "close"
    ERROR = "error"


class RealtimeBrowserProxyMessageType(StrEnum):
    AUDIO = "audio"
    CONTROL = "control"
    TOOL_RESULT = "tool_result"


BLOCKED_BROWSER_PROXY_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "client_secret",
        "dashscope_api_key",
        "raw_arguments",
        "raw_audio",
        "sdp",
        "tool_call_token",
    }
)


class RealtimeSafeProviderError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    safe_summary: str = Field(min_length=1)
    provider_event_type: str | None = Field(default=None, min_length=1)

    @field_validator("safe_summary")
    @classmethod
    def reject_secret_bearing_summary(cls, value: str) -> str:
        normalized = value.lower()
        for key in BLOCKED_BROWSER_PROXY_KEYS:
            if key in normalized:
                raise ValueError(f"safe_summary must not contain {key}")
        if "bearer " in normalized:
            raise ValueError("safe_summary must not contain bearer credentials")
        return value


class RealtimeOutboundEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    kind: RealtimeOutboundEventKind
    payload: dict[str, object] | None = None
    audio: bytes | None = None
    close_code: int | None = Field(default=None, ge=1000, le=4999)
    safe_summary: str | None = Field(default=None, min_length=1)
    safe_error: RealtimeSafeProviderError | None = None

    @model_validator(mode="after")
    def validate_kind_shape(self) -> "RealtimeOutboundEvent":
        if self.kind is RealtimeOutboundEventKind.JSON and self.payload is None:
            raise ValueError("payload is required for json outbound events")
        if self.kind is RealtimeOutboundEventKind.AUDIO and self.audio is None:
            raise ValueError("audio is required for audio outbound events")
        if self.kind is RealtimeOutboundEventKind.CLOSE and self.close_code is None:
            raise ValueError("close_code is required for close outbound events")
        if self.kind is RealtimeOutboundEventKind.ERROR and self.safe_error is None:
            raise ValueError("safe_error is required for error outbound events")
        return self


class RealtimeBrowserProxyMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: RealtimeBrowserProxyMessageType
    payload: dict[str, object]

    @model_validator(mode="after")
    def reject_blocked_payload_keys(self) -> "RealtimeBrowserProxyMessage":
        blocked_key = _find_blocked_key(self.payload)
        if blocked_key is not None:
            raise ValueError(f"browser proxy payload must not contain {blocked_key}")
        return self


@runtime_checkable
class RealtimeOutboundTransport(Protocol):
    async def connect(self) -> None:
        ...

    async def send_json(self, payload: Mapping[str, object]) -> None:
        ...

    async def send_audio(self, audio: bytes) -> None:
        ...

    async def receive(self) -> RealtimeOutboundEvent:
        ...

    async def close(self) -> None:
        ...


@runtime_checkable
class NativeRealtimeProviderAdapter(Protocol):
    def build_connection_url(self) -> str:
        ...

    def build_headers(self) -> Mapping[str, str]:
        ...

    def build_session_update_message(
        self,
        session_config: RealtimeSessionConfig,
    ) -> Mapping[str, object]:
        ...

    def map_browser_message(
        self,
        message: RealtimeBrowserProxyMessage,
    ) -> Mapping[str, object] | bytes | None:
        ...

    def normalize_provider_event(
        self,
        payload: Mapping[str, object],
        *,
        session_id: str,
        call_id: str,
        merchant_id: str,
    ) -> RealtimeOutboundEvent | RealtimeEventIngestRequest:
        ...

    def normalize_provider_tool_call(
        self,
        payload: Mapping[str, object],
        *,
        session_id: str,
        call_id: str,
        merchant_id: str,
    ) -> RealtimeToolCallRequest:
        ...

    def build_tool_result_messages(
        self,
        response: RealtimeToolCallResponse,
        *,
        provider_call_id: str,
    ) -> list[Mapping[str, object]]:
        ...

    def safe_connection_summary(self) -> Mapping[str, object]:
        ...


def _find_blocked_key(value: object) -> str | None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if str(key).lower() in BLOCKED_BROWSER_PROXY_KEYS:
                return str(key)
            nested_blocked_key = _find_blocked_key(nested_value)
            if nested_blocked_key is not None:
                return nested_blocked_key
    if isinstance(value, list):
        for item in value:
            nested_blocked_key = _find_blocked_key(item)
            if nested_blocked_key is not None:
                return nested_blocked_key
    return None
