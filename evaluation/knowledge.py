"""Evaluation-only top-k and reversible document suppression wrapper."""

from __future__ import annotations

from collections.abc import Iterable
from threading import RLock

from rag.service import KnowledgeService


VALID_TOP_K = {3, 5, 8}


class EvaluationKnowledgeService:
    def __init__(self, base: KnowledgeService, top_k: int) -> None:
        if top_k not in VALID_TOP_K:
            raise ValueError("Evaluation top-k must be one of 3, 5, or 8")
        self.base = base
        self.top_k = top_k
        self._excluded_document_ids: set[str] = set()
        self._lock = RLock()

    @property
    def is_ready(self) -> bool:
        return self.base.is_ready

    @property
    def error(self) -> str | None:
        return self.base.error

    def set_excluded_documents(self, document_ids: Iterable[str]) -> None:
        with self._lock:
            self._excluded_document_ids = set(document_ids)

    def search(self, query: str, **kwargs):
        kwargs["top_k"] = self.top_k
        results = self.base.search(query, **kwargs)
        with self._lock:
            excluded = set(self._excluded_document_ids)
        return [result for result in results if result.document_id not in excluded]
