"""Typed registration boundary for confirmation-gated mock actions."""

from typing import Protocol


class ActionToolRegistrar(Protocol):
    def register(self, server: object) -> None: ...

