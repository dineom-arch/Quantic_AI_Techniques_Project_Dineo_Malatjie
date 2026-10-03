"""Demonstration-only MCP actions with session-bound confirmation gates."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.actions.store import MockActionStore, get_mock_action_store
from app.operational.tool_support import resolve_session


def _text(value: str, field_name: str) -> tuple[str | None, dict[str, object] | None]:
    cleaned = value.strip() if isinstance(value, str) else ""
    if not cleaned:
        return None, {"status": "invalid_request", "message": f"{field_name} is required"}
    return cleaned, None


def register_action_tools(server: Any, store_provider=get_mock_action_store) -> None:
    @server.tool()
    async def draft_hr_email(
        purpose: str, recipient_role: str, supported_facts: list[str], ctx: Context,
    ) -> dict[str, object]:
        """Create a non-sending HR/support email draft from supplied supported facts."""
        session_id, identity = resolve_session(ctx)
        if identity is None or session_id is None:
            return {"status": "forbidden", "message": "Authenticated session required"}
        purpose_value, failure = _text(purpose, "purpose")
        if failure:
            return failure
        role_value, failure = _text(recipient_role, "recipient_role")
        if failure:
            return failure
        facts = [str(item).strip() for item in supported_facts if str(item).strip()]
        if not facts:
            return {"status": "invalid_request", "message": "supported_facts are required"}
        return {
            "status": "ok",
            "draft": {
                "recipient_role": role_value,
                "subject": f"Support request: {purpose_value}",
                "body": f"Hello {role_value},\n\nI am requesting support regarding {purpose_value}. "
                f"Relevant verified information: {'; '.join(facts)}.\n\nRegards,\n{identity.display_name}",
                "status": "draft",
            },
            "message": "Draft created only; no email was sent.",
            "data_source": "runtime.mock_actions",
        }

    @server.tool()
    async def create_mock_hr_ticket(
        category: str, summary: str, confirmed: bool, ctx: Context,
    ) -> dict[str, object]:
        """Propose or create one transient mock support ticket; never a real ticket."""
        session_id, identity = resolve_session(ctx)
        if identity is None or session_id is None:
            return {"status": "forbidden", "message": "Authenticated session required"}
        category_value, failure = _text(category, "category")
        if failure:
            return failure
        summary_value, failure = _text(summary, "summary")
        if failure:
            return failure
        store: MockActionStore = store_provider()
        arguments = {"category": category_value, "summary": summary_value}
        if not confirmed:
            store.propose(
                session_id=session_id, employee_id=identity.employee_id,
                action_name="create_mock_hr_ticket", arguments=arguments,
            )
            return {
                "status": "confirmation_required", "action": "create_mock_hr_ticket",
                "message": "A mock support ticket is ready. Explicit confirmation is required.",
                "data_source": "runtime.mock_actions",
            }
        record = store.complete(
            session_id=session_id, employee_id=identity.employee_id,
            action_name="create_mock_hr_ticket",
        )
        if record is None:
            return {
                "status": "invalid_request",
                "message": "No matching pending mock support ticket exists for this session.",
            }
        return {
            "status": "ok", "mock_ticket_reference": record["reference"],
            "category": record["category"], "summary": record["summary"],
            "status_detail": record["status"], "created_at": record["created_at"],
            "message": "Mock ticket created; no enterprise ticketing system was contacted.",
            "data_source": "runtime.mock_actions",
        }

    @server.tool()
    async def create_mock_travel_request(
        request_type: str, details: dict[str, object], confirmed: bool, ctx: Context,
    ) -> dict[str, object]:
        """Propose or create a transient mock request; never a booking or approval."""
        session_id, identity = resolve_session(ctx)
        if identity is None or session_id is None:
            return {"status": "forbidden", "message": "Authenticated session required"}
        if request_type not in {"personal_extension", "travel_change"}:
            return {"status": "invalid_request", "message": "Unsupported request_type"}
        store: MockActionStore = store_provider()
        if not confirmed:
            if not isinstance(details, dict) or not details:
                return {"status": "invalid_request", "message": "details are required"}
            store.propose(
                session_id=session_id, employee_id=identity.employee_id,
                action_name="create_mock_travel_request",
                arguments={"request_type": request_type, **details},
            )
            return {
                "status": "confirmation_required", "action": "create_mock_travel_request",
                "message": "A mock travel request is ready. Explicit confirmation is required.",
                "data_source": "runtime.mock_actions",
            }
        record = store.complete(
            session_id=session_id, employee_id=identity.employee_id,
            action_name="create_mock_travel_request",
            expected_request_type=request_type,
        )
        if record is None:
            return {
                "status": "invalid_request",
                "message": "No matching pending mock travel request exists for this session.",
            }
        return {
            "status": "ok", "mock_request_reference": record["reference"],
            "request_type": record["request_type"], "summary": record.get("summary"),
            "approval_role": record.get("approval_role"),
            "approval_person": record.get("approval_person"),
            "status_detail": record["status"], "created_at": record["created_at"],
            "message": "Mock request created; this is not a booking or approval.",
            "data_source": "runtime.mock_actions",
        }

