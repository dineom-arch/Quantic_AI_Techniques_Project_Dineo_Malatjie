"""Application readiness endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    application: str
    mcp: str
    rag: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report honest Phase-1 component readiness."""

    return HealthResponse(
        status="degraded",
        application="meridian-compass",
        mcp="connected",
        rag="not_ready",
    )

