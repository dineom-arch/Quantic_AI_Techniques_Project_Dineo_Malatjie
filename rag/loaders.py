"""Loader interfaces; canonical ingestion is deferred to Phase 2."""

from pathlib import Path
from typing import Protocol


class CorpusLoader(Protocol):
    def load(self, source: Path) -> list[object]: ...

