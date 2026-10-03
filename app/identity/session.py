"""In-memory authenticated session context for the synthetic demo."""

from __future__ import annotations

from threading import RLock
from uuid import uuid4

from app.identity.models import EnterpriseIdentity, SessionIdentity
from app.identity.provider import IdentityProvider


class SessionNotFoundError(LookupError):
    pass


class IdentityNotFoundError(LookupError):
    pass


class SessionStore:
    """Stores server-side identity; prompt content is never consulted."""

    def __init__(self, provider: IdentityProvider) -> None:
        self._provider = provider
        self._sessions: dict[str, EnterpriseIdentity] = {}
        self._lock = RLock()

    def create(self, corporate_username: str) -> SessionIdentity:
        identity = self._provider.get_by_username(corporate_username)
        if identity is None:
            raise IdentityNotFoundError("Active Enterprise Identity not found")

        session_id = str(uuid4())
        with self._lock:
            self._sessions[session_id] = identity
        return SessionIdentity(session_id=session_id, identity=identity)

    def resolve(self, session_id: str) -> EnterpriseIdentity:
        with self._lock:
            identity = self._sessions.get(session_id)
        if identity is None:
            raise SessionNotFoundError("Authenticated session not found")
        return identity

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()

