from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from voiceagents.contracts.common import HandoffReason
from voiceagents.realtime.contracts import VoiceSessionState


DEFAULT_TOOL_CALL_TOKEN_TTL_SECONDS = 600


@dataclass(frozen=True)
class TranscriptEntry:
    role: str
    text: str


@dataclass(frozen=True)
class ToolCallEntry:
    tool_name: str
    safe_summary: str


@dataclass
class VoiceSession:
    session_id: str
    call_id: str
    merchant_id: str
    state: VoiceSessionState
    token_hash: str
    token_expires_at: datetime
    transcripts: list[TranscriptEntry] = field(default_factory=list)
    tool_calls: list[ToolCallEntry] = field(default_factory=list)
    handoff_reason: HandoffReason | None = None
    handoff_id: str | None = None
    ended_at: datetime | None = None


@dataclass(frozen=True)
class CreatedVoiceSession:
    session: VoiceSession
    tool_call_token: str


class VoiceSessionNotFound(KeyError):
    pass


class InMemoryVoiceSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, VoiceSession] = {}

    def create_session(
        self,
        *,
        session_id: str,
        call_id: str,
        merchant_id: str,
        token_expires_at: datetime | None = None,
        now: datetime | None = None,
    ) -> CreatedVoiceSession:
        created_at = now or _utc_now()
        expires_at = token_expires_at or (
            created_at + timedelta(seconds=DEFAULT_TOOL_CALL_TOKEN_TTL_SECONDS)
        )
        token = secrets.token_urlsafe(32)
        session = VoiceSession(
            session_id=session_id,
            call_id=call_id,
            merchant_id=merchant_id,
            state=VoiceSessionState.IDLE,
            token_hash=_hash_token(token),
            token_expires_at=expires_at,
        )
        self._sessions[session_id] = session
        return CreatedVoiceSession(session=session, tool_call_token=token)

    def get_session(self, session_id: str) -> VoiceSession:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise VoiceSessionNotFound(session_id) from error

    def verify_tool_call_token(
        self,
        session_id: str,
        token: str,
        *,
        now: datetime | None = None,
    ) -> bool:
        session = self.get_session(session_id)
        if session.ended_at is not None:
            return False
        if (now or _utc_now()) >= session.token_expires_at:
            return False
        return hmac.compare_digest(session.token_hash, _hash_token(token))

    def update_state(self, session_id: str, state: VoiceSessionState) -> VoiceSession:
        session = self.get_session(session_id)
        session.state = state
        return session

    def append_transcript(self, session_id: str, role: str, text: str) -> VoiceSession:
        session = self.get_session(session_id)
        session.transcripts.append(TranscriptEntry(role=role, text=text))
        return session

    def append_tool_call(
        self,
        session_id: str,
        tool_name: str,
        safe_summary: str,
    ) -> VoiceSession:
        session = self.get_session(session_id)
        session.tool_calls.append(ToolCallEntry(tool_name=tool_name, safe_summary=safe_summary))
        return session

    def mark_handoff(
        self,
        session_id: str,
        handoff_reason: HandoffReason,
        handoff_id: str,
    ) -> VoiceSession:
        session = self.update_state(session_id, VoiceSessionState.HANDOFF_PENDING)
        session.handoff_reason = handoff_reason
        session.handoff_id = handoff_id
        return session

    def end_session(
        self,
        session_id: str,
        *,
        ended_at: datetime | None = None,
    ) -> VoiceSession:
        session = self.update_state(session_id, VoiceSessionState.ENDED)
        session.ended_at = ended_at or _utc_now()
        return session


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
