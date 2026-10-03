"""Guardrail result models; business-rule enforcement is deferred."""

from pydantic import BaseModel


class GuardrailResult(BaseModel):
    allowed: bool
    reason: str | None = None

