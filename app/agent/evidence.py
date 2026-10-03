"""Bounded, auditable evidence and orchestration result models."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agent.planner import ExecutionPlan
from app.agent.traces import TraceEvent


EvidenceKind = Literal["identity", "operational", "knowledge"]
OrchestrationStatus = Literal[
    "sufficient_evidence", "insufficient_evidence", "forbidden", "not_found",
    "invalid_request", "confirmation_required", "dependency_unavailable", "out_of_scope",
]


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_type: EvidenceKind
    source: str
    status: str
    request_id: str
    data_domain: str | None = None
    fact: dict[str, Any] | None = None
    document_id: str | None = None
    document_title: str | None = None
    document_type: str | None = None
    section: str | None = None
    snippet: str | None = None


class EvidenceBundle(BaseModel):
    items: list[EvidenceItem] = Field(default_factory=list)
    required_request_ids: list[str] = Field(default_factory=list)
    completed_request_ids: list[str] = Field(default_factory=list)
    missing_request_ids: list[str] = Field(default_factory=list)
    complete: bool = False


class OrchestrationResult(BaseModel):
    status: OrchestrationStatus
    intent: str
    domains: list[str]
    authenticated_display_name: str
    plan: ExecutionPlan
    evidence: EvidenceBundle
    tool_trace: list[TraceEvent]
    message: str
