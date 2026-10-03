from __future__ import annotations

import asyncio
import json
import socket
from threading import Thread
import time

import httpx
import pytest
import uvicorn

from app.identity.runtime import session_store
from app.actions.store import get_mock_action_store
from app.integrations.mcp_runtime import meridian_mcp_client_class
from app.main import create_app


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _payload(result) -> dict:
    return result.structuredContent or json.loads(result.content[0].text)


@pytest.fixture(scope="module")
def operational_mcp():
    session_store.reset()
    get_mock_action_store().reset()
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="error")
    )
    thread = Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/auth/identities", timeout=0.25)
            if response.status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.05)
    else:
        raise AssertionError("ASGI server did not become ready")

    session_id = httpx.post(
        f"{base_url}/auth/session",
        json={"corporate_username": "naledi.molefe"},
    ).json()["session_id"]
    client = meridian_mcp_client_class()(f"{base_url}/mcp/", session_id=session_id)
    yield client
    server.should_exit = True
    thread.join(timeout=10)
    session_store.reset()
    get_mock_action_store().reset()
    assert not thread.is_alive()


def _call(client, name: str, arguments: dict) -> dict:
    return _payload(asyncio.run(client.call_tool(name, arguments)))


def test_authenticated_operational_tools_return_controlled_facts(operational_mcp) -> None:
    profile = _call(operational_mcp, "lookup_employee_profile", {"target": "self"})
    assert profile["status"] == "ok"
    assert profile["profile"]["display_name"] == "Naledi Molefe"
    assert "employee_id" not in json.dumps(profile)

    pto = _call(operational_mcp, "check_pto_balance", {"target": "self"})
    assert pto["pto_balance"]["available_days"] == 15

    assignment = _call(
        operational_mcp,
        "lookup_active_assignment",
        {"target": "self", "as_of": "2026-10-16"},
    )
    assert assignment["assignment"]["assignment_id"] == "ENG-2045"
    assert assignment["assignment"]["engagement_manager"]["display_name"] == "Amara Okafor"

    authorization = _call(
        operational_mcp,
        "lookup_travel_authorization",
        {"target": "self", "travel_authorization_id": "TA-3012"},
    )
    assert authorization["travel_authorization"]["status"] == "approved"
    assert "approved_by" not in authorization["travel_authorization"]

    booking = _call(
        operational_mcp, "get_mock_travel_booking", {"target": "self", "booking_id": "TB-4012"}
    )
    assert booking["booking"]["business_return_fare"] == 8400
    assert booking["booking"]["personal_extension_proposal"] == {
        "proposed_return_date": "2026-10-20",
        "alternative_return_fare": 9650,
        "incremental_employee_cost": 1250,
        "status": "proposed_not_approved",
    }
    assert "permitted" not in json.dumps(booking).lower()

    per_diem = _call(
        operational_mcp,
        "get_per_diem_rate",
        {"country": "Kenya", "city": "Nairobi", "as_of": "2026-10-08"},
    )
    assert per_diem["per_diem_rate"]["currency"] == "USD"
    assert per_diem["per_diem_rate"]["daily_rate"] == 85

    expense = _call(
        operational_mcp, "get_mock_expense_claim", {"target": "self", "expense_id": "EXP-5013"}
    )
    assert expense["expense_claim"]["category"] == "meal"
    assert expense["expense_claim"]["amount"] == 3200
    assert expense["expense_claim"]["status"] == "draft"
    assert "reimburs" not in json.dumps(expense).lower()

    benefits = _call(
        operational_mcp,
        "lookup_benefits_status",
        {"target": "self", "benefit_type": "MEDICAL"},
    )
    assert benefits["benefits"][0]["eligibility_status"] == "eligible"
    assert benefits["benefits"][0]["enrollment_status"] == "enrolled"


def test_approval_role_resolution_uses_only_explicit_relationships(operational_mcp) -> None:
    manager = _call(
        operational_mcp,
        "resolve_approval_role",
        {"target": "self", "approval_role": "engagement_manager", "assignment_id": "ENG-2045"},
    )
    assert manager == {
        "status": "ok",
        "role": "engagement_manager",
        "display_name": "Amara Okafor",
        "job_title": "Manager",
        "data_source": "hr_operations.assignments+employees",
    }
    designated = _call(
        operational_mcp,
        "resolve_approval_role",
        {"target": "self", "approval_role": "designated_travel_approver"},
    )
    assert designated["status"] == "not_found"
    assert designated["role"] == "designated_travel_approver"


def test_identity_privacy_missing_and_invalid_requests(operational_mcp) -> None:
    forbidden = _call(operational_mcp, "check_pto_balance", {"target": "Liam Chen"})
    assert forbidden["status"] == "forbidden"
    assert "pto_balance" not in forbidden
    assert "balance" not in forbidden
    private_fields = {"entitlement_days", "used_days", "pending_days", "available_days"}
    assert private_fields.isdisjoint(forbidden)
    serialized_forbidden = json.dumps(forbidden)
    assert "Liam Chen" not in serialized_forbidden
    assert "EMP-1104" not in serialized_forbidden
    assert "13" not in serialized_forbidden
    for field in private_fields:
        assert field not in serialized_forbidden

    override = _call(operational_mcp, "lookup_employee_profile", {"target": "EMP-1104"})
    assert override["status"] == "forbidden"
    self_after_override = _call(operational_mcp, "lookup_employee_profile", {"target": "self"})
    assert self_after_override["profile"]["display_name"] == "Naledi Molefe"

    missing = _call(
        operational_mcp, "get_mock_expense_claim", {"target": "self", "expense_id": "EXP-MISSING"}
    )
    assert missing["status"] == "not_found"
    invalid = _call(
        operational_mcp,
        "lookup_active_assignment",
        {"target": "self", "as_of": "next Thursday"},
    )
    assert invalid["status"] == "invalid_request"


def test_mock_action_tools_are_non_sending_and_confirmation_gated(operational_mcp) -> None:
    draft = _call(operational_mcp, "draft_hr_email", {
        "purpose": "guidance on a gift",
        "recipient_role": "Ethics & Compliance",
        "supported_facts": ["The procedure identifies this support route."],
    })
    assert draft["status"] == "ok"
    assert draft["draft"]["status"] == "draft"
    assert "no email was sent" in draft["message"].lower()

    ticket = _call(operational_mcp, "create_mock_hr_ticket", {
        "category": "Ethics & Compliance support",
        "summary": "Unresolved gift question",
        "confirmed": False,
    })
    assert ticket["status"] == "confirmation_required"
    assert get_mock_action_store().records() == []

    travel = _call(operational_mcp, "create_mock_travel_request", {
        "request_type": "personal_extension",
        "details": {"summary": "Personal extension"},
        "confirmed": False,
    })
    assert travel["status"] == "confirmation_required"
    assert get_mock_action_store().records() == []
