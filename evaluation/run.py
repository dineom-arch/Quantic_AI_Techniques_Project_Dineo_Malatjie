"""CLI for baseline, top-k, and grounding-ablation evaluation."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from evaluation.runner import DEFAULT_RESULTS_DIRECTORY, EvaluationRunner, write_report


def _comparison_markdown(reports) -> str:
    lines = [
        "# Top-k Comparison", "",
        "| k | Passed | Total | Pass rate | Groundedness | Citation accuracy | Tool selection | Mean ms | p50 ms | p95 ms |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for report in reports:
        summary = report.aggregate
        quality = summary.quality_percentages
        lines.append(
            f"| {report.top_k} | {summary.passed_cases} | {summary.total_cases} | "
            f"{summary.pass_percentage:.2f}% | {quality.get('groundedness', 0):.2f}% | "
            f"{quality.get('citation_accuracy', 0):.2f}% | {quality.get('tool_selection', 0):.2f}% | "
            f"{summary.mean_latency_ms:.3f} | {summary.p50_latency_ms:.3f} | {summary.p95_latency_ms:.3f} |"
        )
    lines.extend(["", "Local deterministic evaluation latency; not a production SLA.", ""])
    return "\n".join(lines)


def _ablation_markdown(baseline, ablated) -> str:
    before = baseline.results[0]
    after = ablated.results[0]
    return "\n".join([
        "# Knowledge-removal Ablation", "",
        "Selected case: **EVAL-016 — Security ablation**", "",
        "The ablation suppresses `MSG-POL-009` in the evaluation-only retrieval wrapper. "
        "No corpus file or production default is changed.", "",
        "| Mode | Actual status | Groundedness | Citations | Overall result |",
        "|---|---|---:|---:|---:|",
        f"| Policy available | {before.actual_status} | "
        f"{'PASS' if before.dimensions['groundedness'].passed else 'FAIL'} | "
        f"{'PASS' if before.dimensions['citation_accuracy'].passed else 'FAIL'} | "
        f"{'PASS' if before.passed else 'FAIL'} |",
        f"| Policy suppressed | {after.actual_status} | "
        f"{'PASS' if after.dimensions['groundedness'].passed else 'FAIL'} | "
        f"{'PASS' if after.dimensions['citation_accuracy'].passed else 'FAIL'} | "
        f"{'PASS' if after.passed else 'FAIL'} |",
        "", "The expected safety behavior is an insufficient-evidence response after suppression.", "",
    ])


def execute(mode: str, output_dir: Path) -> dict[str, object]:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("mcp").setLevel(logging.WARNING)
    runner = EvaluationRunner()
    output_dir.mkdir(parents=True, exist_ok=True)
    completed: dict[str, object] = {}
    baseline = None
    if mode in {"all", "baseline"}:
        baseline = runner.run(top_k=5, mode="baseline")
        write_report(
            baseline, output_dir / "evaluation_results.json",
            output_dir / "evaluation_summary.md",
        )
        completed["baseline"] = baseline.aggregate.model_dump()
        print(
            f"Baseline: {baseline.aggregate.passed_cases}/{baseline.aggregate.total_cases} "
            f"passed ({baseline.aggregate.pass_percentage:.2f}%)"
        )
    if mode in {"all", "top-k"}:
        reports = [
            runner.run(top_k=3, mode="top-k-3"),
            baseline or runner.run(top_k=5, mode="top-k-5"),
            runner.run(top_k=8, mode="top-k-8"),
        ]
        comparison = {
            "schema_version": "1.0", "deterministic_offline": True,
            "runs": [report.model_dump(mode="json") for report in reports],
        }
        (output_dir / "top_k_comparison.json").write_text(
            json.dumps(comparison, indent=2), encoding="utf-8",
        )
        (output_dir / "top_k_comparison.md").write_text(
            _comparison_markdown(reports), encoding="utf-8",
        )
        completed["top_k"] = [report.aggregate.model_dump() for report in reports]
        print("Top-k comparison complete: k=3, k=5, k=8")
    if mode in {"all", "ablation"}:
        selected = {"EVAL-016"}
        # The controlled EVAL-016 case automatically suppresses its policy. For
        # the control, use the equivalent EVAL-015 prompt with policy available.
        control_case = next(case for case in runner.cases if case.case_id == "EVAL-015")
        before = EvaluationRunner(cases=[control_case]).run(
            top_k=5, mode="ablation-control", selected_case_ids={"EVAL-015"},
        )
        after = runner.run(
            top_k=5, mode="ablation-policy-removed", selected_case_ids=selected,
            force_ablation=True,
        )
        ablation = {
            "schema_version": "1.0", "removed_document_id": "MSG-POL-009",
            "control": before.model_dump(mode="json"),
            "ablated": after.model_dump(mode="json"),
        }
        (output_dir / "ablation_results.json").write_text(
            json.dumps(ablation, indent=2), encoding="utf-8",
        )
        (output_dir / "ablation_summary.md").write_text(
            _ablation_markdown(before, after), encoding="utf-8",
        )
        completed["ablation"] = {
            "control_status": before.results[0].actual_status,
            "ablated_status": after.results[0].actual_status,
        }
        print(
            f"Ablation: {before.results[0].actual_status} -> {after.results[0].actual_status}"
        )
    return completed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Meridian Compass controlled evaluation")
    parser.add_argument(
        "--mode", choices=("all", "baseline", "top-k", "ablation"), default="all",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_RESULTS_DIRECTORY)
    arguments = parser.parse_args()
    execute(arguments.mode, arguments.output_dir)


if __name__ == "__main__":
    main()
