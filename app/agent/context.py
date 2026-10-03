"""Request context models for later workflow orchestration."""

from pydantic import BaseModel, ConfigDict

from app.identity.models import EnterpriseIdentity


class AgentContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    identity: EnterpriseIdentity
    message: str
    confirm_action: bool = False

