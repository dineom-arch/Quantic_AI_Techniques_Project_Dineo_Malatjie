"""Section-aware chunking models."""

from pydantic import BaseModel


class DocumentChunk(BaseModel):
    document_id: str
    title: str
    document_type: str
    topic: str
    section: str
    effective_date: str
    text: str

