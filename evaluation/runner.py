"""Sequential, reproducible evaluation runner over the public application path."""

from __future__ import annotations

from datetime import date, datetime, UTC
import json
import os
from pathlib import Path
from types import SimpleNamespace
from time import perf_counter
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.actions.store import get_mock_action_store
from app.agent.context import AgentContext
from app.config import REPOSITORY_ROOT
from app.identity.runtime import identity_provider, session_store
from app.integrations.mcp_runtime import meridian_mcp_client_class
from app.main import create_app
from evaluation.knowledge import EvaluationKnowledgeService, VALID_TOP_K
from evaluation.metrics import aggregate, evaluate_dimensions, expected_public_statuses
from evaluation.models import CaseResult, EvaluationCase, EvaluationReport
from evaluation.provider import DeterministicEvaluationProvider
from rag.service import KnowledgeService, set_knowledge_service


DATASET_PATH = REPOSITORY_ROOT / "project_docs" / "evaluation" / "02_evaluation_dataset_v1_2.json"
DEFAULT_RESULTS_DIRECTORY = REPOSITORY_ROOT / "evaluation" / "results"


def load_cases(path: Path = DATASET_PATH) -> list[EvaluationCase]:
    cases = TypeAdapter(list[EvaluationCase]).validate_json(path.read_text(encoding="utf-8"))
    if len(cases) != 30:
        raise ValueError(f"Authoritative v1.2 evaluation dataset must contain 30 cases, found {len(cases)}")
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("Evaluation case IDs must be unique")
    return cases


def _username_for(display_name: str) -> str:
    match = next(
        (item for item in identity_provider.list_active_options() if item.display_name == display_name),
        None,
    )
    if match is None:
        raise ValueError(f"No controlled identity for {display_name}")
    return match.corporate_username


class _FailingMCPClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        raise RuntimeError("simulated evaluation dependency outage")


def _missing_booking_client_class(real_class):
    class MissingBookingClient:
        def __init__(self, *args, **kwargs) -> None:
            self.delegate = real_class(*args, **kwargs)

        async def call_tool(self, name: str, arguments: dict[str, Any]):
            if name == "get_mock_travel_booking":
                return SimpleNamespace(
                    structuredContent={
                        "status": "not_found", "message": "Travel booking not found",
                    },
                    content=[],
                )
            return await self.delegate.call_tool(name, arguments)

    return MissingBookingClient


class EvaluationRunner:
    def __init__(self, cases: list[EvaluationCase] | None = None) -> None:
        self.cases = cases or load_cases()
        # The model and index must already exist locally. These flags prevent
        # model-library metadata checks or downloads during evaluation.
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        self.base_knowledge = KnowledgeService(
            REPOSITORY_ROOT / "knowledge", REPOSITORY_ROOT / "runtime_data" / "rag_index",
        )
        if not self.base_knowledge.load():
            raise RuntimeError(f"Existing RAG index could not be loaded: {self.base_knowledge.error}")
        self.real_mcp_client_class = meridian_mcp_client_class()

    def run(
        self,
        *,
        top_k: int = 5,
        mode: str = "baseline",
        selected_case_ids: set[str] | None = None,
        force_ablation: bool = False,
    ) -> EvaluationReport:
        if top_k not in VALID_TOP_K:
            raise ValueError("Evaluation top-k must be one of 3, 5, or 8")
        run_id = f"{mode}-k{top_k}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
        knowledge = EvaluationKnowledgeService(self.base_knowledge, top_k)
        session_store.reset()
        get_mock_action_store().reset()
        set_knowledge_service(knowledge)
        results: list[CaseResult] = []
        dependent_session: str | None = None
        try:
            with TestClient(create_app(llm_provider=DeterministicEvaluationProvider())) as client:
                for case in self.cases:
                    if selected_case_ids and case.case_id not in selected_case_ids:
                        continue
                    excluded = {"MSG-POL-009"} if force_ablation or case.case_id == "EVAL-016" else set()
                    knowledge.set_excluded_documents(excluded)
                    if case.case_id == "EVAL-028" and dependent_session:
                        session_id = dependent_session
                    else:
                        session_id = client.post("/auth/session", json={
                            "corporate_username": _username_for(case.authenticated_user),
                        }).json()["session_id"]
                    if case.case_id == "EVAL-027":
                        dependent_session = session_id
                    results.append(self._run_case(client, case, session_id, run_id))
        finally:
            knowledge.set_excluded_documents(set())
            set_knowledge_service(None)
            session_store.reset()
            get_mock_action_store().reset()
        return EvaluationReport(
            evaluation_mode=mode, run_id=run_id, top_k=top_k,
            results=results, aggregate=aggregate(results),
        )

    def _run_case(
        self, client: TestClient, case: EvaluationCase, session_id: str, run_id: str,
    ) -> CaseResult:
        patches = []
        if case.case_id == "EVAL-029":
            patches.append(patch(
                "app.api.chat.meridian_mcp_client_class",
                return_value=_missing_booking_client_class(self.real_mcp_client_class),
            ))
        elif case.case_id == "EVAL-030":
            patches.append(patch(
                "app.api.chat.meridian_mcp_client_class", return_value=_FailingMCPClient,
            ))
        if case.evaluation_as_of:
            controlled_date = date.fromisoformat(case.evaluation_as_of)

            def controlled_context(**kwargs):
                return AgentContext(**kwargs, as_of=controlled_date)

            patches.append(patch("app.api.chat.AgentContext", side_effect=controlled_context))
        for active_patch in patches:
            active_patch.start()
        started = perf_counter()
        try:
            response = client.post("/chat", json={
                "session_id": session_id, "message": case.prompt,
            })
            payload = response.json()
        except Exception as exc:
            payload = {
                "answer": "Evaluation request failed safely.", "status": "tool_error",
                "citations": [], "source_snippets": [], "tool_trace": [],
                "evaluation_error": type(exc).__name__,
            }
        finally:
            latency_ms = round((perf_counter() - started) * 1000, 3)
            for active_patch in reversed(patches):
                active_patch.stop()

        dimensions = evaluate_dimensions(case, payload)
        failures = [name for name, result in dimensions.items() if not result.passed]
        observed_tools = [
            str(item["tool_name"]) for item in payload.get("tool_trace", []) if item.get("tool_name")
        ]
        document_ids = sorted({
            str(item["document_id"]) for item in payload.get("citations", []) if item.get("document_id")
        })
        return CaseResult(
            case_id=case.case_id, title=case.title, category=case.category,
            run_id=run_id, expected_outcome=case.expected_status,
            expected_public_statuses=sorted(expected_public_statuses(case.expected_status)),
            actual_status=str(payload.get("status", "error")), passed=not failures,
            expected_tools=case.expected_tools, observed_tools=observed_tools,
            retrieved_document_ids=document_ids, dimensions=dimensions,
            latency_ms=latency_ms, failure_reasons=failures,
            answer_excerpt=str(payload.get("answer", ""))[:300],
        )


def report_markdown(report: EvaluationReport) -> str:
    aggregate_result = report.aggregate
    lines = [
        f"# Meridian Compass Evaluation — {report.evaluation_mode}", "",
        f"Run: `{report.run_id}`", "",
        f"Top-k: **{report.top_k}**", "",
        f"Cases: **{aggregate_result.passed_cases}/{aggregate_result.total_cases} passed "
        f"({aggregate_result.pass_percentage:.2f}%)**", "",
        "## Quality dimensions", "",
        "| Dimension | Pass rate |", "|---|---:|",
    ]
    lines.extend(
        f"| {name.replace('_', ' ').title()} | {value:.2f}% |"
        for name, value in aggregate_result.quality_percentages.items()
    )
    lines.extend([
        "", "## Latency", "",
        f"Mean: {aggregate_result.mean_latency_ms:.3f} ms  ",
        f"p50: {aggregate_result.p50_latency_ms:.3f} ms  ",
        f"p95: {aggregate_result.p95_latency_ms:.3f} ms  ",
        f"Min/max: {aggregate_result.min_latency_ms:.3f}/{aggregate_result.max_latency_ms:.3f} ms",
        "", "These are deterministic local evaluation measurements, not production SLA claims.",
        "", "## Case results", "",
        "| Case | Category | Expected | Actual | Result | Latency ms | Failures |",
        "|---|---|---|---|---:|---:|---|",
    ])
    for result in report.results:
        lines.append(
            f"| {result.case_id} | {result.category} | {result.expected_outcome} | "
            f"{result.actual_status} | {'PASS' if result.passed else 'FAIL'} | "
            f"{result.latency_ms:.3f} | {', '.join(result.failure_reasons) or '—'} |"
        )
    return "\n".join(lines) + "\n"


def write_report(report: EvaluationReport, json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(report_markdown(report), encoding="utf-8")
