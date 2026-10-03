# Meridian Compass — Software Requirements Specification
Version 1.0

## Functional requirements
FR-01 Synthetic Enterprise Identity selector/login and server-side session context.
FR-02 Employee-facing chat UI.
FR-03 `POST /chat` returns answer, status, citations/snippets and concise architectural trace.
FR-04 `GET /health` reports application, MCP and RAG readiness.
FR-05 Agent classifies intent and selects RAG/tools.
FR-06 Canonical approved Markdown is authoritative RAG input; duplicate representations are not double-indexed.
FR-07 Preserve document ID/title/type/topic/section/effective-date metadata.
FR-08 Baseline retrieval top-k=5 and configurable.
FR-09 Discover/invoke MCP tools over the configured protocol boundary.
FR-10 Orchestrator must not directly read MCP-owned operational JSON.
FR-11 Material policy/procedure claims undergo grounding verification.
FR-12 Privacy uses authenticated identity; prompt identity overrides are rejected.
FR-13 Establish supported approval role before resolving a named person.
FR-14 Missing evidence produces explicit insufficiency, not inference.
FR-15 Consequential mock actions require confirmation and transient storage.
FR-16 No internet/web-search capability for Meridian policy answers.
FR-17 Logs contain architectural events, not hidden reasoning.

## API
`POST /chat` request: `{"message":"string","session_id":"string","confirm_action":false}`.
Identity is resolved server-side.
Response fields: `answer`, `status`, `citations[]`, `trace[]`.
Statuses: `answered`, `insufficient_evidence`, `clarification_required`, `action_confirmation_required`, `tool_error`.

Healthy `/health` target:
`{"status":"healthy","application":"meridian-compass","mcp":"connected","rag":"ready"}`.

## Non-functional
Python, FastAPI, Pydantic, official MCP Python SDK, Streamable HTTP, Sentence Transformers, FAISS, pytest, Docker, GitHub Actions, Render-compatible deployment and environment-variable secrets.
