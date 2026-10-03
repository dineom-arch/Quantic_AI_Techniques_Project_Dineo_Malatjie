"""Canonical chat endpoint with a Phase-1 non-substantive placeholder."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.auth import session_store
from app.identity.session import SessionNotFoundError


router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    confirm_action: bool = False


class Citation(BaseModel):
    document_id: str
    title: str
    section: str
    snippet: str


class SourceSnippet(BaseModel):
    document_id: str
    section: str
    snippet: str


class ToolTraceEntry(BaseModel):
    event: str
    status: str


PublicStatus = Literal[
    "answered",
    "insufficient_evidence",
    "clarification_required",
    "action_confirmation_required",
    "forbidden",
    "not_found",
    "out_of_scope",
    "tool_error",
]


class ChatResponse(BaseModel):
    answer: str
    status: PublicStatus
    citations: list[Citation]
    source_snippets: list[SourceSnippet]
    tool_trace: list[ToolTraceEntry]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Return the canonical schema without Phase-2 agent behavior."""

    try:
        session_store.resolve(request.session_id)
    except SessionNotFoundError:
        return ChatResponse(
            answer="The authenticated session was not found.",
            status="not_found",
            citations=[],
            source_snippets=[],
            tool_trace=[{"event": "authenticated_identity_load", "status": "not_found"}],
        )

    return ChatResponse(
        answer="Meridian Compass chat workflows are not available in the Phase-1 foundation.",
        status="insufficient_evidence",
        citations=[],
        source_snippets=[],
        tool_trace=[
            {"event": "authenticated_identity_loaded", "status": "ok"},
            {"event": "phase_1_placeholder", "status": "not_ready"},
        ],
    )

