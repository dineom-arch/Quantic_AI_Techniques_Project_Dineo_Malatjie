"""Deterministic evidence orchestration over the real MCP client boundary."""

from __future__ import annotations

from app.agent.context import AgentContext
from app.agent.evidence import EvidenceBundle, OrchestrationResult, OrchestrationStatus
from app.agent.executor import MCPPlanExecutor
from app.agent.planner import DeterministicPlanner, ExecutionPlan
from app.agent.traces import TraceEvent


class EvidenceOrchestrator:
    def __init__(self, client, planner: DeterministicPlanner | None = None) -> None:
        self.planner = planner or DeterministicPlanner()
        self.executor = MCPPlanExecutor(client)

    async def run(self, context: AgentContext) -> OrchestrationResult:
        plan = await self.planner.plan(context)
        identity_trace = TraceEvent(
            event="authenticated_identity_loaded", status="ok",
        )
        if plan.intent == "out_of_scope":
            return self._result(context, plan, [], [identity_trace], "out_of_scope", "The request is outside the supported Meridian People and Travel Operations scope.")

        executed = await self.executor.execute(plan)
        statuses = [item.status for item in executed]
        completed = [item.request.request_id for item in executed if item.satisfies_requirement]
        required = [item.request_id for item in plan.calls if item.required]
        missing = [request_id for request_id in required if request_id not in completed]
        if not missing:
            status: OrchestrationStatus = "sufficient_evidence"
            message = "Required operational and approved knowledge evidence was collected."
        else:
            status = "insufficient_evidence"
            if "dependency_unavailable" in statuses:
                status = "dependency_unavailable"
            elif "forbidden" in statuses:
                status = "forbidden"
            elif "invalid_request" in statuses:
                status = "invalid_request"
            elif "confirmation_required" in statuses:
                status = "confirmation_required"
            elif any(
                item.status == "not_found" and item.request.kind == "operational"
                for item in executed
            ):
                status = "not_found"
            message = "Required authoritative evidence could not be fully collected."
        return self._result(
            context, plan, executed, [identity_trace, *(item.trace for item in executed)],
            status, message, completed, missing,
        )

    @staticmethod
    def _result(
        context: AgentContext,
        plan: ExecutionPlan,
        executed,
        traces: list[TraceEvent],
        status: OrchestrationStatus,
        message: str,
        completed: list[str] | None = None,
        missing: list[str] | None = None,
    ) -> OrchestrationResult:
        required = [call.request_id for call in plan.calls if call.required]
        return OrchestrationResult(
            status=status, intent=plan.intent, domains=list(plan.domains),
            authenticated_display_name=context.identity.display_name, plan=plan,
            evidence=EvidenceBundle(
                items=[evidence for call in executed for evidence in call.evidence],
                required_request_ids=required, completed_request_ids=completed or [],
                missing_request_ids=missing or required, complete=status == "sufficient_evidence",
            ),
            tool_trace=traces, message=message,
        )
