"""Deterministic intent and evidence-needs planning without policy decisions."""

from __future__ import annotations

from datetime import date
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.agent.context import AgentContext
from app.identity.runtime import identity_provider


ToolKind = Literal["operational", "knowledge"]


class PlannedToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    tool_name: str
    arguments: dict[str, Any]
    kind: ToolKind
    domain: str
    required: bool = True
    expected_document_ids: tuple[str, ...] = ()


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    intent: str
    domains: tuple[str, ...]
    calls: tuple[PlannedToolCall, ...] = ()


MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def _mentioned_date(message: str, fallback: date) -> str:
    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", message)
    if iso:
        return iso.group(1)
    written = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?(?:\s+and\s+\d{1,2})?\s+"
        r"(" + "|".join(MONTHS) + r")(?:\s+(20\d{2}))?\b",
        message,
        flags=re.IGNORECASE,
    )
    if written:
        year = int(written.group(3) or fallback.year)
        return date(year, MONTHS[written.group(2).casefold()], int(written.group(1))).isoformat()
    return fallback.isoformat()


def _references_other_identity(text: str, context: AgentContext) -> bool:
    """Recognise controlled identity references without using prompt identity as authority."""
    for option in identity_provider.list_active_options():
        if option.corporate_username == context.identity.corporate_username:
            continue
        identity = identity_provider.get_by_username(option.corporate_username)
        if identity is None:
            continue
        references = {
            identity.display_name.casefold(), identity.given_name.casefold(),
            identity.surname.casefold(), identity.corporate_username.casefold(),
            identity.employee_id.casefold(),
        }
        if any(re.search(rf"(?<![\w.-]){re.escape(value)}(?![\w.-])", text) for value in references):
            return True
    return False


def _external_company_policy(text: str) -> bool:
    match = re.search(r"\bwhat does\s+([a-z][\w&.-]*)['’]s\s+.+?policy\b", text)
    return bool(match and match.group(1) not in {"meridian", "msg"})


class DeterministicPlanner:
    """Maps bounded request language to evidence domains and approved tools."""

    async def plan(self, context: AgentContext) -> ExecutionPlan:
        text = context.message.casefold()
        domains: list[str] = []
        calls: list[PlannedToolCall] = []

        def add_domain(name: str) -> None:
            if name not in domains:
                domains.append(name)

        def add_call(
            tool_name: str,
            arguments: dict[str, Any],
            kind: ToolKind,
            evidence_domain: str,
            expected: tuple[str, ...] = (),
        ) -> None:
            calls.append(
                PlannedToolCall(
                    request_id=f"evidence-{len(calls) + 1:02d}",
                    tool_name=tool_name,
                    arguments=arguments,
                    kind=kind,
                    domain=evidence_domain,
                    expected_document_ids=expected,
                )
            )

        if _external_company_policy(text):
            return ExecutionPlan(intent="out_of_scope", domains=())

        pto = any(term in text for term in ("pto", "leave", "days off", "time off"))
        flight_policy = any(
            term in text for term in ("flight", "business class", "economy", "cabin class", "air travel")
        ) or bool(re.search(r"\bfl(?:y|ying)\b", text))
        travel = any(
            term in text
            for term in ("travel", "travelling", "flight", "hotel", "itinerary", "return flight", "stay in", "trip")
        )
        personal_extension = any(
            term in text
            for term in ("extend", "extension", "change my return", "stay until", "stay through", "stay after")
        )
        extension_information_only = any(
            term in text for term in ("what would", "what do i need", "show me", "who would")
        )
        extension_situation = personal_extension and travel and not extension_information_only and any(
            term in text
            for term in (
                "nairobi", "flight", "hotel", "itinerary", "stay", "assignment ends",
                "create", "submit", "for me",
            )
        )
        mentioned_calendar_date = bool(
            re.search(r"\b20\d{2}-\d{2}-\d{2}\b", text)
            or re.search(r"\b\d{1,2}(?:st|nd|rd|th)?(?:\s+and\s+\d{1,2})?\s+(?:" + "|".join(MONTHS) + r")\b", text)
        )
        explicit_assignment = bool(re.search(r"\bENG-\d+\b", context.message, re.IGNORECASE)) or any(
            term in text for term in ("my assignment", "current assignment", "active assignment")
        )
        assignment = (
            explicit_assignment or extension_situation
            or (personal_extension and "travel extension" in text)
            or (pto and mentioned_calendar_date)
        )
        expense = any(term in text for term in ("expense", "claim", "reimburse", "reimbursement", "receipt", "cost of my"))
        unsupported_cost_subject = bool(re.search(r"\bcost of my\s+.+?\s+while\b", text))
        taxi_expense = "taxi" in text or "ground transport" in text
        meal_expense = any(term in text for term in ("meal", "dinner", "lunch", "breakfast"))
        benefits = any(term in text for term in ("benefit", "medical plan", "enrolled"))
        per_diem = "per diem" in text or (meal_expense and "nairobi" in text)
        security = "security" in text and travel
        remote = any(term in text for term in ("remote", "hybrid"))
        international_work = any(term in text for term in ("work from", "international work", "cross-border"))
        identity_override_claim = any(
            term in text for term in ("pretend i am", "pretend i'm", "i'm emp-", "i am emp-")
        )
        privacy = any(
            term in text for term in ("another employee", "someone else's", "colleague's")
        ) or (_references_other_identity(text, context) and not identity_override_claim)
        support = unsupported_cost_subject or any(
            term in text
            for term in (
                "gift", "hospitality", "escalat", "support route", "vip ticket",
                "tickets offered", "client gave", "vendor gave", "entertainment",
            )
        )
        profile = any(term in text for term in ("my profile", "job title", "job level", "who am i"))
        flight_personal_context = flight_policy and any(
            term in text for term in ("i'm", "i am", "can i", "my manager", "my approved")
        )
        approved_travel_context = flight_policy and "approved" in text and any(
            term in text for term in ("travel", "travelling", "assignment")
        )

        if not any((pto, travel, flight_policy, assignment, expense, benefits, per_diem, security, remote, international_work, privacy, support, profile, personal_extension)):
            return ExecutionPlan(intent="out_of_scope", domains=())

        if profile and not pto:
            add_domain("employee")
            add_call("lookup_employee_profile", {"target": "self"}, "operational", "employee")

        if pto:
            add_domain("pto")
            add_call("lookup_employee_profile", {"target": "self"}, "operational", "employee")
            add_call(
                "check_pto_balance",
                {"target": "other" if privacy else "self"},
                "operational", "pto",
            )
            add_call(
                "search_knowledge_documents",
                {"query": "PTO active assignment Engagement Manager approval 14 calendar days notice", "document_type": "policy", "top_k": 5, "topic": "leave"},
                "knowledge", "pto", ("MSG-POL-001",),
            )
            add_call(
                "search_knowledge_documents",
                {"query": "PTO request and approval process", "document_type": "procedure", "top_k": 5, "topic": "leave"},
                "knowledge", "pto", ("MSG-PROC-001",),
            )

        if assignment:
            add_domain("assignment")
            assignment_as_of = (
                context.as_of.isoformat()
                if personal_extension
                else _mentioned_date(context.message, context.as_of)
            )
            add_call(
                "lookup_active_assignment",
                {"target": "self", "as_of": assignment_as_of},
                "operational", "assignment",
            )
            add_call(
                "search_knowledge_documents",
                {"query": "active client assignment responsibilities", "document_type": "policy", "top_k": 5, "topic": "assignment"},
                "knowledge", "assignment", ("MSG-POL-002",),
            )

        broad_travel = travel and not (flight_policy and not personal_extension) and not taxi_expense
        if broad_travel or extension_situation:
            add_domain("business_travel")
            add_call("lookup_travel_authorization", {"target": "self"}, "operational", "travel")
            if personal_extension or any(term in text for term in ("booking", "hotel", "flight")):
                add_call("get_mock_travel_booking", {"target": "self"}, "operational", "travel")
            add_call(
                "search_knowledge_documents",
                {"query": "business travel personal extension itinerary flight hotel", "document_type": "policy", "top_k": 5, "topic": "travel"},
                "knowledge", "travel", ("MSG-POL-003",),
            )
            if personal_extension or "booking" in text or "change" in text:
                add_call(
                    "search_knowledge_documents",
                    {"query": "personal extension itinerary modification booking process", "document_type": "procedure", "top_k": 5, "topic": "travel"},
                    "knowledge", "travel", ("MSG-PROC-003",),
                )
            if any(term in text for term in ("hotel", "accommodation", "taxi", "ground transport")):
                add_domain("accommodation_transport")
                add_call(
                    "search_knowledge_documents",
                    {"query": "accommodation hotel ground transport requirements", "document_type": "policy", "top_k": 5, "topic": "travel"},
                    "knowledge", "accommodation_transport", ("MSG-POL-005",),
                )

        if taxi_expense:
            add_domain("business_travel")
            add_call("lookup_travel_authorization", {"target": "self"}, "operational", "travel")
            add_call(
                "search_knowledge_documents",
                {"query": "taxi ground transport approved business locations", "document_type": "policy", "top_k": 5, "topic": "travel"},
                "knowledge", "accommodation_transport", ("MSG-POL-005",),
            )

        if flight_policy:
            add_domain("flight_booking")
            if not extension_situation and flight_personal_context:
                add_call("lookup_employee_profile", {"target": "self"}, "operational", "employee")
            if not extension_situation and approved_travel_context:
                add_call("lookup_travel_authorization", {"target": "self"}, "operational", "travel")
            add_call(
                "search_knowledge_documents",
                {"query": "flight booking cabin class economy business class long haul duration exception", "document_type": "policy", "top_k": 5, "topic": "travel"},
                "knowledge", "flight_booking", ("MSG-POL-004",),
            )

        if personal_extension and not extension_situation:
            add_domain("business_travel_policy")
            add_call(
                "search_knowledge_documents",
                {"query": "business travel personal extension eligibility cost approval", "document_type": "policy", "top_k": 5, "topic": "travel"},
                "knowledge", "business_travel", ("MSG-POL-003",),
            )
            add_call(
                "search_knowledge_documents",
                {"query": "personal extension itinerary modification approval procedure", "document_type": "procedure", "top_k": 5, "topic": "travel"},
                "knowledge", "business_travel", ("MSG-PROC-003",),
            )

        if per_diem:
            add_domain("per_diem")
            if "london" in text:
                per_diem_country, per_diem_city = "United Kingdom", "London"
            elif "nairobi" in text:
                per_diem_country, per_diem_city = "Kenya", "Nairobi"
            else:
                per_diem_country, per_diem_city = "", ""
            add_call(
                "get_per_diem_rate",
                {"country": per_diem_country, "city": per_diem_city, "as_of": _mentioned_date(context.message, context.as_of)},
                "operational", "per_diem",
            )
            add_call(
                "search_knowledge_documents",
                {"query": "per diem coverage and applicability", "document_type": "policy", "top_k": 5, "topic": "travel"},
                "knowledge", "per_diem", ("MSG-POL-006",),
            )

        if expense:
            add_domain("expenses")
            expense_match = re.search(r"\bEXP-\d+\b", context.message, re.IGNORECASE)
            if expense_match:
                add_call(
                    "get_mock_expense_claim",
                    {"target": "self", "expense_id": expense_match.group(0).upper()},
                    "operational", "expenses",
                )
            add_call(
                "search_knowledge_documents",
                {"query": "expense reimbursement eligibility and submission", "document_type": "all", "top_k": 5, "topic": "expenses"},
                "knowledge", "expenses", ("MSG-POL-007", "MSG-PROC-004"),
            )

        if benefits:
            add_domain("benefits")
            if "eligible" in text or "eligibility" in text:
                add_call("lookup_employee_profile", {"target": "self"}, "operational", "employee")
            add_call("lookup_benefits_status", {"target": "self", "benefit_type": None}, "operational", "benefits")
            add_call(
                "search_knowledge_documents",
                {"query": "benefits eligibility", "document_type": "policy", "top_k": 5, "topic": "benefits"},
                "knowledge", "benefits", ("MSG-POL-010",),
            )

        knowledge_only = (
            (security, "security", "security while travelling", "policy", "security", ("MSG-POL-009",)),
            (remote, "remote_work", "remote hybrid working", "policy", "working_arrangements", ("MSG-POL-011",)),
            (international_work, "international_work", "international working approval", "all", "international_work", ("MSG-POL-008", "MSG-PROC-005")),
            (privacy, "privacy", "employee data access privacy", "policy", "privacy", ("MSG-POL-012",)),
            (support, "enterprise_support", "gifts hospitality Ethics Compliance support route substantive determination", "procedure", "enterprise_support", ("MSG-PROC-007",)),
        )
        for needed, name, query, document_type, topic, expected in knowledge_only:
            if needed:
                add_domain(name)
                add_call(
                    "search_knowledge_documents",
                    {"query": query, "document_type": document_type, "top_k": 5, "topic": topic},
                    "knowledge", name, expected,
                )

        intent = "multi_step_workflow" if len(domains) > 1 else "evidence_retrieval"
        return ExecutionPlan(intent=intent, domains=tuple(domains), calls=tuple(calls))
