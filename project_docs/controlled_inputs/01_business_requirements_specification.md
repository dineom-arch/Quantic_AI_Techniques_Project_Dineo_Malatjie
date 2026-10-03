# Meridian Compass — Business Requirements Specification
Version 1.0

## Purpose and business problem
Meridian Compass is a fictional internal employee assistant for Meridian Strategy Group (MSG). It combines approved internal policy/procedure evidence with authorised synthetic operational facts so authenticated employees can understand what applies to their situation, the supported approval path and next steps.

## Authority model
Enterprise Identity establishes **who** the user is. Structured operational data establishes **what situation exists**. Policy establishes **what is permitted, required or prohibited**. Procedure establishes **how the supported process is carried out**. General model knowledge, internet search, other companies' practices and user assertions are not authoritative MSG evidence.

## Business requirements
BR-01 Authenticate/simulate Enterprise Identity before employee-specific processing.
BR-02 Resolve self-service context from authenticated identity, not a typed employee ID.
BR-03 Retrieve approved policy/procedure evidence for material company claims.
BR-04 Access structured operational facts only through approved MCP operations.
BR-05 Support multiple multi-step people/travel workflows.
BR-06 Protect another employee's private information.
BR-07 Cite relevant internal document ID/title/section/snippet.
BR-08 Expose a concise architectural tool/source trace, not hidden chain-of-thought.
BR-09 Require explicit confirmation before consequential mock actions.
BR-10 Never perform real bookings, HR changes or financial actions.
BR-11 Fail safely when evidence/data is insufficient.
BR-12 Run reproducibly locally, in Docker, CI and free-tier deployment.
BR-13 Evaluate grounding, citations, tool behaviour, safety and latency.
BR-14 Keep controlled fixtures immutable and mock-action state transient/resettable.

## Primary workflows
1. International-assignment PTO.
2. Role-aware business travel entitlement.
3. PTO plus personal travel extension.
4. Expense/per-diem reconciliation.

## Success
The implementation must use a real MCP client/server boundary, grounded RAG evidence, privacy controls, citations, safe traces and controlled evaluation without inventing missing company rules.
