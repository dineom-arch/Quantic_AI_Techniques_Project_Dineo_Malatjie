"""Canonical chat endpoint backed by Phase-3B evidence orchestration."""

from typing import Any, Literal

from fastapi import APIRouter, Request
import httpx
from pydantic import BaseModel, Field

from app.agent.context import AgentContext
from app.agent.orchestrator import EvidenceOrchestrator
from app.api.auth import session_store
from app.identity.session import SessionNotFoundError
from app.integrations.mcp_runtime import meridian_mcp_client_class


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
    sequence: int | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    summary: str | None = None
    source: str | None = None
    duration_ms: float | None = None


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


PUBLIC_STATUS = {
    "sufficient_evidence": "answered",
    "insufficient_evidence": "insufficient_evidence",
    "forbidden": "forbidden",
    "not_found": "not_found",
    "invalid_request": "clarification_required",
    "confirmation_required": "action_confirmation_required",
    "dependency_unavailable": "tool_error",
    "out_of_scope": "out_of_scope",
}


@router.post("/chat", response_model=ChatResponse, response_model_exclude_none=True)
async def chat(chat_request: ChatRequest, request: Request) -> ChatResponse:
    """Collect authoritative evidence without performing final policy synthesis."""

    try:
        identity = session_store.resolve(chat_request.session_id)
    except SessionNotFoundError:
        return ChatResponse(
            answer="The authenticated session was not found.",
            status="not_found",
            citations=[],
            source_snippets=[],
            tool_trace=[{"event": "authenticated_identity_load", "status": "not_found"}],
        )

    endpoint = "http://127.0.0.1:8000/mcp/"
    transport = httpx.ASGITransport(app=request.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as http_client:
        mcp_client = meridian_mcp_client_class()(
            endpoint, session_id=chat_request.session_id, http_client=http_client
        )
        result = await EvidenceOrchestrator(mcp_client).run(
            AgentContext(
                session_id=chat_request.session_id,
                identity=identity,
                message=chat_request.message,
                confirm_action=chat_request.confirm_action,
            )
        )

    knowledge = [item for item in result.evidence.items if item.evidence_type == "knowledge"]
    citations: list[Citation] = []
    seen: set[tuple[str, str]] = set()
    for item in knowledge:
        key = (item.document_id or "", item.section or "")
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            Citation(
                document_id=item.document_id or "",
                title=item.document_title or "",
                section=item.section or "",
                snippet=item.snippet or "",
            )
        )
    if result.status == "sufficient_evidence":
        answer = (
            "Authoritative operational and knowledge evidence was collected. "
            "Final grounded policy-answer synthesis is not implemented in Phase 3B."
        )
    else:
        answer = result.message
    return ChatResponse(
        answer=answer,
        status=PUBLIC_STATUS[result.status],
        citations=citations,
        source_snippets=[
            SourceSnippet(
                document_id=item.document_id or "",
                section=item.section or "",
                snippet=item.snippet or "",
            )
            for item in knowledge
        ],
        tool_trace=[ToolTraceEntry(**trace.model_dump()) for trace in result.tool_trace],
    )

