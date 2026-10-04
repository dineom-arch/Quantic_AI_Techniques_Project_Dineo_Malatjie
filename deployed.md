# Deployment

## URLs

Application: https://quantic-ai-techniques-project-dineo.onrender.com

Health: https://quantic-ai-techniques-project-dineo.onrender.com/health

Repository:
https://github.com/dineom-arch/Quantic_AI_Techniques_Project_Dineo_Malatjie

## Architecture

Meridian Compass is deployed as a Docker-based Render web service from
`main`.

One service contains: - FastAPI web app/UI; - agent orchestrator; - LLM
provider client; - MCP client/server using an in-process official
Streamable HTTP protocol boundary mounted at `/mcp`; - FAISS vector
store; - approved fictional corpus; - synthetic structured operational
data. The application crosses the official MCP `ClientSession` /
Streamable HTTP protocol boundary in-process rather than through a
localhost TCP network connection.

Production paths:

``` text
/app/knowledge
/app/data/vector_store
/app/mock_data
```

Secrets/configuration are supplied through Render environment variables
and are not committed. The application binds to the host-provided
`PORT`.

## Health

Expected response:

``` json
{"status":"healthy","application":"meridian-compass","mcp":"connected","rag":"ready"}
```

Production logs confirmed:

``` text
RAG ready: corpus_path=/app/knowledge
vector_store_path=/app/data/vector_store
StreamableHTTP session manager started
Application startup complete.
```

## Validation gates

1.  clean local Docker build;
2.  local Docker `/health`;
3.  in-container retrieval including `MSG-POL-001`;
4.  GitHub Actions;
5.  Render deployment;
6.  production `/health`;
7.  simulated Enterprise Identity authentication;
8.  live production PTO workflow;
9.  visible policy citation/source snippet;
10. visible system/tool trace.

## CI/CD

GitHub Actions on push/PR to `main`: 1. checkout; 2. Python 3.12; 3.
install dependencies; 4. build canonical test RAG index; 5. run
automated tests; 6. verify RAG retrieval; 7. verify Streamable HTTP MCP
discovery and a safe call; 8. build Docker; 9. start container; 10.
retry and verify `/health`; 11. log failures and clean up.

Final validated CI commit: `b10f941`
(`fix: align CI RAG index setup with test suite`).

## Cold start and resource sizing

The free instance had a substantial cold start while loading the Python
ML/SentenceTransformer stack.

A 512 MB service could start and report healthy but failed during a
complete live agent workflow. Render Events reported:

``` text
Ran out of memory (used over 512MB) while running your code.
```

Immediately before restart, logs showed successful MCP protocol traffic
and `CallToolRequest` processing. There was no Python business-logic
traceback.

The service was right-sized to **2 GB RAM** for final production
acceptance. This was an infrastructure resource requirement; application
code was not changed to mask it.

## Production acceptance

Question:

> I want to take PTO on Thursday 15 October 2026 and Friday 16 October
> 2026. Can I take those days off?

The deployed system returned a grounded answer using: - 15 days
available PTO; - active Nairobi assignment; - Engagement Manager
route; - 11 calendar days' notice at runtime versus the standard 14-day
planned-PTO requirement; - Amara Okafor as recorded Engagement
Manager; - the distinction between submission and approval.

The UI cited `MSG-POL-001 PTO & Leave Policy` and displayed the system
trace.

## Grader notes

-   Use **Continue with Enterprise Identity** to authenticate the
    controlled demo employee.
-   All company data is fictional/synthetic.
-   A service restart can expire the simulated session; simply
    authenticate again.
-   Final production acceptance uses 2 GB RAM because 512 MB exceeded
    memory during a full agent workflow.
-   Live LLM calls are deliberately excluded from CI and are verified
    manually in production.
