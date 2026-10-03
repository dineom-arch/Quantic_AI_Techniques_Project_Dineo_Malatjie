"""Validated models for the controlled HR operational fixtures."""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class FixtureModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Employee(FixtureModel):
    employee_id: str
    display_name: str
    job_title: str
    employee_group: str
    function: str
    home_office: str
    home_country: str
    manager_id: str | None
    employment_status: str


class PTOBalance(FixtureModel):
    pto_record_id: str
    employee_id: str
    leave_year: int
    entitlement_days: int
    used_days: int
    pending_days: int
    available_days: int
    last_updated: date


class Benefit(FixtureModel):
    benefit_record_id: str
    employee_id: str
    benefit_code: str
    benefit_name: str
    eligibility_status: str
    enrollment_status: str
    effective_date: date


class Assignment(FixtureModel):
    assignment_id: str
    employee_id: str
    client_name: str
    project_name: str
    location_city: str
    location_country: str
    start_date: date
    end_date: date
    status: str
    engagement_manager_id: str | None
    engagement_partner_id: str
    charge_code: str


class TravelAuthorization(FixtureModel):
    travel_authorization_id: str
    employee_id: str
    assignment_id: str | None
    origin_city: str
    origin_country: str
    destination_city: str
    destination_country: str
    departure_date: date
    business_return_date: date
    purpose: str
    scheduled_flight_duration_hours: float | None = None
    status: str
    approved_by: str
    approved_at: datetime


class PersonalExtensionProposal(FixtureModel):
    proposed_return_date: date
    alternative_return_fare: int
    incremental_employee_cost: int
    status: str


class TravelBooking(FixtureModel):
    booking_id: str
    employee_id: str
    travel_authorization_id: str
    assignment_id: str | None
    status: str
    origin_city: str
    destination_city: str
    departure_date: date
    return_date: date
    cabin_class: str
    currency: str
    business_return_fare: int
    hotel_name: str
    hotel_check_in: date
    hotel_check_out: date
    personal_extension_proposal: PersonalExtensionProposal | None


class ExpenseClaim(FixtureModel):
    expense_claim_id: str
    employee_id: str
    assignment_id: str | None
    travel_authorization_id: str | None
    expense_date: date
    category: str
    description: str
    amount: int
    currency: str
    receipt_attached: bool
    status: str


class PerDiemRate(FixtureModel):
    per_diem_rate_id: str
    country: str
    city: str
    currency: str
    daily_rate: int
    includes_meals: bool
    effective_date: date
    end_date: date | None


class HRTicket(FixtureModel):
    ticket_id: str
    employee_id: str
    category: str
    subject: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
