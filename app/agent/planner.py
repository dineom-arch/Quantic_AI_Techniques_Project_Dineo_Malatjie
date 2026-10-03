"""Planning interface; substantive intent logic is deferred."""

from typing import Protocol

from app.agent.context import AgentContext


class Planner(Protocol):
    async def plan(self, context: AgentContext) -> object: ...

