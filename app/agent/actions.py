"""Deterministic workflow completion for confirmation-gated mock actions."""

from __future__ import annotations

import json
import re
from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field

from app.actions.store import PendingAction, get_mock_action_store
from app.agent.context import AgentContext
from app.agent.evidence import OrchestrationResult
from app.agent.synthesis import GroundedAnswer, VerifiedCitation
from app.agent.traces import TraceEvent


class ActionWorkflowResult(BaseModel):
    answer: str
    status: str
    citations: list[VerifiedCitation] = Field(default_factory=list)
    source_snippets: list[VerifiedCitation] = Field(default_factory=list)
    trace_events: list[TraceEvent] = Field(default_factory=list)


def _payload(result: Any) -> dict[str, Any]:
    if result.structuredContent is not None:
        return dict(result.structuredContent)
    if result.content and getattr(result.content[0], "text", None):
        parsed = json.loads(result.content[0].text)
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _explicit_confirmation(message: str, confirmation_control: bool) -> bool:
    if confirmation_control:
        return True
    normalised = " ".join(message.casefold().strip().rstrip(".!" ).split())
    patterns = (
        r"yes(?:,)? (?:please )?(?:create|submit|proceed)(?: .+)?",
        r"(?:create|submit) it",
        r"proceed(?: with (?:the )?(?:mock )?(?:ticket|travel request|request))?",
    )
    return any(re.fullmatch(pattern, normalised) for pattern in patterns)


def _action_related(message: str) -> bool:
    text = message.casefold()
    return any(term in text for term in ("yes", "create", "submit", "proceed", "ticket", "request"))


def _trace(sequence: int, tool_name: str, status: str, started: float) -> TraceEvent:
    return TraceEvent(
        event="mcp_tool_call", sequence=sequence, tool_name=tool_name,
        arguments={"confirmed": True if status != "confirmation_required" else False},
        status=status, summary=f"Mock action returned {status}",
        source="runtime.mock_actions",
        duration_ms=round((perf_counter() - started) * 1000, 2),
    )


def _citation_context(citations: list[VerifiedCitation]) -> list[dict[str, Any]]:
    return [item.model_dump() for item in citations]


class ActionWorkflowCoordinator:
    def __init__(self, mcp_client) -> None:
        self.mcp_client = mcp_client
        self.store = get_mock_action_store()

    async def before_grounding(self, context: AgentContext) -> ActionWorkflowResult | None:
        pending = self.store.pending(context.session_id)
        confirmed = _explicit_confirmation(context.message, context.confirm_action)
        if pending is None:
            if confirmed:
                return ActionWorkflowResult(
                    answer="There is no pending mock action for this authenticated session. A new action must first be grounded and proposed.",
                    status="clarification_required",
                )
            return None
        if not confirmed:
            if _action_related(context.message):
                return self._pending_reminder(pending)
            return None
        return await self._execute_pending(context, pending)

    async def after_grounding(
        self,
        context: AgentContext,
        orchestration: OrchestrationResult,
        grounded: GroundedAnswer,
    ) -> ActionWorkflowResult | None:
        text = context.message.casefold()
        if self._personal_extension_action_ready(text, orchestration, grounded):
            booking = self._operational_fact(orchestration, "get_mock_travel_booking", "booking")
            approval = next(
                (item for item in grounded.resolved_approvals if item.approval_role == "engagement_manager"),
                None,
            )
            proposal = booking.get("personal_extension_proposal", {})
            arguments = {
                "request_type": "personal_extension",
                "details": {
                    "summary": "Personal extension of an authorised business trip",
                    "approval_role": approval.approval_role if approval else None,
                    "approval_person": approval.display_name if approval else None,
                    "proposed_return_date": proposal.get("proposed_return_date"),
                    "incremental_employee_cost": proposal.get("incremental_employee_cost"),
                    "currency": booking.get("currency"),
                },
                "confirmed": False,
            }
            return await self._propose(
                context, grounded, "create_mock_travel_request", arguments,
                "A mock personal travel-extension request is ready. Reply “Yes, create the mock travel request” to create it. This will not book or approve travel.",
            )
        if self._support_route_supported(text, grounded):
            if "email" in text and any(term in text for term in ("draft", "write", "prepare")):
                return await self._draft_support_email(context, grounded)
            if "ticket" in text and any(term in text for term in ("create", "open", "submit")):
                arguments = {
                    "category": "Ethics & Compliance support",
                    "summary": "Request guidance on an unresolved gifts or hospitality question",
                    "confirmed": False,
                }
                return await self._propose(
                    context, grounded, "create_mock_hr_ticket", arguments,
                    "A mock Ethics & Compliance support ticket is ready. Reply “Yes, create the ticket” to create it. No real enterprise ticket will be opened.",
                )
        return None

    @staticmethod
    def _personal_extension_action_ready(
        text: str, orchestration: OrchestrationResult, grounded: GroundedAnswer,
    ) -> bool:
        personal_extension = any(term in text for term in ("extend", "extension", "change my return"))
        information_only = any(term in text for term in ("what would", "what do i need", "show me", "who would"))
        documents = {item.document_id for item in grounded.citations}
        approval_supported = any(
            item.approval_role == "engagement_manager" for item in grounded.resolved_approvals
        )
        sources = {item.source for item in orchestration.evidence.items if item.status == "ok"}
        return (
            personal_extension and not information_only and grounded.status == "answered"
            and {"MSG-POL-003", "MSG-PROC-003"}.issubset(documents)
            and approval_supported
            and {"lookup_travel_authorization", "get_mock_travel_booking"}.issubset(sources)
        )

    @staticmethod
    def _support_route_supported(text: str, grounded: GroundedAnswer) -> bool:
        return (
            any(term in text for term in ("gift", "hospitality"))
            and "Ethics & Compliance" in grounded.answer
            and any(item.document_id == "MSG-PROC-007" for item in grounded.citations)
        )

    @staticmethod
    def _operational_fact(
        orchestration: OrchestrationResult, source: str, key: str,
    ) -> dict[str, Any]:
        for item in orchestration.evidence.items:
            if item.source == source and item.status == "ok" and item.fact:
                value = item.fact.get(key)
                return value if isinstance(value, dict) else {}
        return {}

    async def _propose(
        self,
        context: AgentContext,
        grounded: GroundedAnswer,
        tool_name: str,
        arguments: dict[str, Any],
        prompt: str,
    ) -> ActionWorkflowResult:
        started = perf_counter()
        try:
            payload = _payload(await self.mcp_client.call_tool(tool_name, arguments))
        except Exception:
            payload = {"status": "dependency_unavailable"}
        status = str(payload.get("status", "dependency_unavailable"))
        trace = _trace(1, tool_name, status, started)
        if status != "confirmation_required":
            return ActionWorkflowResult(
                answer="The mock action could not be prepared. No action was performed.",
                status="tool_error" if status == "dependency_unavailable" else "clarification_required",
                citations=grounded.citations, source_snippets=grounded.source_snippets,
                trace_events=[trace],
            )
        self.store.attach_public_context(context.session_id, {
            "answer": grounded.answer,
            "citations": _citation_context(grounded.citations),
            "source_snippets": _citation_context(grounded.source_snippets),
        })
        return ActionWorkflowResult(
            answer=f"{grounded.answer}\n\n{prompt}", status="action_confirmation_required",
            citations=grounded.citations, source_snippets=grounded.source_snippets,
            trace_events=[trace],
        )

    async def _execute_pending(
        self, context: AgentContext, pending: PendingAction,
    ) -> ActionWorkflowResult:
        arguments = dict(pending.arguments)
        if pending.action_name == "create_mock_travel_request":
            request_type = str(arguments.pop("request_type"))
            call_arguments = {"request_type": request_type, "details": arguments, "confirmed": True}
        else:
            call_arguments = {**arguments, "confirmed": True}
        started = perf_counter()
        try:
            payload = _payload(await self.mcp_client.call_tool(pending.action_name, call_arguments))
        except Exception:
            payload = {"status": "dependency_unavailable"}
        status = str(payload.get("status", "dependency_unavailable"))
        trace = _trace(1, pending.action_name, status, started)
        context_data = pending.public_context
        citations = [VerifiedCitation(**item) for item in context_data.get("citations", [])]
        snippets = [VerifiedCitation(**item) for item in context_data.get("source_snippets", [])]
        if status != "ok":
            return ActionWorkflowResult(
                answer="The mock action was not completed. No real or simulated external action was claimed as successful.",
                status="tool_error" if status == "dependency_unavailable" else "clarification_required",
                citations=citations, source_snippets=snippets, trace_events=[trace],
            )
        if pending.action_name == "create_mock_travel_request":
            answer = (
                f"Created mock travel request {payload['mock_request_reference']}. "
                "This is a simulated request only; it is not a booking or approval."
            )
        else:
            answer = (
                f"Created mock support ticket {payload['mock_ticket_reference']}. "
                "This is a simulated ticket only; no enterprise system was contacted."
            )
        return ActionWorkflowResult(
            answer=answer, status="answered", citations=citations,
            source_snippets=snippets, trace_events=[trace],
        )

    async def _draft_support_email(
        self, context: AgentContext, grounded: GroundedAnswer,
    ) -> ActionWorkflowResult:
        arguments = {
            "purpose": "guidance on a gifts or hospitality question",
            "recipient_role": "Ethics & Compliance",
            "supported_facts": ["The approved procedure identifies Ethics & Compliance as the support route."],
        }
        started = perf_counter()
        try:
            payload = _payload(await self.mcp_client.call_tool("draft_hr_email", arguments))
        except Exception:
            payload = {"status": "dependency_unavailable"}
        status = str(payload.get("status", "dependency_unavailable"))
        trace = _trace(1, "draft_hr_email", status, started)
        if status != "ok" or not isinstance(payload.get("draft"), dict):
            return ActionWorkflowResult(
                answer="The support email draft could not be prepared. No email was sent.",
                status="tool_error", citations=grounded.citations,
                source_snippets=grounded.source_snippets, trace_events=[trace],
            )
        draft = payload["draft"]
        return ActionWorkflowResult(
            answer=(
                f"Draft email to {draft['recipient_role']}\n\nSubject: {draft['subject']}\n\n"
                f"{draft['body']}\n\nThis is a draft only; no email was sent."
            ),
            status="answered", citations=grounded.citations,
            source_snippets=grounded.source_snippets, trace_events=[trace],
        )

    @staticmethod
    def _pending_reminder(pending: PendingAction) -> ActionWorkflowResult:
        label = "mock travel request" if pending.action_name == "create_mock_travel_request" else "mock support ticket"
        context = pending.public_context
        return ActionWorkflowResult(
            answer=f"The {label} is still pending. Please explicitly confirm that you want it created.",
            status="action_confirmation_required",
            citations=[VerifiedCitation(**item) for item in context.get("citations", [])],
            source_snippets=[VerifiedCitation(**item) for item in context.get("source_snippets", [])],
        )
