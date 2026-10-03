"""Typed registration boundary for controlled assignment tools."""

from typing import Protocol


class AssignmentToolRegistrar(Protocol):
    def register(self, server: object) -> None: ...

