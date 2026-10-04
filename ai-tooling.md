# AI Tooling

## Approach

AI tools were used as engineering assistants. They were not treated as
authoritative sources for Meridian policy, controlled data, test
outcomes or deployment status. Suggestions were reconciled against the
assignment requirements, controlled artefacts and observed evidence.

## ChatGPT

ChatGPT was used for: - assignment/rubric decomposition; - architecture
and authority-model reasoning; - phased build planning; - RAG, MCP,
orchestration and grounding design; - interpretation of tests, GitHub
Actions and Render evidence; - production incident diagnosis; -
documentation and presentation planning; - technical explanation during
implementation.

### What worked well

ChatGPT was useful for requirements decomposition, architecture
reasoning, log interpretation and maintaining the distinction between
identity, operational data, policy and procedure authority.

During final production validation it helped avoid an unnecessary code
change: `/health` was healthy but a PTO request failed. Render logs
showed successful MCP traffic followed by a restart; Render Events then
showed a 512 MB out-of-memory failure. The service was right-sized and
the same build passed.

### What did not work well

Some early presentation/artifact iterations consumed time without
advancing engineering gates. Long context also required periodic
reconciliation against the actual repository. Broad AI advice was less
useful than tightly constrained, evidence-first steps.

## Codex

Codex was used for repository-level implementation and verification: -
targeted code changes; - tests; - Docker/RAG production corrections; -
GitHub Actions; - CI diagnosis; - final read-only repository audit.

Late prompts explicitly constrained scope and prohibited uncontrolled
changes.

### What worked well

Codex was effective at repository-wide implementation, test execution,
Docker/CI corrections and structured audit work.

### What did not work well

Broad repository-agent prompts can produce more change than is desirable
late in a project, so human review remained necessary. A local
Windows/Python 3.14 monolithic test process terminated without a pytest
summary; the supported Python 3.12 GitHub Actions result remained the
authoritative full-suite validation.

## Antigravity

An Antigravity architecture-review prompt was prepared in the controlled
project artefacts. At the time this document was created, Antigravity
had **not yet modified the final implementation**.

Its intended remaining role is architecture assurance and diagram
review: checking that visual artefacts accurately represent the
implemented web app, orchestrator, MCP boundary, RAG, structured data,
LLM provider, verification layer and deployment.

If Antigravity is used before submission, this section should be updated
with the exact review and accepted/rejected recommendations. It should
not be credited with work it did not perform.

## Human oversight and verification

AI output was not accepted as proof. Verification included: - controlled
contracts and fixtures; - automated tests; - RAG manifest/index
validation; - real MCP discovery and safe invocation; - clean Docker
builds; - container health; - GitHub Actions; - Render deployment; -
production `/health`; - live production workflow; - visible citations
and trace; - Render runtime telemetry.

## Examples

### Production RAG

AI-assisted diagnosis identified that the production image did not
contain the canonical FAISS index and that runtime/build paths were
inconsistent. The correction built the index into Docker and
standardised production on `/app/data/vector_store`. It was accepted
only after clean Docker, in-container retrieval, CI and Render
validation.

### CI sequencing

The first workflow ran the full suite before the expected RAG index
existed and used a path inconsistent with the test fixture. Codex
diagnosed the sequence/path issue. The corrected workflow built
`runtime_data/rag_index` first; the second GitHub Actions run passed.

### Production memory

A live request failed despite healthy startup. Rather than refactor
immediately, logs and Events were inspected. Render reported memory use
over 512 MB. Compute was right-sized and the unchanged build then
completed the workflow.

## Academic integrity

Meridian Strategy Group, its policies and employee data are
fictional/synthetic. AI use is disclosed because AI tools materially
supported the engineering process. The student remains responsible for
the code, architecture, evaluation, security/privacy decisions,
documentation, deployed behaviour and presentation.
