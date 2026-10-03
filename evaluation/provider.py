"""Deterministic evidence-bound synthesis provider for reproducible offline evaluation."""

from __future__ import annotations

import json
from app.agent.extractive import build_extractive_draft


class DeterministicEvaluationProvider:
    """Produces extractive claims only from the evidence included in its request."""

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        return json.dumps(build_extractive_draft(json.loads(user_prompt)))

