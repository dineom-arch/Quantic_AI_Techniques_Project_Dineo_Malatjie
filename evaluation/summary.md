# Evaluation Summary

## Scope

The controlled 30-case set covers policy Q&A, multi-document reasoning,
structured-data tools, multi-step workflows, approval routing, privacy,
missing evidence, out-of-scope requests and action safety.

## Final result

**27/30 passed (90%).**

Three bounded failures remained: 1. one expected-answer check
distinguished `eight` from `8`; 2. the controlled MCP tool contract
requires `expense_id` for expense lookup, but two evaluation prompts did
not supply the required identifier while still expecting the expense
lookup tool to be called.

The missing identifier and missing authority were not invented merely to
force a pass.

## Representative cases

  -----------------------------------------------------------------------
  Case                    Purpose                 Result
  ----------------------- ----------------------- -----------------------
  Planned PTO             Identity + PTO +        PASS
                          assignment + RAG +
                          approval

  Personal travel         Travel + per diem +     PASS
  extension               policy + approval

  Approval resolution     Policy role to          PASS
                          operational approver

  Missing gifts policy    Fail closed + supported PASS
                          escalation

  Out-of-scope question   Reject general-model    PASS
                          answer

  Privacy request         Do not disclose another PASS
                          employee's HR data
  -----------------------------------------------------------------------

A supplemental capital-of-France case was rejected without tool use or a
general-knowledge answer.

## Retrieval comparison

`k=3`, `k=5` and `k=8` produced the same 14/30 outcome at an earlier
stage because the dominant failures were routing/orchestration defects,
not retrieval depth.

## Ablation

Removing the relevant security policy produced the expected
insufficient-evidence response rather than a fabricated policy rule:
**PASS**.

## Latency

  Metric          Result
  --------- ------------
  Mean        168.318 ms
  p50         126.106 ms
  p95         355.581 ms
  Minimum       1.185 ms
  Maximum     865.186 ms

These are local deterministic evaluation figures, not live end-user LLM
latency.

## Automated evidence

-   138 tests collected;
-   no skip/xfail markers;
-   compilation passed;
-   GitHub Actions passed on Python 3.12;
-   canonical RAG build/retrieval verified;
-   real Streamable HTTP MCP discovery and safe call verified;
-   Docker build/start and `/health` verified.

## Production evidence

Final deployed health:

``` json
{"status":"healthy","application":"meridian-compass","mcp":"connected","rag":"ready"}
```

A live PTO workflow then completed with operational context, RAG
evidence, citation, source snippet and system trace.

The free/512 MB hosting configuration was also tested. It could start
but exceeded memory during the full live workflow. Final production
acceptance used a 2 GB instance.

## Interpretation

The system is designed to stop when authority is absent. The remaining
controlled failures were not hidden by weakening grounding requirements
or inventing missing contracts.
