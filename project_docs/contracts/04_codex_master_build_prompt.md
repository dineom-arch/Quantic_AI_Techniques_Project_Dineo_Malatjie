# Meridian Compass — Codex Master Build Prompt
Version 2.0 — Final Handover Prompt
## Repository identity
The required repository name is `Quantic_AI_Techniques_Project_Dineo_Malatjie`. Preserve this exact repository/project-folder name. The product/application name is Meridian Compass.


You are the primary implementation engineer for Meridian Compass, an agentic People & Travel Operations assistant for the fictional Meridian Strategy Group.

THIS IS AN IMPLEMENTATION TASK, NOT A REDESIGN TASK.

Before modifying code, inspect the entire repository and all supplied project artefacts. Produce a short implementation plan mapped to the existing repository. Then implement in controlled phases and run relevant tests after every phase.

## Authoritative artefacts
Treat the supplied BRS, SRS, Solution Design, Domain/Policy/Procedure Specification, Synthetic Data Package, approved Knowledge Corpus, MCP Tool Contract, Agent & Grounding Contract and Evaluation Dataset as controlled implementation inputs.

Do not invent or change business rules, data fixtures, approval logic, privacy rules, escalation routes or corpus content merely to make implementation easier.

If artefacts conflict, stop and report the conflict. Do not silently reconcile it using general knowledge.

## Pre-build blocking checks
1. Confirm the repository uses `data/identity/` for simulated Enterprise Identity and `mock_data/hr_operations/` for operational fixtures.
2. Confirm MSG-PROC-003 explicitly states:
   - active client assignment personal extension -> Engagement Manager approval before itinerary modification;
   - authorised business travel not tied to active client assignment -> designated travel approver;
   - extension containing a working day -> separate PTO approval.
   If the canonical corpus does not contain this approved rule, report it as a blocking corpus correction. Do not silently insert a new rule into application code.
3. Measure the canonical corpus page-equivalent/actual rendered page count. The coursework corpus must ultimately be 30–120 pages. If below 30 pages, report a corpus-readiness blocker. Do not pad or invent policy content.

## Architecture
Preserve:
Enterprise Identity -> FastAPI web/API -> explicit Python Agent Orchestrator -> MCP Client -> Streamable HTTP -> MCP Server -> RAG/structured-data tools.
External LLM access is through a provider abstraction.
Use Sentence Transformers baseline `all-MiniLM-L6-v2`, FAISS, pytest, Docker, GitHub Actions and Render configuration.

Logical separation does not require physical separation: components may run in one container while retaining explicit module and protocol boundaries.

## Closed-corpus rule
Only authenticated Enterprise Identity, approved Meridian corpus evidence and authorised structured company data returned by approved MCP tools may establish Meridian-specific facts.

NO WEB SEARCH.
NO external company policies.
NO general corporate practice as policy.
NO pretrained model knowledge as Meridian policy.
NO user assertion as a substitute for policy.
NO invented approval or escalation route.

If evidence is insufficient, the system must say so.

## MCP
Implement the supplied MCP Tool Contract using the official MCP Python SDK and Streamable HTTP.
The orchestrator must genuinely use MCP discovery/invocation for MCP-defined capabilities. Do not bypass MCP by directly reading operational JSON from the orchestrator.

## RAG
Load approved Markdown and PDF formats while preventing duplicate authoritative representations from being indexed twice.
Use section-aware chunking and preserve document_id, title, document_type, topic, section and effective_date.
Use FAISS and configurable top-k; baseline k=5.
Citations must come from retrieved metadata.
Policy establishes WHAT; procedure establishes HOW. A procedure cannot create substantive eligibility.

## Agent
Implement explicit orchestration:
authenticate -> classify -> identify facts/authority -> discover/call MCP -> retrieve -> assess evidence -> resolve relationships -> clarify if necessary -> synthesise -> claim/evidence verification -> return.

Do not expose hidden chain-of-thought. Expose only concise architectural trace.

## Identity/privacy
Authenticated session identity cannot be overridden by prompt text.
Employee IDs are internal relational keys and should not normally appear in the primary UI.
Enforce cross-employee privacy at multiple layers.

## Actions
All actions are simulated. Information questions must not trigger actions. Consequential mock actions require explicit confirmation. Baseline fixture files remain immutable/resettable.

## API/UI
Implement POST /chat and GET /health.
`/chat` returns answer, citations, source_snippets, tool_trace and status.
`/health` must meaningfully report app, MCP and RAG readiness.
Create an enterprise employee-facing UI with synthetic identity selection, chat, sources and expandable "View sources and system trace".

## Docker/deployment
Use one reproducible Docker architecture for local, CI and Render.
Bind 0.0.0.0:${PORT}.
Use environment variables and never commit secrets.

## CI
On push/PR: install -> tests -> RAG verification -> MCP discovery -> safe MCP call -> Docker build -> container start -> /health.
Deployment must depend on successful checks.

## Evaluation
Implement the supplied 30-case evaluation dataset rather than replacing it with convenient tests.
Measure groundedness, citation accuracy, policy applicability, procedural completeness, approval accuracy, tool selection, workflow completion, clarification/escalation, action safety, unsupported-claim rate and p50/p95 latency.
Run k=3/5/8 retrieval ablation.
Run the security-policy removal ablation and verify that the agent stops supplying unsupported security rules.

## Implementation phases
1. Inspect repo and report gaps/blockers.
2. Scaffolding/config/schema validation.
3. Enterprise Identity/session.
4. Synthetic data validation.
5. RAG ingestion/index/retrieval/citations.
6. MCP server/tools/discovery.
7. MCP client.
8. Agent/context/guardrails/grounding.
9. API/UI.
10. Tests.
11. Docker/CI.
12. Evaluation.
13. Render configuration.
14. Documentation alignment.

Run tests after each phase. Fix failures before moving forward unless the failure is a documented external blocker.

## Do not do
- Do not redesign frozen business rules.
- Do not add web-search capability.
- Do not let the orchestrator bypass MCP.
- Do not hard-code demo answers.
- Do not encode undocumented policy inside eligibility tools.
- Do not expose private colleague data.
- Do not expose hidden chain-of-thought.
- Do not permanently mutate baseline mock data.
- Do not fabricate missing records.
- Do not fabricate citations.
- Do not claim deployment/tests succeeded unless actually verified.

## Completion report
At completion report:
- repository tree;
- files added/changed;
- architecture implemented;
- MCP tools discovered;
- tests and exact results;
- Docker verification;
- RAG verification;
- evaluation summary;
- deployment status;
- specification deviations;
- known limitations;
- unresolved blockers.

If a frozen requirement is impossible or contradictory, stop at that boundary and report it rather than inventing a substitute.
