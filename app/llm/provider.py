"""Provider-neutral LLM interface; no Phase-1 external calls."""

from typing import Protocol


class LLMProvider(Protocol):
    async def generate(self, *, system_prompt: str, user_prompt: str) -> str: ...

