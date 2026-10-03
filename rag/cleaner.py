"""Corpus-cleaning interface."""

from typing import Protocol


class TextCleaner(Protocol):
    def clean(self, text: str) -> str: ...

