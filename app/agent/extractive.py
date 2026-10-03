"""Deterministic extractive synthesis used when a model draft cannot be verified."""

from __future__ import annotations

import re
from typing import Any


def _sentence(snippet: str) -> str:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", snippet) if part.strip()]
    return parts[0] if parts else snippet.strip()


def _find_values(value: Any, key: str) -> list[Any]:
    if isinstance(value, dict):
        found = [value[key]] if key in value else []
        return found + [item for child in value.values() for item in _find_values(child, key)]
    if isinstance(value, list):
        return [item for child in value for item in _find_values(child, key)]
    return []


def _operational_subset(source: str, fact: dict[str, Any]) -> dict[str, Any]:
    selectors: dict[str, tuple[str, tuple[str, ...]]] = {
        "lookup_employee_profile": ("profile", ("display_name", "job_title", "job_level")),
        "check_pto_balance": ("pto_balance", ("available_days",)),
        "lookup_active_assignment": (
            "assignment", ("assignment_id", "location_city", "location_country", "start_date", "end_date")
        ),
        "lookup_travel_authorization": (
            "travel_authorization", ("status", "destination", "destination_city", "assignment_id")
        ),
        "get_mock_travel_booking": (
            "booking", ("currency", "business_return_fare", "hotel_check_out", "personal_extension_proposal")
        ),
        "get_per_diem_rate": ("per_diem_rate", ("currency", "daily_rate", "city")),
        "get_mock_expense_claim": ("expense_claim", ("category", "amount", "currency", "status")),
        "lookup_benefits_status": ("benefits", ()),
    }
    selector = selectors.get(source)
    if selector is None:
        return fact
    container_name, keys = selector
    container = fact.get(container_name)
    if container_name == "benefits" and isinstance(container, list) and container:
        selected = {
            key: container[0][key]
            for key in ("benefit_type", "eligibility_status", "enrollment_status")
            if key in container[0]
        }
        return {container_name: [selected]}
    if not isinstance(container, dict):
        return fact
    return {container_name: {key: container[key] for key in keys if key in container}}


def _scalar_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_scalar_text(child) for child in value.values())
    if isinstance(value, list):
        return " ".join(_scalar_text(child) for child in value)
    return str(value)


def build_extractive_draft(request: dict[str, Any]) -> dict[str, Any]:
    """Build a verifier-compatible draft without adding facts or policy conclusions."""
    question = str(request["question"]).casefold()
    evidence = request["authorised_evidence"]
    claims: list[dict[str, Any]] = []
    citations: list[dict[str, str]] = []
    approval_requests: list[dict[str, Any]] = []

    for index, item in enumerate(evidence, start=1):
        if item["evidence_type"] == "operational":
            subset = _operational_subset(item["source"], item.get("fact") or {})
            claims.append({
                "claim_id": f"operational-{index}",
                "text": f"Recorded facts: {_scalar_text(subset)}",
                "claim_type": "operational",
                "evidence_ids": [item["evidence_id"]],
                "supporting_fact": subset,
            })
            continue
        quote = _sentence(item.get("snippet") or "")
        claim_type = item.get("document_type")
        if not quote or claim_type not in {"policy", "procedure"}:
            continue
        claim_id = f"knowledge-{index}"
        claims.append({
            "claim_id": claim_id,
            "text": quote,
            "claim_type": claim_type,
            "evidence_ids": [item["evidence_id"]],
            "evidence_quote": quote,
        })
        citations.append({"evidence_id": item["evidence_id"]})
        if "engagement manager" in quote.casefold() and any(
            term in question for term in ("pto", "leave", "extend", "extension", "approv")
        ):
            assignment_ids = [
                str(value)
                for source in evidence if source["evidence_type"] == "operational"
                for value in _find_values(source.get("fact"), "assignment_id")
            ]
            approval_requests.append({
                "claim_id": claim_id,
                "approval_role": "engagement_manager",
                "assignment_id": assignment_ids[0] if assignment_ids else None,
            })

    gifts = any(term in question for term in ("gift", "hospitality", "vip tickets"))
    if gifts:
        route_claims = [
            claim for claim in claims
            if claim["claim_type"] == "procedure"
            and "ethics & compliance" in claim["text"].casefold()
        ]
        claims = route_claims
        if claims:
            claims.insert(0, {
                "claim_id": "controlled-limitation",
                "text": "The retrieved procedure does not establish a substantive gifts or hospitality rule.",
                "claim_type": "limitation",
                "evidence_ids": claims[0]["evidence_ids"],
            })
        citations = [
            citation for citation in citations
            if any(citation["evidence_id"] in claim["evidence_ids"] for claim in route_claims)
        ]

    return {
        "proposed_answer": "Untrusted extractive draft",
        "proposed_status": "insufficient_evidence" if gifts else "answered",
        "claims": claims,
        "citations": citations,
        "approval_requests": approval_requests,
        "insufficiency_statement": None,
    }
