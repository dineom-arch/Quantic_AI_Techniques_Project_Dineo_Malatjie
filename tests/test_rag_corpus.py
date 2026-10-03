from pathlib import Path

import pytest

from app.config import REPOSITORY_ROOT
from rag.chunker import MAX_CHARS, chunk_documents
from rag.loaders import CorpusDocument, CorpusValidationError, load_approved_corpus


def test_all_approved_corpus_documents_load_with_metadata() -> None:
    documents = load_approved_corpus(REPOSITORY_ROOT / "knowledge")

    assert len(documents) == 19
    assert sum(document.document_type == "policy" for document in documents) == 12
    assert sum(document.document_type == "procedure" for document in documents) == 7
    assert all(document.status == "approved" for document in documents)
    assert all(
        document.document_id
        and document.title
        and document.topic
        and document.effective_date
        and document.version
        and document.owner
        for document in documents
    )
    assert all(document.source_path.startswith(("policies/", "procedures/")) for document in documents)


def test_missing_corpus_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(CorpusValidationError, match="not found"):
        load_approved_corpus(tmp_path / "missing")


def test_malformed_metadata_fails_clearly(tmp_path: Path) -> None:
    policies = tmp_path / "policies"
    procedures = tmp_path / "procedures"
    policies.mkdir()
    procedures.mkdir()
    (policies / "bad.md").write_text("---\ndocument_id: BAD\n---\n# Bad", encoding="utf-8")
    with pytest.raises(CorpusValidationError, match="Missing metadata"):
        load_approved_corpus(tmp_path)


def test_chunking_is_deterministic_and_preserves_metadata() -> None:
    documents = load_approved_corpus(REPOSITORY_ROOT / "knowledge")
    first = chunk_documents(documents)
    second = chunk_documents(documents)

    assert first == second
    assert len(first) > len(documents)
    assert len({chunk.chunk_id for chunk in first}) == len(first)
    assert all(chunk.document_id and chunk.section and chunk.source_path for chunk in first)
    assert all(chunk.status == "approved" for chunk in first)


def test_oversized_paragraph_is_bounded_preserved_and_deterministic() -> None:
    paragraph = ("authoritative wording " * 130).strip()
    document = CorpusDocument(
        document_id="TEST-POL-001",
        title="Test Policy",
        document_type="policy",
        topic="test",
        effective_date="2026-01-01",
        version="1.0",
        owner="Test Owner",
        status="approved",
        source_path="policies/test.md",
        content=f"# Test Policy\n\n## Long Rule\n\n{paragraph}",
    )

    first = chunk_documents([document])
    second = chunk_documents([document])

    assert first == second
    assert all(len(chunk.text) <= MAX_CHARS for chunk in first)
    assert "".join(chunk.text for chunk in first) == paragraph

