"""Expense operational-fact tools."""

from typing import Any

from mcp.server.fastmcp import Context

from app.operational.repository import OperationalDataError, get_operational_repository
from app.operational.tool_support import public_record, require_self


def register_expense_tools(server: Any, repository_provider=get_operational_repository) -> None:
    @server.tool()
    async def get_mock_expense_claim(
        target: str, expense_id: str, ctx: Context
    ) -> dict[str, object]:
        """Return a matching expense record, without reimbursement interpretation."""
        identity, failure = require_self(target, ctx)
        if failure:
            return failure
        if not expense_id.strip():
            return {"status": "invalid_request", "message": "expense_id is required"}
        try:
            claim = repository_provider().expense(identity.employee_id, expense_id)
        except OperationalDataError as exc:
            return {"status": "dependency_unavailable", "message": str(exc)}
        if claim is None:
            return {"status": "not_found", "message": "Expense claim not found"}
        return {
            "status": "ok",
            "expense_claim": public_record(claim),
            "data_source": "hr_operations.expense_claims",
        }

