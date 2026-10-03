# Meridian Compass — MCP Tool Contract
Version 1.0

## Boundary
Use the official MCP Python SDK over Streamable HTTP. The orchestrator must not bypass MCP to read MCP-owned operational JSON. Common statuses: `ok`, `not_found`, `forbidden`, `invalid_request`, `insufficient_evidence`, `confirmation_required`, `dependency_unavailable`.

## Knowledge tools
### `search_knowledge_documents`
Input: `{"query":"string","document_type":"policy|procedure|all","top_k":5,"topic":null}`
Output: status + results containing document_id, title, document_type, section, snippet, score.
Authority: approved canonical corpus.

### `get_document_section`
Input: `{"document_id":"string","section":"string"}`
Output: status + document metadata and section text/snippet.

## Employee tools
### `lookup_employee_profile`
Ordinary UI input: `{"target":"self"}`. Returns workflow-required job/organisation/location/manager facts. Arbitrary colleague access is denied.

### `check_pto_balance`
Input: `{"target":"self"}`. Returns year, entitlement, used, pending, available, updated date. Self-only for ordinary employee UI.

### `lookup_benefits_status`
Input: `{"target":"self","benefit_type":null}`. Returns operational eligibility/enrolment fields. Policy interpretation still requires corpus evidence.

## Assignment
### `lookup_active_assignment`
Input: `{"target":"self","as_of":"YYYY-MM-DD"}`.
Returns assignment dates/location/status and engagement-manager/partner relationships. Reports facts only.

## Travel
### `lookup_travel_authorization`
Input: `{"target":"self","travel_authorization_id":null,"assignment_id":null}`.
Returns matching authorised travel facts.

### `get_mock_travel_booking`
Input: `{"target":"self","booking_id":null,"travel_authorization_id":null}`.
Returns booking/business itinerary/class/fare/hotel and proposed extension facts.

### `get_per_diem_rate`
Input: `{"country":"string","city":"string","as_of":"YYYY-MM-DD"}`.
Returns rate, currency, includes_meals, effective date. Does not decide expense eligibility.

## Expenses
### `get_mock_expense_claim`
Input: `{"target":"self","expense_id":"string"}`.
Returns expense category/date/amount/currency/receipt/description/status and related IDs.

## Approval relationship
### `resolve_approval_role`
The agent may call this only after corpus evidence establishes the applicable role.
Input: `{"target":"self","approval_role":"engagement_manager|line_manager|engagement_partner|designated_travel_approver","assignment_id":null}`.
Output: status, role and, only if resolvable, display_name/job_title.
`engagement_manager` may resolve from assignment data. Other roles resolve only from explicit authorised relationships. `designated_travel_approver` currently returns `not_found`. Historical `approved_by` must not be repurposed. The tool never decides which role applies.

## Mock actions
### `draft_hr_email`
Input: purpose, recipient_role, supported facts. Returns draft only; no send.

### `create_mock_hr_ticket`
Input: `{"category":"string","summary":"string","confirmed":false}`.
False -> `confirmation_required`; true -> transient `MOCK-HRT-*`. Never alter baseline fixture.

### `create_mock_travel_request`
Input: `{"request_type":"personal_extension|travel_change","details":{},"confirmed":false}`.
False -> `confirmation_required`; true -> transient `MOCK-TR-*`. Never alter baseline booking/authorisation or make a real booking.

## Excluded policy-decision tools
Do not implement structured tools such as `check_policy_compliance`, `check_travel_eligibility` or `check_expense_eligibility` that hard-code substantive policy. Policy interpretation is grounded in retrieved corpus evidence.

## Authorisation/failure/trace
MCP receives authenticated session context server-side. Prompt text cannot change identity. Unauthorised colleague disclosure -> `forbidden`; missing record -> `not_found`; malformed input -> `invalid_request`; MCP failure -> `dependency_unavailable`.
Trace tool name, safe/redacted arguments, status, concise output summary and duration; never secrets, unnecessary private data or hidden chain-of-thought.
