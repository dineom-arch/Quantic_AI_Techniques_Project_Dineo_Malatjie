"""Claim/evidence bookkeeping interfaces."""

from typing import Literal

from pydantic import BaseModel


class GroundingResult(BaseModel):
    status: Literal["supported", "partially_supported", "insufficient_evidence", "conflicting_evidence"]
    supported_claims: int = 0
    unsupported_claims: int = 0

