"""Authenticated request context for deterministic evidence orchestration."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.identity.models import EnterpriseIdentity


class ConversationTurn(BaseModel):
    """Bounded session context. Content is user-stated, never authoritative evidence."""

    model_config = ConfigDict(frozen=True)

    user_message: str
    assistant_status: str
    assistant_answer: str
    recorded_at: datetime


class AgentContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    identity: EnterpriseIdentity
    message: str
    confirm_action: bool = False
    as_of: date = Field(default_factory=date.today)
    conversation_history: tuple[ConversationTurn, ...] = ()

