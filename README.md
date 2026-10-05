# Meridian Compass

**People & Travel Operations Assistant for Meridian Strategy Group
(MSG)**

Meridian Compass is a deployed agentic HR and travel operations
assistant built for the Quantic MSc AI Engineering course. It combines
simulated Enterprise Identity, retrieval-augmented generation (RAG),
authorised synthetic operational data, MCP tools, deterministic
grounding checks and an LLM to return employee-specific, cited next
steps.

## Deployed application

Application: https://quantic-ai-techniques-project-dineo.onrender.com

Health: https://quantic-ai-techniques-project-dineo.onrender.com/health

Repository:
https://github.com/dineom-arch/Quantic_AI_Techniques_Project_Dineo_Malatjie

A healthy deployment returns:

``` json
{"status":"healthy","application":"meridian-compass","mcp":"connected","rag":"ready"}
```

## Authority model

Meridian Compass deliberately separates four kinds of authority:

1.  **Enterprise Identity** establishes who the employee is.
2.  **Authorised structured data** establishes the employee's current
    operational situation.
3.  **Approved policy** establishes what is permitted, required or
    prohibited.
4.  **Approved procedure** establishes how the employee should proceed.

If approved Meridian documents and authorised structured data do not
support an answer, the system fails closed rather than substituting
general model knowledge.

## Architecture

``` text
Employee
  |
Web UI / FastAPI
  |
Simulated Enterprise Identity
  |
Agent Orchestrator -------- LLM Provider
  |
MCP Client
  |
Streamable HTTP
  |
MCP Server
  |----------------------|
RAG Knowledge       Structured Operations
  |----------------------|
           |
Deterministic Claim Verifier
           |
Answer + citations + snippets + trace
```

The deployed service contains the web app, orchestrator, MCP
client/server, FAISS index and synthetic JSON data in one Render service
while retaining an in-process official Streamable HTTP MCP protocol
boundary mounted at `/mcp`.

## Technology

-   Python and FastAPI
-   MCP with Streamable HTTP
-   Sentence Transformers `all-MiniLM-L6-v2`
-   FAISS `IndexFlatIP`
-   GPT-4.1-mini in the validated production configuration
-   Docker
-   GitHub Actions
-   Render

The controlled knowledge corpus contains **19 approved fictional
documents**: 12 policies and 7 procedures. The index contains **353
chunks** with **384-dimensional embeddings**.

## MCP tools

Knowledge: - `search_knowledge_documents`

Structured read: - `lookup_employee_profile` - `check_pto_balance` -
`lookup_benefits_status` - `lookup_active_assignment` -
`lookup_travel_authorization` - `get_mock_travel_booking` -
`get_per_diem_rate` - `get_mock_expense_claim` - `resolve_approval_role`

Controlled actions: - `draft_hr_email` - `create_mock_hr_ticket` -
`create_mock_travel_request`

## Repository structure

``` text
app/                 FastAPI app, UI, orchestration and verification
mcp/                 MCP server/client and tool definitions
rag/                 RAG ingestion and retrieval
knowledge/           Approved fictional policy/procedure corpus
mock_data/           Synthetic operational data
data/                Simulated Enterprise Identity data
evaluation/          Evaluation implementation and reported summary
tests/               Automated tests
scripts/             Build and validation scripts
.github/workflows/   CI
project_docs/        Controlled engineering contracts/specifications
project_docs/evaluation/  Controlled evaluation dataset/specification
Dockerfile           Production image
```

## Local setup

``` bash
git clone https://github.com/dineom-arch/Quantic_AI_Techniques_Project_Dineo_Malatjie.git
cd Quantic_AI_Techniques_Project_Dineo_Malatjie
python -m venv .venv
```

Windows PowerShell:

``` powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, populate the required LLM provider values
and do not commit `.env`.

Build the RAG index:

``` bash
python scripts/build_index.py
```

## Docker

``` bash
docker build -t meridian-compass .
docker run --rm -p 8000:8000 \
  -e LLM_API_KEY -e LLM_MODEL -e LLM_BASE_URL \
  meridian-compass
```

The Docker build constructs the canonical index at
`/app/data/vector_store`; the approved corpus is at `/app/knowledge`.
Set the three LLM variables in the host shell before running the command.
Do not pass the local `.env` unchanged because its relative development
paths would override the container paths. The container must retain
`KNOWLEDGE_DATA_PATH=/app/knowledge`,
`VECTOR_STORE_PATH=/app/data/vector_store` and
`MOCK_DATA_PATH=/app/mock_data` from the Docker image.

## Tests and CI

The automated inventory contains **138 tests**. The final GitHub Actions
pipeline on Python 3.12 performs dependency installation, canonical RAG
index construction, the automated suite, explicit `MSG-POL-001`
retrieval, real MCP discovery and a safe knowledge-tool invocation,
Docker build, container startup and `/health` verification.

The final repository audit found no skipped/expected-failure tests and
no tracked secrets or generated runtime index artefacts.

## Evaluation

Final controlled result: **27/30 cases passed (90%)**.

Representative local deterministic latency: - mean 168.318 ms - p50
126.106 ms - p95 355.581 ms

Retrieval was compared at `k=3`, `k=5` and `k=8`. A policy-removal
ablation verified that the system returns insufficient evidence rather
than manufacturing a missing rule.

See `design-and-evaluation.md` and `evaluation/summary.md`.

## Demo workflows

**Planned PTO during an active assignment:** identity, employee profile,
PTO balance, assignment, policy retrieval and approval resolution
combine into a grounded answer.

**Personal travel extension:** authorised travel, booking,
assignment/PTO context, per-diem/travel policy and approval routing
combine into grounded cost and next-step guidance.

## Safety and limitations

-   Meridian Strategy Group, its policies and all employee data are
    fictional/synthetic.
-   User assertions cannot override authenticated identity, structured
    data or approved policy.
-   Structured data cannot create policy.
-   Procedures cannot create substantive eligibility absent policy.
-   Missing authoritative evidence produces an insufficient-evidence
    response.
-   Out-of-scope general-knowledge questions are rejected.
-   Enterprise Identity is simulated.
-   Controlled actions do not modify a real HR system.
-   Real LLM calls are excluded from CI and are validated manually in
    production.
-   Render's 512 MB instance could start the service but exceeded memory
    during a full live workflow. Final production acceptance used a 2 GB
    instance. See `deployed.md`.

## Submission documentation

-   `design-and-evaluation.md`
-   `ai-tooling.md`
-   `deployed.md`
-   `evaluation/summary.md`

## Project Demonstration

- **Recorded Demo Video:** [Watch the 7-10 minute application demonstration](https://drive.google.com/file/d/158xzIbdMliU_-pGDlWhef9z8dBRp32I5/view?usp=drive_link)
- **Presentation:** [View the Meridian Compass project presentation](https://drive.google.com/file/d/1GObRSo4kCxs7QY6nL2QVuSiV5orgICGE/view?usp=drive_link)
