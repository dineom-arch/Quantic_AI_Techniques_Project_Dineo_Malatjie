"""Orchestrator interface; Phase-2 implementation is intentionally deferred."""

from typing import Protocol

from app.agent.context import AgentContext


class Orchestrator(Protocol):
    async def run(self, context: AgentContext) -> object: ...

