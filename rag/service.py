"""Lifecycle facade for building, loading, and querying the RAG index."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock

from app.config import get_settings
from rag.chunker import chunk_documents
from rag.embeddings import BASELINE_MODEL, SentenceTransformerEmbeddings
from rag.index import build_faiss_index, corpus_fingerprint, load_index, save_index
from rag.loaders import load_approved_corpus
from rag.retriever import FaissRetriever, RetrievalResult


@dataclass(frozen=True)
class BuildResult:
    document_count: int
    policy_count: int
    procedure_count: int
    chunk_count: int
    index_path: Path


class KnowledgeService:
    def __init__(self, corpus_path: Path, index_path: Path, embeddings=None) -> None:
        self.corpus_path = corpus_path
        self.index_path = index_path
        self.embeddings = embeddings or SentenceTransformerEmbeddings()
        self._retriever: FaissRetriever | None = None
        self._error: str | None = None
        self._lock = RLock()

    @property
    def is_ready(self) -> bool:
        return self._retriever is not None

    @property
    def error(self) -> str | None:
        return self._error

    def build(self) -> BuildResult:
        documents = load_approved_corpus(self.corpus_path)
        chunks = chunk_documents(documents)
        vectors = self.embeddings.embed([chunk.text for chunk in chunks])
        index = build_faiss_index(vectors)
        save_index(
            self.index_path,
            index,
            chunks,
            model_name=getattr(self.embeddings, "model_name", BASELINE_MODEL),
            current_corpus_fingerprint=corpus_fingerprint(documents),
        )
        with self._lock:
            self._retriever = FaissRetriever(index, chunks, self.embeddings)
            self._error = None
        return BuildResult(
            document_count=len(documents),
            policy_count=sum(document.document_type == "policy" for document in documents),
            procedure_count=sum(document.document_type == "procedure" for document in documents),
            chunk_count=len(chunks),
            index_path=self.index_path,
        )

    def load(self) -> bool:
        try:
            current_documents = load_approved_corpus(self.corpus_path)
            index, chunks, manifest = load_index(self.index_path)
            persisted_corpus_fingerprint = manifest.get("corpus_fingerprint")
            if not persisted_corpus_fingerprint:
                raise RuntimeError("Persisted index has no current-corpus fingerprint")
            if persisted_corpus_fingerprint != corpus_fingerprint(current_documents):
                raise RuntimeError("Persisted RAG index is stale for the current approved corpus")
            if manifest.get("model_name") != getattr(self.embeddings, "model_name", BASELINE_MODEL):
                raise RuntimeError("Embedding model does not match persisted index")
            validate = getattr(self.embeddings, "validate", None)
            if validate is not None:
                validate()
            with self._lock:
                self._retriever = FaissRetriever(index, chunks, self.embeddings)
                self._error = None
            return True
        except Exception as exc:
            with self._lock:
                self._retriever = None
                self._error = str(exc)
            return False

    def search(self, query: str, **kwargs) -> list[RetrievalResult]:
        if self._retriever is None:
            raise RuntimeError(self._error or "RAG index is not ready")
        return self._retriever.search(query, **kwargs)


_service: KnowledgeService | None = None
_service_lock = RLock()


def get_knowledge_service() -> KnowledgeService:
    global _service
    with _service_lock:
        if _service is None:
            settings = get_settings()
            _service = KnowledgeService(settings.knowledge_data_path, settings.vector_store_path)
            _service.load()
        return _service


def set_knowledge_service(service: KnowledgeService | None) -> None:
    """Set/reset runtime service for controlled application tests."""

    global _service
    with _service_lock:
        _service = service
