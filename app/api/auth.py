"""Synthetic identity selector and server-side session endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.identity.models import IdentityOption
from app.identity.provider import IdentityProvider
from app.identity.session import IdentityNotFoundError, SessionStore


router = APIRouter(prefix="/auth", tags=["auth"])
identity_provider = IdentityProvider()
session_store = SessionStore(identity_provider)


class CreateSessionRequest(BaseModel):
    corporate_username: str


class CreateSessionResponse(BaseModel):
    session_id: str
    display_name: str
    job_title: str


@router.get("/identities", response_model=list[IdentityOption])
async def list_identities() -> list[IdentityOption]:
    return identity_provider.list_active_options()


@router.post("/session", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
    try:
        session = session_store.create(request.corporate_username)
    except IdentityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CreateSessionResponse(
        session_id=session.session_id,
        display_name=session.identity.display_name,
        job_title=session.identity.job_title,
    )

