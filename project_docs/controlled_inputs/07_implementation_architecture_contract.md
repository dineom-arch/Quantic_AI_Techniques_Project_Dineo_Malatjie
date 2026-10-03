# Meridian Compass — Implementation Architecture Contract
Version 1.0

## Repository and structure
Exact repository/project folder: `Quantic_AI_Techniques_Project_Dineo_Malatjie`. Product: Meridian Compass.

Use the module layout frozen in `03_solution_design.md`: top-level `app/`, `mcp/`, `rag/`, `evaluation/`, `tests/`, `scripts/`, `.github/workflows/`. Do not replace `mcp/` with `mcp_server/` or move `rag/` beneath `app/` without human approval.

## LLM provider
Provider abstraction configured by `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`. Provider-specific business logic must not enter orchestration.

## Environment
`APP_ENV`, `PORT`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `VECTOR_STORE_PATH`, `KNOWLEDGE_DATA_PATH`, `MOCK_DATA_PATH`, `MCP_TRANSPORT`, `LOG_LEVEL`.
`.env` ignored; `.env.example` placeholders only. Container default `MOCK_DATA_PATH=/app/mock_data`.

## Session
Demo UI selects a synthetic Enterprise Identity and establishes server-side session context. Employee IDs are not normal user input.

## Grounding verification
Material company-specific policy/procedure claims must map to retrieved corpus evidence; operational facts must map to authorised tool results. Unsupported material claims are removed or converted to explicit insufficiency. This is evidence bookkeeping, not hidden reasoning exposure.

## Citations
`document_id`, `title`, `section`, `snippet`. Retrieval scores/chunk IDs stay in technical trace.

## Mock actions
Use in-memory/temp generated state ignored by Git and provide reset support. Baseline fixtures remain immutable.

## CI/deployment
Single Docker container baseline, binding `0.0.0.0:${PORT}`.
CI on push/PR: install -> tests -> controlled-input validation -> RAG smoke -> MCP discovery -> safe MCP call -> Docker build -> container start -> `/health`.
Deployment is separate and follows successful verification.

## Evaluation
Case-level `metrics` are targeted annotations, not the complete metric universe. The evaluator computes all globally required metrics. Plausible but unsupported Meridian claims fail.
