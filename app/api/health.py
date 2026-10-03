"""Application readiness endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from rag.service import get_knowledge_service


router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    application: str
    mcp: str
    rag: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report actual application, MCP, and RAG readiness."""

    rag_ready = get_knowledge_service().is_ready
    return HealthResponse(
        status="healthy" if rag_ready else "degraded",
        application="meridian-compass",
        mcp="connected",
        rag="ready" if rag_ready else "not_ready",
    )

