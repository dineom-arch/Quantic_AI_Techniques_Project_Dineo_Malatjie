"""Embedding provider interface; model loading is deferred."""

from typing import Protocol, Sequence


class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...

