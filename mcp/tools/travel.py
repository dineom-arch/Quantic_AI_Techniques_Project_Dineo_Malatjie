"""Typed registration boundary for controlled travel tools."""

from typing import Protocol


class TravelToolRegistrar(Protocol):
    def register(self, server: object) -> None: ...

