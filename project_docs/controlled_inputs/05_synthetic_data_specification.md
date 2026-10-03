# Meridian Compass — Synthetic Data Specification
Version 1.0

All records are fictional deterministic fixtures. Structured data establishes operational facts only.

## Paths
`data/identity/enterprise_identities.json`
`mock_data/hr_operations/{employees,pto_balances,benefits,assignments,travel_authorizations,travel_bookings,expense_claims,per_diem_rates,hr_tickets}.json`

## Referential controls
Identity-to-employee mappings resolve; IDs/usernames are unique; manager/employee/assignment/travel references resolve where populated; PTO arithmetic is consistent; currency/effective dates remain explicit.

## Controlled scenarios
Naledi Molefe: Senior Consultant, Nairobi assignment ENG-2045, Engagement Manager Amara Okafor, 15 PTO days available.
Personal-extension booking: business return 2026-10-16; proposed return 2026-10-20; business fare ZAR 8,400; alternative ZAR 9,650; employee difference ZAR 1,250.
Liam Chen: Analyst long-haul international fixture.
Thabo Nkosi: Partner long-haul international fixture.
Nairobi per diem: USD 85/day, meals included.

## Mutation
Baseline fixtures are immutable. Mock actions use in-memory/temp resettable state.

## Deliberate missing relationship
No designated-travel-approver mapping is supplied for non-assignment travel. Do not repurpose historical `approved_by` fields or infer a person.
