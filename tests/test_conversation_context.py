from __future__ import annotations

import asyncio
from datetime import date
from types import SimpleNamespace

import pytest

from app.agent.context import AgentContext
from app.agent.orchestrator import EvidenceOrchestrator
from app.agent.planner import DeterministicPlanner, _mentioned_date
from app.identity.provider import IdentityProvider
from app.identity.session import SessionNotFoundError, SessionStore


SCENARIO = (
    "I'm in Dar es Salaam for a project and I have just been told I have another "
    "assignment in Zambia on Wednesday. I want to stop by the Nairobi office on "
    "Tuesday, but I want to take PTO on Monday. Will the company cover the full "
    "fare for the Nairobi trip if I'm on PTO on Monday?"
)


class SafeEvidenceClient:
    """Provides complete schema-shaped evidence without promoting user assertions."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, arguments))
        if name == "search_knowledge_documents":
            expected = {
                "leave": "MSG-POL-001",
                "assignment": "MSG-POL-002",
                "travel": "MSG-POL-003",
                "expenses": "MSG-POL-007",
            }
            document_id = expected.get(arguments.get("topic"), "MSG-PROC-004")
            payload = {"status": "ok", "results": [{
                "document_id": document_id, "title": "Controlled evidence",
                "document_type": "policy", "section": "Scope",
                "snippet": "Controlled Meridian evidence for the requested domain.",
            }]}
        elif name == "lookup_employee_profile":
            payload = {"status": "ok", "profile": {"job_title": "Senior Consultant"}}
        elif name == "check_pto_balance":
            payload = {"status": "ok", "pto_balance": {"available_days": 15}}
        elif name == "lookup_active_assignment":
            payload = {"status": "ok", "assignment": {"assignment_id": "ENG-2045", "location": "Nairobi"}}
        elif name == "lookup_travel_authorization":
            payload = {"status": "ok", "travel_authorization": {"status": "approved", "location": "Nairobi"}}
        elif name == "get_mock_travel_booking":
            payload = {"status": "ok", "booking": {"status": "recorded", "destination": "Nairobi"}}
        else:
            payload = {"status": "not_found"}
        return SimpleNamespace(structuredContent=payload, content=[])


def _context(store: SessionStore, session_id: str, message: str) -> AgentContext:
    return AgentContext(
        session_id=session_id, identity=store.resolve(session_id), message=message,
        as_of=date(2026, 10, 3), conversation_history=store.history(session_id),
    )


def test_complex_scenario_routes_fresh_policy_and_recorded_evidence() -> None:
    store = SessionStore(IdentityProvider())
    session = store.create("naledi.molefe")
    client = SafeEvidenceClient()
    result = asyncio.run(EvidenceOrchestrator(client).run(_context(store, session.session_id, SCENARIO)))
    tools = [call.tool_name for call in result.plan.calls]

    assert {"lookup_active_assignment", "check_pto_balance", "lookup_travel_authorization"} <= set(tools)
    assert "search_knowledge_documents" in tools
    assert any(arguments.get("as_of") == "2026-10-07" for name, arguments in client.calls if name == "lookup_active_assignment")
    recorded = str([item.fact for item in result.evidence.items if item.fact])
    assert "Zambia" not in recorded
    assert "Nairobi" in recorded


def test_follow_ups_reuse_bounded_user_context_for_planning_not_evidence() -> None:
    store = SessionStore(IdentityProvider())
    session = store.create("naledi.molefe")
    store.record_turn(session.session_id, SCENARIO, "More evidence is needed.", "insufficient_evidence")

    no_pto = asyncio.run(DeterministicPlanner().plan(_context(store, session.session_id, "What if I don't take PTO on Monday?")))
    direct = asyncio.run(DeterministicPlanner().plan(_context(store, session.session_id, "What if I fly straight to Zambia instead?")))
    assert "pto" in no_pto.domains and "business_travel" in no_pto.domains
    assert "business_travel" in direct.domains and "assignment" in direct.domains
    assert all(call.tool_name != "create_mock_travel_request" for call in (*no_pto.calls, *direct.calls))


def test_ambiguous_follow_up_without_history_requires_clarification() -> None:
    store = SessionStore(IdentityProvider())
    session = store.create("naledi.molefe")
    result = asyncio.run(EvidenceOrchestrator(SafeEvidenceClient()).run(
        _context(store, session.session_id, "What about that trip?")
    ))
    assert result.status == "invalid_request"
    assert result.plan.intent == "clarification_required"


def test_history_is_bounded_and_session_private_and_resettable() -> None:
    store = SessionStore(IdentityProvider())
    naledi = store.create("naledi.molefe")
    liam = store.create("liam.chen")
    for number in range(20):
        store.record_turn(naledi.session_id, f"Naledi scenario {number}", "answer", "answered")
    assert len(store.history(naledi.session_id)) == store.MAX_CONVERSATION_TURNS
    assert store.history(naledi.session_id)[0].user_message == "Naledi scenario 8"
    assert store.history(liam.session_id) == ()
    store.end(naledi.session_id)
    with pytest.raises(SessionNotFoundError):
        store.history(naledi.session_id)


def test_relative_dates_use_authoritative_request_date() -> None:
    controlled = date(2026, 10, 3)  # Saturday
    assert _mentioned_date("PTO on Monday", controlled) == "2026-10-05"
    assert _mentioned_date("fly on Tuesday", controlled) == "2026-10-06"
    assert _mentioned_date("assignment on Wednesday", controlled) == "2026-10-07"
    assert _mentioned_date("travel tomorrow", controlled) == "2026-10-04"
