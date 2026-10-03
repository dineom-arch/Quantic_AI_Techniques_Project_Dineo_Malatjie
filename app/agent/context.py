"""Authenticated request context for deterministic evidence orchestration."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.identity.models import EnterpriseIdentity


class AgentContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    identity: EnterpriseIdentity
    message: str
    confirm_action: bool = False
    as_of: date = Field(default_factory=date.today)

