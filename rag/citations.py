"""Human-readable citation models."""

from pydantic import BaseModel


class Citation(BaseModel):
    document_id: str
    title: str
    section: str
    snippet: str

