# Meridian Compass — Controlled Input Resolution Register
Version 1.0

| Codex finding | Controlled disposition |
|---|---|
| BRS absent | Supplied. |
| SRS absent | Supplied. |
| Solution Design absent | Supplied; module layout frozen. |
| Domain/Policy/Procedure Specification absent | Supplied. |
| Synthetic Data Specification absent | Supplied. |
| MCP Tool Contract absent | Supplied with exact boundary/schemas/privacy/failures. |
| Manifest `version: 1.0` vs `corpus_version: 1.1` | Treat `corpus_version: 1.1` as controlled content version. The older top-level field has no policy meaning. |
| Rendered PDFs absent | Deliberate: PDFs are verification/alternate-format artefacts, not runtime authority. Pre-repo validation established 58 rendered pages; runtime indexes canonical Markdown only. |
| Designated travel approver cannot resolve to person | Deliberate. Return supported role and `not_found` for named-person resolution; do not infer. |
| Non-assignment PTO named approver absent | Do not invent; return only what approved evidence supports. |
| EVAL-002 relative date | Dataset v1.1 adds controlled evaluation date/fixed dates. |
| EVAL-028 session dependency | Dataset v1.1 declares prerequisite session context and clean action state. |
| EVAL-029 unspecified trip | Dataset v1.1 explicitly defines missing-record setup. |
| Mock action schema/lifecycle | Defined by MCP/implementation contracts: confirmation-gated, transient/resettable. |
| Case metrics vs global metrics | Case metrics are targeted; evaluator computes complete global set. |
| EVAL-030 'MCP unavailable' as tool | Dataset v1.1 treats it as environment setup, not a callable tool. |
| No non-assignment travel fixture | No named-person resolution expected. Unit-test role-only/not-found behavior; do not invent a fixture. |
