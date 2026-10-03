"""Employee operational-fact tools with self-only privacy enforcement."""

from typing import Any

from mcp.server.fastmcp import Context

from app.operational.repository import OperationalDataError, get_operational_repository
from app.operational.tool_support import public_record, require_self


def register_employee_tools(server: Any, repository_provider=get_operational_repository) -> None:
    @server.tool()
    async def lookup_employee_profile(target: str, ctx: Context) -> dict[str, object]:
        """Return authenticated employee job and organisation facts; never policy."""
        identity, failure = require_self(target, ctx)
        if failure:
            return failure
        try:
            repository = repository_provider()
            employee = repository.employee(identity.employee_id)
            if employee is None:
                return {"status": "not_found", "message": "Employee profile not found"}
            manager = repository.employee(employee.manager_id) if employee.manager_id else None
        except OperationalDataError as exc:
            return {"status": "dependency_unavailable", "message": str(exc)}
        return {
            "status": "ok",
            "profile": public_record(employee, exclude={"employee_id", "manager_id"}),
            "manager": (
                {"display_name": manager.display_name, "job_title": manager.job_title}
                if manager else None
            ),
            "data_source": "hr_operations.employees",
        }

    @server.tool()
    async def check_pto_balance(target: str, ctx: Context) -> dict[str, object]:
        """Return the authenticated employee's recorded PTO balance."""
        identity, failure = require_self(target, ctx)
        if failure:
            return failure
        try:
            balance = repository_provider().pto(identity.employee_id)
        except OperationalDataError as exc:
            return {"status": "dependency_unavailable", "message": str(exc)}
        if balance is None:
            return {"status": "not_found", "message": "PTO record not found"}
        return {
            "status": "ok",
            "pto_balance": public_record(balance, exclude={"employee_id", "pto_record_id"}),
            "data_source": "hr_operations.pto_balances",
        }

    @server.tool()
    async def lookup_benefits_status(
        target: str, ctx: Context, benefit_type: str | None = None
    ) -> dict[str, object]:
        """Return recorded eligibility and enrollment fields without interpretation."""
        identity, failure = require_self(target, ctx)
        if failure:
            return failure
        try:
            benefits = repository_provider().employee_benefits(identity.employee_id, benefit_type)
        except OperationalDataError as exc:
            return {"status": "dependency_unavailable", "message": str(exc)}
        if not benefits:
            return {"status": "not_found", "benefits": [], "message": "Benefit record not found"}
        return {
            "status": "ok",
            "benefits": [public_record(x, exclude={"employee_id", "benefit_record_id"}) for x in benefits],
            "data_source": "hr_operations.benefits",
        }

