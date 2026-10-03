"""Safe architectural trace models without reasoning or private payloads."""

from typing import Any

from pydantic import BaseModel


class TraceEvent(BaseModel):
    event: str
    status: str
    sequence: int | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    summary: str | None = None
    source: str | None = None
    duration_ms: float | None = None

