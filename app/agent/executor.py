"""Approved MCP plan execution and evidence normalization."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Protocol

from app.agent.evidence import EvidenceItem
from app.agent.planner import ExecutionPlan, PlannedToolCall
from app.agent.traces import TraceEvent


ALLOWED_ORCHESTRATION_TOOLS = frozenset(
    {
        "search_knowledge_documents", "lookup_employee_profile", "check_pto_balance",
        "lookup_benefits_status", "lookup_active_assignment", "lookup_travel_authorization",
        "get_mock_travel_booking", "get_per_diem_rate", "get_mock_expense_claim",
    }
)

OPERATIONAL_FACT_KEYS: dict[str, str] = {
    "lookup_employee_profile": "profile",
    "check_pto_balance": "pto_balance",
    "lookup_benefits_status": "benefits",
    "lookup_active_assignment": "assignment",
    "lookup_travel_authorization": "travel_authorization",
    "get_mock_travel_booking": "booking",
    "get_per_diem_rate": "per_diem_rate",
    "get_mock_expense_claim": "expense_claim",
}


class MCPClient(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, Any]): ...


class ExecutedCall:
    def __init__(self, request: PlannedToolCall, status: str, evidence: list[EvidenceItem], trace: TraceEvent, satisfies_requirement: bool) -> None:
        self.request = request
        self.status = status
        self.evidence = evidence
        self.trace = trace
        self.satisfies_requirement = satisfies_requirement


def _payload(result: Any) -> dict[str, Any]:
    if result.structuredContent is not None:
        return dict(result.structuredContent)
    if result.content and getattr(result.content[0], "text", None):
        parsed = json.loads(result.content[0].text)
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _safe_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    return {key: "[redacted]" if "employee" in key.casefold() else value for key, value in arguments.items()}


def _summary(call: PlannedToolCall, status: str, payload: dict[str, Any]) -> str:
    if status != "ok":
        return f"{call.domain} evidence returned {status}"
    if call.kind == "knowledge":
        return f"Retrieved {len(payload.get('results', []))} approved knowledge snippets"
    keys = sorted(key for key in payload if key not in {"status", "data_source", "message"})
    return f"Retrieved {call.domain} facts: {', '.join(keys) or 'record'}"


def _has_required_operational_fact(call: PlannedToolCall, payload: dict[str, Any]) -> bool:
    """Validate the contracted record container without rejecting falsey field values."""

    fact_key = OPERATIONAL_FACT_KEYS.get(call.tool_name)
    if fact_key is None or fact_key not in payload:
        return False
    fact = payload[fact_key]
    if isinstance(fact, dict):
        return len(fact) > 0
    if isinstance(fact, list):
        return len(fact) > 0
    return False


class MCPPlanExecutor:
    def __init__(self, client: MCPClient) -> None:
        self.client = client

    async def execute(self, plan: ExecutionPlan) -> list[ExecutedCall]:
        executed: list[ExecutedCall] = []
        for sequence, call in enumerate(plan.calls, start=1):
            started = perf_counter()
            if call.tool_name not in ALLOWED_ORCHESTRATION_TOOLS:
                status, payload = "invalid_request", {}
            else:
                try:
                    payload = _payload(await self.client.call_tool(call.tool_name, call.arguments))
                    status = str(payload.get("status", "dependency_unavailable"))
                except Exception:
                    status, payload = "dependency_unavailable", {}
            evidence = self._evidence(call, status, payload)
            if call.kind == "knowledge":
                expected = set(call.expected_document_ids)
                returned = {item.document_id for item in evidence if item.document_id}
                satisfies = status == "ok" and bool(returned) and (
                    not expected or expected.issubset(returned)
                )
            else:
                satisfies = status == "ok" and _has_required_operational_fact(call, payload)
            trace = TraceEvent(
                event="mcp_tool_call", sequence=sequence, tool_name=call.tool_name,
                arguments=_safe_arguments(call.arguments), status=status,
                summary=_summary(call, status, payload),
                source=str(payload.get("data_source") or call.domain),
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
            executed.append(ExecutedCall(call, status, evidence, trace, satisfies))
        return executed

    @staticmethod
    def _evidence(call: PlannedToolCall, status: str, payload: dict[str, Any]) -> list[EvidenceItem]:
        if call.kind == "knowledge":
            return [
                EvidenceItem(
                    evidence_type="knowledge", source=call.tool_name, status=status,
                    request_id=call.request_id, data_domain=call.domain,
                    document_id=result.get("document_id"), document_title=result.get("title"),
                    document_type=result.get("document_type"), section=result.get("section"),
                    snippet=result.get("snippet"),
                )
                for result in payload.get("results", [])
            ]
        fact = {key: value for key, value in payload.items() if key not in {"status", "message", "data_source"}}
        return [
            EvidenceItem(
                evidence_type="operational", source=call.tool_name, status=status,
                request_id=call.request_id,
                data_domain=str(payload.get("data_source") or call.domain), fact=fact or None,
            )
        ]
