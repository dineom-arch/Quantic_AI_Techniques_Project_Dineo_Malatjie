"""Assignment and explicitly requested approval-relationship tools."""

from typing import Any, Literal

from mcp.server.fastmcp import Context

from app.operational.repository import OperationalDataError, get_operational_repository
from app.operational.tool_support import parse_date, public_record, require_self


ApprovalRole = Literal[
    "engagement_manager", "line_manager", "engagement_partner", "designated_travel_approver"
]


def _person(repository, employee_id: str | None) -> dict[str, str] | None:
    employee = repository.employee(employee_id) if employee_id else None
    if employee is None:
        return None
    return {"display_name": employee.display_name, "job_title": employee.job_title}


def register_assignment_tools(server: Any, repository_provider=get_operational_repository) -> None:
    @server.tool()
    async def lookup_active_assignment(
        target: str, as_of: str, ctx: Context
    ) -> dict[str, object]:
        """Return assignment dates, status, location and recorded relationships only."""
        identity, failure = require_self(target, ctx)
        if failure:
            return failure
        as_of_date, failure = parse_date(as_of)
        if failure:
            return failure
        try:
            repository = repository_provider()
            assignment = repository.active_assignment(identity.employee_id, as_of_date)
            if assignment is None:
                return {"status": "not_found", "message": "Active assignment not found"}
            record = public_record(
                assignment,
                exclude={"employee_id", "engagement_manager_id", "engagement_partner_id", "charge_code"},
            )
            record["engagement_manager"] = _person(repository, assignment.engagement_manager_id)
            record["engagement_partner"] = _person(repository, assignment.engagement_partner_id)
        except OperationalDataError as exc:
            return {"status": "dependency_unavailable", "message": str(exc)}
        return {"status": "ok", "assignment": record, "data_source": "hr_operations.assignments"}

    @server.tool()
    async def resolve_approval_role(
        target: str,
        approval_role: ApprovalRole,
        ctx: Context,
        assignment_id: str | None = None,
    ) -> dict[str, object]:
        """Resolve a caller-established role; this tool never decides which role applies."""
        identity, failure = require_self(target, ctx)
        if failure:
            return failure
        if approval_role == "designated_travel_approver":
            return {
                "status": "not_found",
                "role": approval_role,
                "message": "No named designated travel approver is present in authorised data",
            }
        try:
            repository = repository_provider()
            employee = repository.employee(identity.employee_id)
            if employee is None:
                return {"status": "not_found", "role": approval_role, "message": "Employee not found"}
            if approval_role == "line_manager":
                person = _person(repository, employee.manager_id)
                source = "hr_operations.employees"
            else:
                assignment = repository.assignment(identity.employee_id, assignment_id)
                if assignment is None:
                    return {"status": "not_found", "role": approval_role, "message": "Assignment not found"}
                relationship_id = (
                    assignment.engagement_manager_id
                    if approval_role == "engagement_manager"
                    else assignment.engagement_partner_id
                )
                person = _person(repository, relationship_id)
                source = "hr_operations.assignments+employees"
        except OperationalDataError as exc:
            return {"status": "dependency_unavailable", "role": approval_role, "message": str(exc)}
        if person is None:
            return {"status": "not_found", "role": approval_role, "message": "Named person not found"}
        return {"status": "ok", "role": approval_role, **person, "data_source": source}

