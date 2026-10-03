"""Provider-neutral LLM boundary with an optional OpenAI-compatible HTTP adapter."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import httpx

from app.config import get_settings


class LLMProviderError(RuntimeError):
    pass


class LLMProvider(Protocol):
    async def generate(self, *, system_prompt: str, user_prompt: str) -> str: ...


class OpenAICompatibleProvider:
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderError("Configured LLM provider is unavailable") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("Configured LLM returned no structured content")
        return content


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider | None:
    settings = get_settings()
    if not settings.llm_api_key or not settings.llm_model or not settings.llm_base_url:
        return None
    return OpenAICompatibleProvider(
        settings.llm_api_key, settings.llm_model, settings.llm_base_url
    )
