from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import numpy as np
import pytest

from app.main import create_app
from rag.index import INDEX_FILENAME
from rag.loaders import CorpusValidationError, load_approved_corpus
from rag.service import KnowledgeService, set_knowledge_service


class TinyEmbeddings:
    model_name = "tiny-test-embeddings"

    def validate(self) -> None:
        return None

    def embed(self, texts):
        vectors = np.zeros((len(texts), 8), dtype="float32")
        for index, text in enumerate(texts):
            vectors[index, index % 8] = 1.0
            vectors[index, (len(text) + index) % 8] += 0.5
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.where(norms == 0, 1, norms)


class FailingEmbeddings(TinyEmbeddings):
    def validate(self) -> None:
        raise RuntimeError("controlled embedding initialization failure")


def _corpus(root: Path) -> Path:
    (root / "policies").mkdir(parents=True)
    (root / "procedures").mkdir(parents=True)
    return root


def _document(
    root: Path,
    *,
    filename: str = "test.md",
    document_id: str = "TEST-POL-001",
    document_type: str = "policy",
    status: str = "approved",
    version: str = "1.0",
    body: str = "Employees must follow the controlled test rule.",
) -> Path:
    directory = "policies" if document_type == "policy" else "procedures"
    path = root / directory / filename
    path.write_text(
        "\n".join(
            [
                "---",
                f"document_id: {document_id}",
                "title: Controlled Test Document",
                f"document_type: {document_type}",
                "topic: test",
                "effective_date: 2026-01-01",
                f'version: "{version}"',
                "owner: Test Owner",
                f"status: {status}",
                "---",
                "",
                "# Controlled Test Document",
                "",
                "## Rule",
                "",
                body,
            ]
        ),
        encoding="utf-8",
    )
    return path


def _built_service(tmp_path: Path) -> tuple[KnowledgeService, Path, Path]:
    corpus = _corpus(tmp_path / "knowledge")
    _document(corpus)
    _document(
        corpus,
        filename="procedure.md",
        document_id="TEST-PROC-001",
        document_type="procedure",
        body="Follow the controlled procedure steps.",
    )
    index_path = tmp_path / "index"
    service = KnowledgeService(corpus, index_path, embeddings=TinyEmbeddings())
    service.build()
    return service, corpus, index_path


def test_ingestion_excludes_files_outside_canonical_directories(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path / "knowledge")
    _document(corpus)
    for directory in ("project_docs", "evaluation", "mock_data"):
        outside = tmp_path / directory
        outside.mkdir()
        _document(_corpus(outside / "nested"), filename=f"{directory}.md", document_id=f"OUT-{directory}")

    documents = load_approved_corpus(corpus)
    assert [document.document_id for document in documents] == ["TEST-POL-001"]


def test_non_approved_document_is_rejected(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path / "knowledge")
    _document(corpus, status="draft")
    with pytest.raises(CorpusValidationError, match="Only approved"):
        load_approved_corpus(corpus)


def test_duplicate_document_id_is_rejected(tmp_path: Path) -> None:
    corpus = _corpus(tmp_path / "knowledge")
    _document(corpus, filename="first.md")
    _document(corpus, filename="second.md")
    with pytest.raises(CorpusValidationError, match="unique"):
        load_approved_corpus(corpus)


def test_corrupt_index_refuses_readiness_and_health(tmp_path: Path) -> None:
    _, corpus, index_path = _built_service(tmp_path)
    (index_path / INDEX_FILENAME).write_bytes(b"not a faiss index")
    service = KnowledgeService(corpus, index_path, embeddings=TinyEmbeddings())
    assert service.load() is False
    assert service.is_ready is False

    set_knowledge_service(service)
    try:
        with TestClient(create_app()) as client:
            response = client.get("/health")
    finally:
        set_knowledge_service(None)
    assert response.json()["status"] == "degraded"
    assert response.json()["rag"] == "not_ready"


def test_embedding_initialization_failure_refuses_readiness(tmp_path: Path) -> None:
    _, corpus, index_path = _built_service(tmp_path)
    service = KnowledgeService(corpus, index_path, embeddings=FailingEmbeddings())
    assert service.load() is False
    assert service.is_ready is False


@pytest.mark.parametrize("change", ["content", "added", "removed", "metadata"])
def test_stale_index_is_rejected_for_authoritative_corpus_changes(
    tmp_path: Path, change: str
) -> None:
    _, corpus, index_path = _built_service(tmp_path)
    original = corpus / "policies" / "test.md"
    if change == "content":
        text = original.read_text(encoding="utf-8")
        original.write_text(text.replace("controlled test rule", "changed controlled rule"), encoding="utf-8")
    elif change == "added":
        _document(corpus, filename="added.md", document_id="TEST-POL-002")
    elif change == "removed":
        original.unlink()
    else:
        text = original.read_text(encoding="utf-8")
        original.write_text(text.replace('version: "1.0"', 'version: "1.1"'), encoding="utf-8")

    service = KnowledgeService(corpus, index_path, embeddings=TinyEmbeddings())
    assert service.load() is False
    assert service.is_ready is False
    assert service.error is not None and "stale" in service.error
