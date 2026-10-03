"""Deterministic, heading-first chunking for the controlled corpus.

Markdown level-1/2/3 headings establish semantic sections. Sections larger
than 1,800 characters are split on paragraph boundaries with one-paragraph
context overlap. Chunk IDs are stable hashes of authoritative content and
identity metadata.
"""

from __future__ import annotations

from hashlib import sha256
import re

from pydantic import BaseModel, ConfigDict

from rag.loaders import CorpusDocument


MAX_CHARS = 1800
HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)


class DocumentChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    document_id: str
    title: str
    document_type: str
    topic: str
    section: str
    effective_date: str
    version: str
    owner: str
    status: str
    source_path: str
    text: str


def _sections(content: str) -> list[tuple[str, str]]:
    matches = list(HEADING.finditer(content))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        body = content[start:end].strip()
        if body:
            sections.append((match.group(2).strip(), body))
    return sections


def _split_section(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    source_paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    paragraphs = [
        segment
        for paragraph in source_paragraphs
        for segment in _split_oversized_paragraph(paragraph, max_chars)
    ]
    chunks: list[str] = []
    current: list[str] = []
    for paragraph in paragraphs:
        proposed = "\n\n".join([*current, paragraph])
        if current and len(proposed) > max_chars:
            chunks.append("\n\n".join(current))
            current = [current[-1], paragraph] if len(current[-1]) + len(paragraph) + 2 <= max_chars else [paragraph]
        else:
            current.append(paragraph)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _split_oversized_paragraph(paragraph: str, max_chars: int) -> list[str]:
    """Split without rewriting or dropping text, preferring whitespace cuts."""

    segments: list[str] = []
    remaining = paragraph
    while len(remaining) > max_chars:
        whitespace = max(
            remaining.rfind(" ", 0, max_chars + 1),
            remaining.rfind("\t", 0, max_chars + 1),
            remaining.rfind("\n", 0, max_chars + 1),
        )
        cut = whitespace + 1 if whitespace >= 0 else max_chars
        segments.append(remaining[:cut])
        remaining = remaining[cut:]
    if remaining:
        segments.append(remaining)
    return segments


def chunk_documents(
    documents: list[CorpusDocument], *, max_chars: int = MAX_CHARS
) -> list[DocumentChunk]:
    if max_chars < 200:
        raise ValueError("max_chars must be at least 200")
    chunks: list[DocumentChunk] = []
    for document in documents:
        for section, body in _sections(document.content):
            for ordinal, text in enumerate(_split_section(body, max_chars), start=1):
                digest_input = f"{document.document_id}|{section}|{ordinal}|{text}"
                chunk_id = f"{document.document_id}-{sha256(digest_input.encode('utf-8')).hexdigest()[:16]}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document.document_id,
                        title=document.title,
                        document_type=document.document_type,
                        topic=document.topic,
                        section=section,
                        effective_date=document.effective_date,
                        version=document.version,
                        owner=document.owner,
                        status=document.status,
                        source_path=document.source_path,
                        text=text,
                    )
                )
    return chunks

