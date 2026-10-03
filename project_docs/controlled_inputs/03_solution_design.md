# Meridian Compass — Solution Design
Version 1.0

## Logical architecture
Employee -> Enterprise Identity -> Web/FastAPI -> Agent Orchestrator -> MCP Client.
MCP Client <-> Streamable HTTP <-> MCP Server -> RAG tools and structured/mock tools.
RAG -> embeddings -> FAISS -> approved corpus.
External LLM provider is accessed through an abstraction.

## Deployment
One Docker container may physically co-locate web/API, orchestrator, MCP client/server, RAG/index and synthetic-data services while preserving logical boundaries. LLM provider remains external.

## Frozen repository/module layout
Repository: `Quantic_AI_Techniques_Project_Dineo_Malatjie`

```text
app/
  main.py
  api/chat.py health.py auth.py
  identity/provider.py session.py models.py
  agent/orchestrator.py planner.py context.py guardrails.py grounding.py traces.py
  llm/provider.py prompts.py
  web/templates/ web/static/
mcp/
  server.py client.py
  tools/knowledge.py employee.py assignment.py travel.py expenses.py actions.py
rag/
  loaders.py cleaner.py chunker.py embeddings.py index.py retriever.py citations.py
knowledge/
data/identity/
mock_data/hr_operations/
evaluation/
tests/
scripts/
.github/workflows/
```

Do not substitute `mcp_server/`, move RAG under `app/`, or adopt another competing high-level layout without explicit human approval.

## RAG
Canonical Markdown is authoritative. PDFs are alternate-format/page-verification artefacts and must not be indexed alongside identical Markdown as duplicate authority. Chunk by semantic section with metadata. Baseline k=5; evaluate 3/5/8.

## Approval resolution
Authenticated identity -> employee -> operational relationship -> corpus-supported approval role -> named person only if authorised data supports the relationship. If role is supported but a person cannot be resolved, return the role and say the named approver cannot be resolved.

## Trace
Expose intent category, retrieved sources, MCP tool/status, safe arguments/output summary, grounding result and final basis. Never expose hidden chain-of-thought.
