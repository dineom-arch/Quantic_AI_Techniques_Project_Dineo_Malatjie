"""Typed registration boundary for controlled expense tools."""

from typing import Protocol


class ExpenseToolRegistrar(Protocol):
    def register(self, server: object) -> None: ...

