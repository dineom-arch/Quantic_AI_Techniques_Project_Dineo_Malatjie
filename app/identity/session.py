"""In-memory authenticated session context for the synthetic demo."""

from __future__ import annotations

from threading import RLock
from datetime import datetime, timezone
from uuid import uuid4

from app.agent.context import ConversationTurn
from app.identity.models import EnterpriseIdentity, SessionIdentity
from app.identity.provider import IdentityProvider


class SessionNotFoundError(LookupError):
    pass


class IdentityNotFoundError(LookupError):
    pass


class SessionStore:
    """Stores server-side identity; prompt content is never consulted."""

    MAX_CONVERSATION_TURNS = 12

    def __init__(self, provider: IdentityProvider) -> None:
        self._provider = provider
        self._sessions: dict[str, EnterpriseIdentity] = {}
        self._conversation: dict[str, list[ConversationTurn]] = {}
        self._lock = RLock()

    def create(self, corporate_username: str) -> SessionIdentity:
        identity = self._provider.get_by_username(corporate_username)
        if identity is None:
            raise IdentityNotFoundError("Active Enterprise Identity not found")

        session_id = str(uuid4())
        with self._lock:
            self._sessions[session_id] = identity
            self._conversation[session_id] = []
        return SessionIdentity(session_id=session_id, identity=identity)

    def resolve(self, session_id: str) -> EnterpriseIdentity:
        with self._lock:
            identity = self._sessions.get(session_id)
        if identity is None:
            raise SessionNotFoundError("Authenticated session not found")
        return identity

    def history(self, session_id: str) -> tuple[ConversationTurn, ...]:
        self.resolve(session_id)
        with self._lock:
            return tuple(self._conversation.get(session_id, ()))

    def record_turn(
        self, session_id: str, user_message: str, assistant_answer: str,
        assistant_status: str,
    ) -> None:
        self.resolve(session_id)
        turn = ConversationTurn(
            user_message=user_message,
            assistant_answer=assistant_answer,
            assistant_status=assistant_status,
            recorded_at=datetime.now(timezone.utc),
        )
        with self._lock:
            turns = self._conversation.setdefault(session_id, [])
            turns.append(turn)
            del turns[:-self.MAX_CONVERSATION_TURNS]

    def end(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
            self._conversation.pop(session_id, None)

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._conversation.clear()

