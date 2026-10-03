"""Deterministic, read-only repository over controlled JSON fixtures."""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter, ValidationError

from app.config import get_settings
from app.operational.models import (
    Assignment,
    Benefit,
    Employee,
    ExpenseClaim,
    HRTicket,
    PTOBalance,
    PerDiemRate,
    TravelAuthorization,
    TravelBooking,
)


RecordT = TypeVar("RecordT", bound=BaseModel)


class OperationalDataError(RuntimeError):
    """The controlled operational dependency is unavailable or invalid."""


class OperationalRepository:
    """Loads each immutable baseline fixture once and exposes factual lookups."""

    def __init__(self, fixture_directory: Path) -> None:
        self.fixture_directory = Path(fixture_directory)
        self.employees = self._load("employees.json", Employee)
        self.pto_balances = self._load("pto_balances.json", PTOBalance)
        self.benefits = self._load("benefits.json", Benefit)
        self.assignments = self._load("assignments.json", Assignment)
        self.travel_authorizations = self._load(
            "travel_authorizations.json", TravelAuthorization
        )
        self.travel_bookings = self._load("travel_bookings.json", TravelBooking)
        self.expense_claims = self._load("expense_claims.json", ExpenseClaim)
        self.per_diem_rates = self._load("per_diem_rates.json", PerDiemRate)
        self.hr_tickets = self._load("hr_tickets.json", HRTicket)
        self._employees_by_id = {item.employee_id: item for item in self.employees}
        if len(self._employees_by_id) != len(self.employees):
            raise OperationalDataError("Employee IDs must be unique")
        self._validate_references()

    def _load(self, filename: str, model: type[RecordT]) -> tuple[RecordT, ...]:
        path = self.fixture_directory / filename
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise OperationalDataError(
                f"Required operational fixture unavailable: {filename}"
            ) from exc
        try:
            raw = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OperationalDataError(
                f"Malformed operational fixture: {filename}"
            ) from exc
        try:
            records = TypeAdapter(list[model]).validate_python(raw)  # type: ignore[valid-type]
        except ValidationError as exc:
            raise OperationalDataError(
                f"Invalid operational fixture structure: {filename}"
            ) from exc
        return tuple(records)

    def _validate_references(self) -> None:
        employee_ids = set(self._employees_by_id)
        assignment_ids = {item.assignment_id for item in self.assignments}
        authorization_ids = {
            item.travel_authorization_id for item in self.travel_authorizations
        }
        referenced_employee_ids = {
            *(item.employee_id for item in self.pto_balances),
            *(item.employee_id for item in self.benefits),
            *(item.employee_id for item in self.assignments),
            *(item.employee_id for item in self.travel_authorizations),
            *(item.employee_id for item in self.travel_bookings),
            *(item.employee_id for item in self.expense_claims),
            *(item.employee_id for item in self.hr_tickets),
            *(item.manager_id for item in self.employees if item.manager_id),
            *(item.engagement_manager_id for item in self.assignments if item.engagement_manager_id),
            *(item.engagement_partner_id for item in self.assignments),
            *(item.approved_by for item in self.travel_authorizations),
        }
        missing_employees = referenced_employee_ids - employee_ids
        if missing_employees:
            raise OperationalDataError(
                f"Broken employee references: {', '.join(sorted(missing_employees))}"
            )
        for record in self.travel_authorizations:
            if record.assignment_id and record.assignment_id not in assignment_ids:
                raise OperationalDataError(
                    f"Broken assignment reference: {record.assignment_id}"
                )
        for record in self.travel_bookings:
            if record.travel_authorization_id not in authorization_ids:
                raise OperationalDataError(
                    f"Broken travel authorization reference: {record.travel_authorization_id}"
                )
            if record.assignment_id and record.assignment_id not in assignment_ids:
                raise OperationalDataError(
                    f"Broken assignment reference: {record.assignment_id}"
                )
        for record in self.expense_claims:
            if record.travel_authorization_id and record.travel_authorization_id not in authorization_ids:
                raise OperationalDataError(
                    f"Broken travel authorization reference: {record.travel_authorization_id}"
                )
            if record.assignment_id and record.assignment_id not in assignment_ids:
                raise OperationalDataError(
                    f"Broken assignment reference: {record.assignment_id}"
                )

    def employee(self, employee_id: str) -> Employee | None:
        return self._employees_by_id.get(employee_id)

    def pto(self, employee_id: str) -> PTOBalance | None:
        return next((x for x in self.pto_balances if x.employee_id == employee_id), None)

    def employee_benefits(self, employee_id: str, benefit_type: str | None) -> list[Benefit]:
        matches = [x for x in self.benefits if x.employee_id == employee_id]
        if benefit_type:
            value = benefit_type.casefold()
            matches = [
                x for x in matches
                if value in {x.benefit_code.casefold(), x.benefit_name.casefold()}
            ]
        return matches

    def active_assignment(self, employee_id: str, as_of: date) -> Assignment | None:
        return next(
            (
                x for x in self.assignments
                if x.employee_id == employee_id
                and x.status == "active"
                and x.start_date <= as_of <= x.end_date
            ),
            None,
        )

    def assignment(self, employee_id: str, assignment_id: str | None) -> Assignment | None:
        matches = [x for x in self.assignments if x.employee_id == employee_id]
        if assignment_id:
            matches = [x for x in matches if x.assignment_id == assignment_id]
        return matches[0] if len(matches) == 1 else None

    def travel_authorization(
        self, employee_id: str, authorization_id: str | None, assignment_id: str | None
    ) -> TravelAuthorization | None:
        matches = [x for x in self.travel_authorizations if x.employee_id == employee_id]
        if authorization_id:
            matches = [x for x in matches if x.travel_authorization_id == authorization_id]
        if assignment_id:
            matches = [x for x in matches if x.assignment_id == assignment_id]
        return matches[0] if len(matches) == 1 else None

    def travel_booking(
        self, employee_id: str, booking_id: str | None, authorization_id: str | None
    ) -> TravelBooking | None:
        matches = [x for x in self.travel_bookings if x.employee_id == employee_id]
        if booking_id:
            matches = [x for x in matches if x.booking_id == booking_id]
        if authorization_id:
            matches = [x for x in matches if x.travel_authorization_id == authorization_id]
        return matches[0] if len(matches) == 1 else None

    def expense(self, employee_id: str, expense_id: str) -> ExpenseClaim | None:
        return next(
            (x for x in self.expense_claims if x.employee_id == employee_id and x.expense_claim_id == expense_id),
            None,
        )

    def per_diem(self, country: str, city: str, as_of: date) -> PerDiemRate | None:
        return next(
            (
                x for x in self.per_diem_rates
                if x.country.casefold() == country.casefold()
                and x.city.casefold() == city.casefold()
                and x.effective_date <= as_of
                and (x.end_date is None or as_of <= x.end_date)
            ),
            None,
        )


@lru_cache(maxsize=None)
def _repository_for_path(directory: Path) -> OperationalRepository:
    """Cache repositories by canonical operational-fixture directory."""

    return OperationalRepository(directory)


def get_operational_repository() -> OperationalRepository:
    """Resolve current configuration before consulting the path-keyed cache."""

    directory = (get_settings().mock_data_path / "hr_operations").resolve()
    return _repository_for_path(directory)
