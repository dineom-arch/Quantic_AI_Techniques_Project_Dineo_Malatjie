"""Travel and per-diem operational-fact tools."""

from typing import Any

from mcp.server.fastmcp import Context

from app.operational.repository import OperationalDataError, get_operational_repository
from app.operational.tool_support import parse_date, public_record, require_self


def register_travel_tools(server: Any, repository_provider=get_operational_repository) -> None:
    @server.tool()
    async def lookup_travel_authorization(
        target: str,
        ctx: Context,
        travel_authorization_id: str | None = None,
        assignment_id: str | None = None,
    ) -> dict[str, object]:
        """Return matching authorised travel facts; historical approver is not exposed."""
        identity, failure = require_self(target, ctx)
        if failure:
            return failure
        try:
            record = repository_provider().travel_authorization(
                identity.employee_id, travel_authorization_id, assignment_id
            )
        except OperationalDataError as exc:
            return {"status": "dependency_unavailable", "message": str(exc)}
        if record is None:
            return {"status": "not_found", "message": "Travel authorization not found"}
        return {
            "status": "ok",
            "travel_authorization": public_record(record, exclude={"employee_id", "approved_by"}),
            "data_source": "hr_operations.travel_authorizations",
        }

    @server.tool()
    async def get_mock_travel_booking(
        target: str,
        ctx: Context,
        booking_id: str | None = None,
        travel_authorization_id: str | None = None,
    ) -> dict[str, object]:
        """Return baseline booking and proposed-extension facts; never a permission conclusion."""
        identity, failure = require_self(target, ctx)
        if failure:
            return failure
        try:
            record = repository_provider().travel_booking(
                identity.employee_id, booking_id, travel_authorization_id
            )
        except OperationalDataError as exc:
            return {"status": "dependency_unavailable", "message": str(exc)}
        if record is None:
            return {"status": "not_found", "message": "Travel booking not found"}
        return {
            "status": "ok",
            "booking": public_record(record),
            "data_source": "hr_operations.travel_bookings",
        }

    @server.tool()
    async def get_per_diem_rate(
        country: str, city: str, as_of: str
    ) -> dict[str, object]:
        """Return the effective location rate, without deciding entitlement or eligibility."""
        if not country.strip() or not city.strip():
            return {"status": "invalid_request", "message": "country and city are required"}
        as_of_date, failure = parse_date(as_of)
        if failure:
            return failure
        try:
            rate = repository_provider().per_diem(country, city, as_of_date)
        except OperationalDataError as exc:
            return {"status": "dependency_unavailable", "message": str(exc)}
        if rate is None:
            return {"status": "not_found", "message": "Per diem rate not found"}
        return {
            "status": "ok",
            "per_diem_rate": public_record(rate, exclude={"per_diem_rate_id"}),
            "data_source": "hr_operations.per_diem_rates",
        }

