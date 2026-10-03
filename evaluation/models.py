"""Validated controlled cases and auditable evaluation result models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="allow")

    case_id: str
    title: str
    authenticated_user: str
    prompt: str
    category: str
    expected_tools: list[str]
    expected_evidence: list[str]
    gold_behavior: str
    expected_status: str
    must_not: list[str]
    metrics: list[str]
    forbidden_answer_terms: list[str] = Field(default_factory=list)
    required_answer_terms: list[str] = Field(default_factory=list)
    evaluation_as_of: str | None = None
    session_dependency: str | None = None


class DimensionResult(BaseModel):
    passed: bool
    notes: str


class CaseResult(BaseModel):
    case_id: str
    title: str
    category: str
    run_id: str
    expected_outcome: str
    expected_public_statuses: list[str]
    actual_status: str
    passed: bool
    expected_tools: list[str]
    observed_tools: list[str]
    retrieved_document_ids: list[str]
    dimensions: dict[str, DimensionResult]
    latency_ms: float = Field(ge=0)
    failure_reasons: list[str] = Field(default_factory=list)
    answer_excerpt: str = ""


class AggregateMetrics(BaseModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_percentage: float
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    quality_percentages: dict[str, float]
    by_category: dict[str, dict[str, float | int]]


class EvaluationReport(BaseModel):
    schema_version: str = "1.0"
    evaluation_mode: str
    dataset_version: str = "v1.2"
    run_id: str
    top_k: int
    deterministic_offline: bool = True
    results: list[CaseResult]
    aggregate: AggregateMetrics

