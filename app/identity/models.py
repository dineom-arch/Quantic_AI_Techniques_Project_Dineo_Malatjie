"""Validated identity and session models."""

from pydantic import BaseModel, ConfigDict, Field


class EnterpriseIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    identity_id: str
    corporate_username: str
    display_name: str
    given_name: str
    surname: str
    employee_id: str
    job_title: str
    account_status: str


class IdentityOption(BaseModel):
    """Safe fields presented by the future demo identity selector."""

    corporate_username: str
    display_name: str
    job_title: str


class SessionIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str = Field(min_length=1)
    identity: EnterpriseIdentity

