# Meridian Compass - Software Requirements Specification
Version 1.2

## Functional requirements
FR-01 Synthetic Enterprise Identity selector/login and server-side session context.
FR-02 Employee-facing chat UI.
FR-03 `POST /chat` returns the canonical fields defined below.
FR-04 `GET /health` reports application, MCP and RAG readiness.
FR-05 Agent interprets intent and selects RAG, MCP tools, clarification or safe insufficiency handling.
FR-06 Approved canonical Markdown is authoritative RAG input; duplicate representations are not double-indexed.
FR-07 Preserve document ID, title, type, topic, section and effective-date metadata where available.
FR-08 Retrieval top-k is configurable with baseline 5.
FR-09 Discover/invoke MCP tools through the configured MCP boundary.
FR-10 Orchestrator must not directly read MCP-owned operational JSON.
FR-11 Material MSG policy/procedure claims undergo grounding verification.
FR-12 Privacy uses authenticated identity; prompt text cannot override identity.
FR-13 Establish the supported approval role before resolving a named person.
FR-14 Missing evidence produces explicit insufficiency rather than inference.
FR-15 Consequential mock actions require confirmation and transient/resettable state.
FR-16 No internet/external policy/general model knowledge may establish Meridian policy.
FR-17 Logs/traces expose architectural events, not hidden chain-of-thought.

## Canonical `POST /chat` contract
Request:
```json
{"message":"string","session_id":"string","confirm_action":false}
```
Authenticated identity is resolved server-side.

Response fields are exactly:
```json
{
  "answer":"string",
  "status":"answered | insufficient_evidence | clarification_required | action_confirmation_required | forbidden | not_found | out_of_scope | tool_error",
  "citations":[],
  "source_snippets":[],
  "tool_trace":[]
}
```

`source_snippets` is separate from `citations`. `tool_trace` is canonical; `trace` is not an alternative public field.

## Canonical public statuses
- `answered`
- `insufficient_evidence`
- `clarification_required`
- `action_confirmation_required`
- `forbidden`
- `not_found`
- `out_of_scope`
- `tool_error`

## MCP/tool status -> public `/chat` status
| MCP/tool status or condition | Public status |
|---|---|
| `ok` with sufficient supported evidence | `answered` |
| `insufficient_evidence` | `insufficient_evidence` |
| `confirmation_required` | `action_confirmation_required` |
| `forbidden` | `forbidden` |
| `not_found` | `not_found` |
| `invalid_request` requiring user detail/correction | `clarification_required` |
| `dependency_unavailable` | `tool_error` |

Agent-only conditions:
- unrelated request -> `out_of_scope`
- unresolved ambiguity requiring user detail -> `clarification_required`
- insufficient company evidence -> `insufficient_evidence`

No additional status equivalences may be invented.

## Evaluation outcome -> public `/chat` status
Evaluation `expected_status` is an evaluation-layer outcome, not necessarily a literal API status.

| Evaluation outcome | Public status |
|---|---|
| `success` | `answered` |
| `context_dependent` | `answered` or `clarification_required`, according to controlled gold behavior |
| `forbidden` | `forbidden` |
| `insufficient_evidence` | `insufficient_evidence` |
| `insufficient_evidence_with_route` | `insufficient_evidence` |
| `out_of_scope` | `out_of_scope` |
| `confirmation_required` | `action_confirmation_required` |
| `not_found` | `not_found` |
| `error` | `tool_error` |

The evaluator must not create equivalences outside this table.

## `GET /health`
Healthy target:
```json
{"status":"healthy","application":"meridian-compass","mcp":"connected","rag":"ready"}
```

## Grounding, privacy and data
Enterprise Identity establishes WHO; authorised structured data establishes WHAT situation exists; policy establishes WHAT is permitted/required/prohibited; procedure establishes HOW.

Only approved Meridian corpus evidence and authorised structured data returned through approved MCP tools may establish MSG-specific facts. Ordinary employees may not obtain another employee's private HR information merely by supplying a name/ID. Baseline fixtures are immutable; mock mutations use transient/resettable state.

## RAG and MCP
Canonical approved Markdown is runtime corpus authority. Equivalent PDFs are alternate-format/validation artefacts and are not double-indexed. MCP tool names/responsibilities are controlled by the MCP Tool Contract and its controlled addenda. Hard-coded policy-decision tools that replace corpus-grounded interpretation are prohibited.

## Technology
Python, FastAPI, Pydantic, official MCP Python SDK, Streamable HTTP, Sentence Transformers, FAISS, pytest, Docker, GitHub Actions, Render-compatible deployment and environment-variable secrets.

## Version authority
This document is **Software Requirements Specification Version 1.2** and supersedes earlier SRS content where conflicting.
`02_evaluation_dataset_v1_2.json` is authoritative for evaluation.
The MCP Tool Contract plus v1.2 alignment addendum controls MCP tools.
The Codex Master Build Prompt v1.2 addendum supersedes conflicting earlier API/tool-name details.
Older evaluation datasets remain audit history only.

