"""Vector-index interface; FAISS creation is deferred."""

from typing import Protocol


class VectorIndex(Protocol):
    def add(self, vectors: list[list[float]], records: list[object]) -> None: ...

