"""Retriever interfaces with the controlled baseline top-k."""

from typing import Protocol


BASELINE_TOP_K = 5


class Retriever(Protocol):
    def search(self, query: str, *, top_k: int = BASELINE_TOP_K) -> list[object]: ...

