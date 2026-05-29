from voiceagents.realtime.contracts import (
    ALLOWED_REALTIME_TOOL_NAMES,
    RealtimeToolCallRequest,
)
from voiceagents.realtime.session_store import InMemoryVoiceSessionStore, VoiceSessionNotFound


class RealtimeToolRouterError(ValueError):
    status_code = 400


class UnknownRealtimeToolError(RealtimeToolRouterError):
    status_code = 400


class InvalidToolCallTokenError(RealtimeToolRouterError):
    status_code = 403


class RealtimeToolRouter:
    def __init__(self, *, session_store: InMemoryVoiceSessionStore) -> None:
        self._session_store = session_store

    def validate_request(self, request: RealtimeToolCallRequest, tool_call_token: str) -> None:
        if request.tool_name not in ALLOWED_REALTIME_TOOL_NAMES:
            raise UnknownRealtimeToolError(f"Unknown realtime tool: {request.tool_name}")

        try:
            token_is_valid = self._session_store.verify_tool_call_token(
                request.session_id,
                tool_call_token,
            )
        except VoiceSessionNotFound as error:
            raise InvalidToolCallTokenError("Invalid realtime tool-call session") from error

        if not token_is_valid:
            raise InvalidToolCallTokenError("Invalid realtime tool-call token")
