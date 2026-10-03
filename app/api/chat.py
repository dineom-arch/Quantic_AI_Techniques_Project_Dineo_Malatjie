"""Canonical chat endpoint backed by Phase-3B evidence orchestration."""

from typing import Any, Literal

from fastapi import APIRouter, Request
import httpx
from pydantic import BaseModel, Field

from app.agent.context import AgentContext
from app.agent.orchestrator import EvidenceOrchestrator
from app.agent.synthesis import GroundedSynthesizer
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
        provider = request.app.state.llm_provider
        if provider is None and result.status == "sufficient_evidence":
            answer = "The configured language-model service is unavailable. No policy answer was generated."
            grounded_status = "tool_error"
            verified_citations = []
            verified_snippets = []
            synthesis_trace = []
        else:
            try:
                grounded = await GroundedSynthesizer(provider, mcp_client).synthesize(
                    AgentContext(
                        session_id=chat_request.session_id,
                        identity=identity,
                        message=chat_request.message,
                        confirm_action=chat_request.confirm_action,
                    ),
                    result,
                )
                answer = grounded.answer
                grounded_status = grounded.status
                verified_citations = grounded.citations
                verified_snippets = grounded.source_snippets
                synthesis_trace = grounded.trace_events
            except Exception:
                answer = "The configured language-model service is unavailable. No policy answer was generated."
                grounded_status = "tool_error"
                verified_citations = []
                verified_snippets = []
                synthesis_trace = []
    return ChatResponse(
        answer=answer,
        status=grounded_status,
        citations=[Citation(**item.model_dump()) for item in verified_citations],
        source_snippets=[
            SourceSnippet(document_id=item.document_id, section=item.section, snippet=item.snippet)
            for item in verified_snippets
        ],
        tool_trace=[
            ToolTraceEntry(**trace.model_dump())
            for trace in [*result.tool_trace, *synthesis_trace]
        ],
    )

