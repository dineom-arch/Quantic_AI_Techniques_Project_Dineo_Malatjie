"""Typed registration boundary for controlled employee tools."""

from typing import Protocol


class EmployeeToolRegistrar(Protocol):
    def register(self, server: object) -> None: ...

