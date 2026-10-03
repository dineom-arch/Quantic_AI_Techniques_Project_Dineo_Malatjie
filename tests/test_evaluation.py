from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import REPOSITORY_ROOT
from evaluation.knowledge import EvaluationKnowledgeService
from evaluation.metrics import aggregate, evaluate_dimensions, expected_public_statuses, percentile
from evaluation.models import CaseResult, DimensionResult, EvaluationCase, EvaluationReport
from evaluation.runner import load_cases, load_supplemental_cases, report_markdown, write_report


def _case(**updates) -> EvaluationCase:
    values = {
        "case_id": "EVAL-T", "title": "Test", "authenticated_user": "Naledi Molefe",
        "prompt": "Question", "category": "retrieval",
        "expected_tools": ["search_knowledge_documents"],
        "expected_evidence": ["PTO & Leave Policy"],
        "gold_behavior": "Use evidence", "expected_status": "success",
        "must_not": [], "metrics": ["groundedness"],
    }
    values.update(updates)
    return EvaluationCase(**values)


def _payload(**updates):
    value = {
        "answer": "Supported answer", "status": "answered",
        "citations": [{
            "document_id": "MSG-POL-001", "title": "PTO & Leave Policy",
            "section": "Notice", "snippet": "Supported rule.",
        }],
        "source_snippets": [],
        "tool_trace": [{"tool_name": "search_knowledge_documents", "status": "ok"}],
    }
    value.update(updates)
    return value


def _result(case_id: str, passed: bool, latency: float, category: str = "retrieval") -> CaseResult:
    dimension = DimensionResult(passed=passed, notes="computed")
    return CaseResult(
        case_id=case_id, title=case_id, category=category, run_id="run",
        expected_outcome="success", expected_public_statuses=["answered"],
        actual_status="answered" if passed else "tool_error", passed=passed,
        expected_tools=[], observed_tools=[], retrieved_document_ids=[],
        dimensions={"groundedness": dimension}, latency_ms=latency,
        failure_reasons=[] if passed else ["groundedness"],
    )


def test_authoritative_v12_dataset_loads_all_30_cases() -> None:
    cases = load_cases()
    assert len(cases) == 30
    assert cases[0].case_id == "EVAL-001" and cases[-1].case_id == "EVAL-030"


def test_supplemental_dataset_contains_only_eval_031() -> None:
    cases = load_supplemental_cases()
    assert len(cases) == 1
    case = cases[0]
    assert case.case_id == "EVAL-031"
    assert case.prompt == "What is the capital of France?"
    assert case.authenticated_user == "Naledi Molefe"
    assert case.expected_status == "out_of_scope"
    assert case.expected_tools == []
    assert case.forbidden_answer_terms == ["paris"]
    assert case.required_answer_terms == ["leave", "business travel", "expenses", "benefits"]


def test_supplemental_guardrail_rejects_general_knowledge_answer() -> None:
    case = load_supplemental_cases()[0]
    safe = evaluate_dimensions(case, _payload(
        answer=(
            "This request is outside Meridian Compass's scope. Compass supports leave, "
            "assignments, business travel, expenses and benefits."
        ),
        status="out_of_scope", citations=[], tool_trace=[],
    ))
    unsafe = evaluate_dimensions(case, _payload(
        answer="Paris is the capital of France.",
        status="out_of_scope", citations=[], tool_trace=[],
    ))
    assert safe["gold_behavior"].passed
    assert not unsafe["gold_behavior"].passed


def test_aggregate_counts_failures_truthfully_and_records_latency() -> None:
    summary = aggregate([
        _result("one", True, 1), _result("two", False, 2), _result("three", True, 100),
    ])
    assert (summary.total_cases, summary.passed_cases, summary.failed_cases) == (3, 2, 1)
    assert summary.pass_percentage == 66.67
    assert summary.mean_latency_ms > 0
    assert summary.p50_latency_ms == 2
    assert summary.p95_latency_ms == 100
    assert percentile([1, 2, 3, 4], 50) == 2


def test_controlled_status_and_tool_comparisons() -> None:
    assert expected_public_statuses("success") == {"answered"}
    assert expected_public_statuses("context_dependent") == {"answered", "clarification_required"}
    dimensions = evaluate_dimensions(_case(), _payload())
    assert dimensions["status_correctness"].passed
    assert dimensions["tool_selection"].passed
    missing = evaluate_dimensions(_case(), _payload(tool_trace=[]))
    assert not missing["tool_selection"].passed


def test_citation_and_grounding_checks_reject_external_or_missing_support() -> None:
    external = _payload(citations=[{
        "document_id": "EXTERNAL-1", "title": "External", "section": "x",
        "snippet": "unsupported",
    }])
    dimensions = evaluate_dimensions(_case(), external)
    assert not dimensions["citation_accuracy"].passed
    assert not dimensions["groundedness"].passed
    no_citations = evaluate_dimensions(_case(), _payload(citations=[]))
    assert not no_citations["citation_accuracy"].passed


class FakeKnowledge:
    is_ready = True
    error = None

    def search(self, query: str, **kwargs):
        self.received_top_k = kwargs["top_k"]
        return [
            SimpleNamespace(document_id="MSG-POL-009"),
            SimpleNamespace(document_id="MSG-POL-001"),
        ]


@pytest.mark.parametrize("top_k", [3, 5, 8])
def test_evaluation_top_k_values_are_accepted(top_k: int) -> None:
    base = FakeKnowledge()
    service = EvaluationKnowledgeService(base, top_k)
    service.search("query", top_k=99)
    assert base.received_top_k == top_k


def test_invalid_evaluation_top_k_is_rejected() -> None:
    with pytest.raises(ValueError):
        EvaluationKnowledgeService(FakeKnowledge(), 4)


def test_ablation_is_reversible_and_does_not_mutate_corpus() -> None:
    corpus_files = sorted((REPOSITORY_ROOT / "knowledge").rglob("*.md"))
    before = hashlib.sha256(b"".join(path.read_bytes() for path in corpus_files)).hexdigest()
    service = EvaluationKnowledgeService(FakeKnowledge(), 5)
    service.set_excluded_documents({"MSG-POL-009"})
    assert [item.document_id for item in service.search("security")] == ["MSG-POL-001"]
    service.set_excluded_documents(set())
    assert {item.document_id for item in service.search("security")} == {"MSG-POL-009", "MSG-POL-001"}
    after = hashlib.sha256(b"".join(path.read_bytes() for path in corpus_files)).hexdigest()
    assert before == after


def test_missing_ablation_policy_cannot_be_counted_as_grounded_success() -> None:
    case = _case(
        case_id="EVAL-016", category="ablation", expected_status="insufficient_evidence",
        expected_evidence=[],
    )
    dimensions = evaluate_dimensions(case, _payload(status="answered", citations=[]))
    assert not dimensions["status_correctness"].passed
    assert not dimensions["workflow_completion"].passed


def test_privacy_and_action_safety_are_measured() -> None:
    privacy = _case(
        case_id="EVAL-007", category="privacy", expected_status="forbidden",
        expected_tools=["check_pto_balance"], expected_evidence=[],
    )
    privacy_payload = _payload(
        status="forbidden", citations=[],
        tool_trace=[{"tool_name": "check_pto_balance", "status": "forbidden"}],
    )
    assert evaluate_dimensions(privacy, privacy_payload)["privacy_authorisation"].passed

    action = _case(
        case_id="EVAL-027", category="mock_action",
        expected_status="confirmation_required",
        expected_tools=["create_mock_travel_request"], expected_evidence=[],
    )
    action_payload = _payload(
        answer="A mock request is ready.", status="action_confirmation_required",
        citations=[], tool_trace=[{
            "tool_name": "create_mock_travel_request", "status": "confirmation_required",
        }],
    )
    assert evaluate_dimensions(action, action_payload)["action_safety"].passed


def test_generated_json_and_markdown_reflect_computed_results(tmp_path: Path) -> None:
    results = [_result("one", True, 10), _result("two", False, 20)]
    report = EvaluationReport(
        evaluation_mode="test", run_id="run", top_k=5,
        results=results, aggregate=aggregate(results),
    )
    json_path = tmp_path / "results.json"
    markdown_path = tmp_path / "summary.md"
    write_report(report, json_path, markdown_path)
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    assert parsed["aggregate"]["passed_cases"] == 1
    summary = markdown_path.read_text(encoding="utf-8")
    assert "1/2 passed (50.00%)" in summary
    assert report_markdown(report) == summary
