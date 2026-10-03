"""Safe architectural trace models."""

from pydantic import BaseModel


class TraceEvent(BaseModel):
    event: str
    status: str
    duration_ms: float | None = None

