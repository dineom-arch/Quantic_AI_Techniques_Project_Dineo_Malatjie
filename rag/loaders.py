"""Validated loading of the approved canonical Markdown corpus."""

from __future__ import annotations

from pathlib import Path
import re

from pydantic import BaseModel, ConfigDict, ValidationError
import yaml

from rag.cleaner import clean_markdown


REQUIRED_METADATA = (
    "document_id",
    "title",
    "document_type",
    "topic",
    "effective_date",
    "version",
    "owner",
    "status",
)
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


class CorpusValidationError(ValueError):
    pass


class CorpusDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    title: str
    document_type: str
    topic: str
    effective_date: str
    version: str
    owner: str
    status: str
    source_path: str
    content: str


def _load_document(path: Path, corpus_root: Path) -> CorpusDocument:
    match = FRONT_MATTER.match(path.read_text(encoding="utf-8"))
    if match is None:
        raise CorpusValidationError(f"Missing YAML front matter: {path}")
    metadata = yaml.safe_load(match.group(1))
    if not isinstance(metadata, dict):
        raise CorpusValidationError(f"Invalid YAML front matter: {path}")
    missing = [key for key in REQUIRED_METADATA if metadata.get(key) in (None, "")]
    if missing:
        raise CorpusValidationError(f"Missing metadata {missing}: {path}")
    if metadata["document_type"] not in {"policy", "procedure"}:
        raise CorpusValidationError(f"Invalid document_type in {path}")
    if metadata["status"] != "approved":
        raise CorpusValidationError(f"Only approved documents may be indexed: {path}")
    try:
        return CorpusDocument(
            **{key: str(metadata[key]) for key in REQUIRED_METADATA},
            source_path=path.relative_to(corpus_root).as_posix(),
            content=clean_markdown(match.group(2)),
        )
    except ValidationError as exc:
        raise CorpusValidationError(f"Invalid metadata in {path}: {exc}") from exc


def load_approved_corpus(corpus_root: Path) -> list[CorpusDocument]:
    """Load only canonical policy and procedure Markdown documents."""

    if not corpus_root.is_dir():
        raise CorpusValidationError(f"Knowledge corpus directory not found: {corpus_root}")
    paths = sorted((corpus_root / "policies").glob("*.md")) + sorted(
        (corpus_root / "procedures").glob("*.md")
    )
    if not paths:
        raise CorpusValidationError(f"No approved corpus documents found: {corpus_root}")
    documents = [_load_document(path, corpus_root) for path in paths]
    identifiers = [document.document_id for document in documents]
    if len(identifiers) != len(set(identifiers)):
        raise CorpusValidationError("Canonical corpus document IDs must be unique")
    return documents

