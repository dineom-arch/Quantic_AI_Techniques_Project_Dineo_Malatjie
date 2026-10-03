"""Citations constructed only from retrieved authoritative metadata."""

from pydantic import BaseModel


class Citation(BaseModel):
    document_id: str
    title: str
    section: str
    snippet: str


def citation_from_result(result, *, snippet_chars: int = 600) -> Citation:
    return Citation(
        document_id=result.document_id,
        title=result.title,
        section=result.section,
        snippet=result.text[:snippet_chars].strip(),
    )

