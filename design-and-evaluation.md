# Meridian Compass: Design and Evaluation

## 1. Design objective

Meridian Compass is an agentic People & Travel Operations Assistant for
the fictional Meridian Strategy Group. Its purpose is to combine
authenticated identity, current operational context and approved
internal knowledge so that answers are employee-specific, cited and
auditable.

Core rule:

> If Meridian's approved internal documents and authorised structured
> company data do not support the answer, Meridian Compass does not know
> the answer.

The LLM synthesises supported evidence; it is not treated as a source of
company policy.

## 2. Authority model

1.  **Enterprise Identity: WHO**. Server-authoritative simulated
    identity.
2.  **Structured operational data: WHAT situation**. Employee, PTO,
    assignment, benefits, travel, expense and approval relationships.
3.  **Policy: WHAT is permitted/required/prohibited**. Substantive rules
    require approved policy evidence.
4.  **Procedure: HOW**. Process and escalation steps require approved
    procedure evidence.

Structured data cannot create policy. Procedure cannot create a
substantive entitlement absent policy.

## 3. Architecture

``` text
Employee
  |
Web UI / FastAPI
  |
Enterprise Identity
  |
Agent Orchestrator ----------------> LLM Provider
  |
MCP Client
  | Streamable HTTP
MCP Server
  |--------------------|------------------|
Knowledge Tool    Structured Reads    Controlled Actions
  |                    |                  |
FAISS RAG          Synthetic JSON      Mock actions
  |--------------------|------------------|
                       |
             Deterministic Claim Verifier
                       |
          Answer + citations + snippets + trace
```

The single-service Render deployment keeps infrastructure compact while
preserving the MCP protocol boundary.

## 4. Agent orchestration

The system uses controlled manual orchestration rather than unrestricted
model autonomy:

1.  authenticate;
2.  classify/route the request;
3.  invoke approved MCP tools selected by the planner;
4.  gather structured facts;
5.  retrieve policy/procedure evidence;
6.  resolve approval relationships where needed;
7.  synthesise using the bounded evidence;
8.  verify material claims;
9.  return only a grounded answer;
10. otherwise fail closed, clarify or use a supported escalation route.

MCP tool discovery is implemented separately and is explicitly verified
by integration and CI tests; it does not run on every `/chat` request.

## 5. RAG design

Corpus: **19 approved documents**, comprising 12 policies and 7
procedures.

Embedding model: `sentence-transformers/all-MiniLM-L6-v2`\
Dimension: **384**\
Vector store: FAISS `IndexFlatIP`\
Chunks: **353**\
Production vector store: `/app/data/vector_store`\
Production corpus: `/app/knowledge`

The index is built during Docker image construction. Runtime checks
validate artifact presence, chunk count, chunk fingerprint, corpus
fingerprint, embedding model name and embedding model initialization.
Embedding dimension is recorded in the index manifest, but runtime does
not explicitly compare the manifest dimension with `index.d`. Missing,
stale, corrupt or incompatible indexes fail closed.

Retrieved chunks retain document, title and section metadata. Material
policy/procedure claims require supporting extractive evidence.

## 6. MCP design

Transport: **Streamable HTTP**.

Knowledge: - `search_knowledge_documents`

Structured reads: - `lookup_employee_profile` - `check_pto_balance` -
`lookup_benefits_status` - `lookup_active_assignment` -
`lookup_travel_authorization` - `get_mock_travel_booking` -
`get_per_diem_rate` - `get_mock_expense_claim` - `resolve_approval_role`

Controlled actions: - `draft_hr_email` - `create_mock_hr_ticket` -
`create_mock_travel_request`

The orchestrator does not directly read operational JSON. Privacy
controls prevent ordinary employees from retrieving another employee's
private HR data.

## 7. Grounding and safety

-   Authenticated identity cannot be overridden by prompt text.
-   General pretrained knowledge cannot substitute for missing Meridian
    policy.
-   Policy/procedure claims require retrieved approved evidence.
-   Operational claims require matching structured facts.
-   Deterministic verification checks the final evidence bundle.
-   Invalid citations, unsupported claims, provider failures and
    insufficient evidence fail closed.
-   Actions are controlled/mock operations and guidance is not
    misrepresented as approval.

## 8. Demo workflow 1: planned PTO

Example:

> I want to take PTO on Thursday 15 October 2026 and Friday 16 October
> 2026. Can I take those days off?

Expected sequence: identity -\> employee profile -\> PTO balance -\>
active assignment -\> knowledge retrieval -\> approval resolution -\>
synthesis -\> verification.

Production acceptance returned: - 15 days PTO available; - active
Nairobi assignment; - Engagement Manager approval route; - 11 calendar
days' notice at runtime, below the standard 14-day planned-PTO
requirement; - Amara Okafor as recorded Engagement Manager; - the
request may be submitted but is not already approved.

The UI cited `MSG-POL-001 PTO & Leave Policy` and displayed the system
trace.

## 9. Demo workflow 2: personal travel extension

The workflow combines identity, authorised travel, booking,
assignment/PTO context, per-diem/travel policy and approval resolution.

Controlled fixture: - business-equivalent fare: ZAR 8,400; - proposed
extended return: ZAR 9,650; - incremental personal cost: ZAR 1,250.

The corpus constrains hotel/per-diem treatment and requires approval
before itinerary modification.

## 10. Evaluation

The controlled set contains 30 cases spanning policy Q&A, multi-document
questions, tool use, multi-step workflows, ambiguity, privacy,
missing-policy handling, out-of-scope requests and action safety.

**Final result: 27/30 passed (90%).**

Three bounded failures remained: - one literal expectation distinguished
`eight` from `8`; - the controlled MCP tool contract requires
`expense_id` for expense lookup, but two evaluation prompts did not
supply the required identifier while still expecting the expense lookup
tool to be called.

The system did not invent the missing identifier or missing authority to
force those cases to pass.

Representative safety checks covered groundedness, citation accuracy,
unsupported-claim control, corpus-only evidence, privacy, action safety,
approval accuracy and out-of-scope refusal.

A supplemental question asking for the capital of France was rejected
without a general-model answer. A missing gifts/hospitality policy case
did not invent a rule and used the approved escalation procedure.

## 11. Retrieval comparison and ablation

`k=3`, `k=5` and `k=8` produced the same 14/30 result at an earlier
evaluation stage because the dominant failures were
routing/orchestration issues, not retrieval depth.

A policy-removal ablation suppressed the relevant security policy.
Result: **PASS**. The system returned insufficient evidence instead of
manufacturing the missing rule.

## 12. Latency

Representative local deterministic evaluation:

  Metric         Result
  -------- ------------
  Mean       168.318 ms
  p50        126.106 ms
  p95        355.581 ms
  Min          1.185 ms
  Max        865.186 ms

These figures are not end-user live LLM latency.

## 13. Automated verification

Final audit: - 138 tests collected; - no skip/xfail markers; -
compilation passed; - GitHub Actions passed on Python 3.12; - clean
working tree; - no tracked secrets/runtime index.

CI builds the index, runs tests, verifies `MSG-POL-001` retrieval,
performs real MCP discovery and a safe call, builds Docker, starts the
container and verifies `/health`.

The local Windows Python 3.14 monolithic run terminated without a pytest
failure summary; supported Python 3.12 CI remained the authoritative
full-suite validation.

## 14. Production acceptance and deployment limitation

Final production health:

``` json
{"status":"healthy","application":"meridian-compass","mcp":"connected","rag":"ready"}
```

The deployed system then completed the PTO workflow with live LLM
synthesis, MCP execution, RAG evidence, structured context, citation
display and trace.

A 512 MB Render instance could start but exceeded memory during the full
live workflow. Render Events explicitly reported out-of-memory use above
512 MB. The same application build passed production acceptance after
right-sizing to 2 GB RAM.

Known limitations include simulated identity, fictional/synthetic data,
controlled mock actions, no paid/live OpenAI calls in CI, concise
`/health`, host-level rather than in-container MCP call testing, bounded
dependency ranges without a lockfile, and ignored generated evaluation
outputs.

## 15. Conclusion

Meridian Compass treats the LLM as one component of a controlled system.
Authenticated identity, authorised operational context, approved RAG
evidence, MCP-mediated tools and deterministic verification combine to
turn a generic employee question into a grounded employee-specific next
action.
