"""Synthetic identity selector and server-side session endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.identity.models import IdentityOption
from app.identity.runtime import identity_provider, session_store
from app.identity.session import IdentityNotFoundError, SessionNotFoundError


router = APIRouter(prefix="/auth", tags=["auth"])
DEFAULT_DEMO_USERNAME = "naledi.molefe"


class CreateSessionRequest(BaseModel):
    corporate_username: str


class CreateSessionResponse(BaseModel):
    session_id: str
    display_name: str
    given_name: str
    job_title: str


@router.get("/identities", response_model=list[IdentityOption])
async def list_identities() -> list[IdentityOption]:
    return identity_provider.list_active_options()


@router.post("/session", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
    return _create_session_response(request.corporate_username)


@router.post("/demo-session", response_model=CreateSessionResponse)
async def create_demo_session() -> CreateSessionResponse:
    """Establish the configured flagship identity without browser selection."""
    return _create_session_response(DEFAULT_DEMO_USERNAME)


@router.get("/session/{session_id}", response_model=CreateSessionResponse)
async def validate_session(session_id: str) -> CreateSessionResponse:
    """Validate browser session state against server-side identity authority."""
    try:
        identity = session_store.resolve(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Authenticated session not found") from exc
    return CreateSessionResponse(
        session_id=session_id,
        display_name=identity.display_name,
        given_name=identity.given_name,
        job_title=identity.job_title,
    )


def _create_session_response(corporate_username: str) -> CreateSessionResponse:
    try:
        session = session_store.create(corporate_username)
    except IdentityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CreateSessionResponse(
        session_id=session.session_id,
        display_name=session.identity.display_name,
        given_name=session.identity.given_name,
        job_title=session.identity.job_title,
    )


@router.delete("/session/{session_id}", status_code=204)
async def end_session(session_id: str) -> None:
    """End a synthetic demo session and discard its conversational context."""
    session_store.end(session_id)

