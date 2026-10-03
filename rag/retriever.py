"""Semantic top-k retrieval over authoritative FAISS-backed chunks."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from rag.chunker import DocumentChunk


BASELINE_TOP_K = 5
VALID_DOCUMENT_TYPES = {"policy", "procedure", "all"}


class RetrievalValidationError(ValueError):
    pass


class RetrievalResult(BaseModel):
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
    score: float


class FaissRetriever:
    def __init__(self, index, chunks: list[DocumentChunk], embeddings) -> None:
        self.index = index
        self.chunks = chunks
        self.embeddings = embeddings

    def search(
        self,
        query: str,
        *,
        top_k: int = BASELINE_TOP_K,
        document_type: str = "all",
        topic: str | None = None,
    ) -> list[RetrievalResult]:
        query = query.strip()
        if not query:
            raise RetrievalValidationError("query must not be empty")
        if document_type not in VALID_DOCUMENT_TYPES:
            raise RetrievalValidationError("document_type must be policy, procedure, or all")
        if top_k < 1:
            raise RetrievalValidationError("top_k must be at least 1")

        candidates = [
            index
            for index, chunk in enumerate(self.chunks)
            if (document_type == "all" or chunk.document_type == document_type)
            and (topic is None or chunk.topic == topic)
        ]
        if not candidates:
            return []

        query_vector = self.embeddings.embed([query])
        search_k = len(self.chunks)
        scores, indices = self.index.search(query_vector, search_k)
        allowed = set(candidates)
        results: list[RetrievalResult] = []
        for score, chunk_index in zip(scores[0], indices[0], strict=True):
            if int(chunk_index) < 0 or int(chunk_index) not in allowed:
                continue
            chunk = self.chunks[int(chunk_index)]
            results.append(RetrievalResult(**chunk.model_dump(), score=float(score)))
            if len(results) == min(top_k, len(candidates)):
                break
        return results

