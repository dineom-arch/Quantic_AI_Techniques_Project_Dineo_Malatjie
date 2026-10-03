"""Deterministic claim and citation verification against authorised evidence."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agent.evidence import EvidenceBundle


ClaimType = Literal["operational", "policy", "procedure", "limitation"]


class ProposedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    text: str
    claim_type: ClaimType
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_quote: str | None = None
    supporting_fact: dict[str, Any] | None = None
    necessary: bool = True


class CitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    approval_role: Literal[
        "engagement_manager", "line_manager", "engagement_partner", "designated_travel_approver"
    ]
    assignment_id: str | None = None


class SynthesisDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposed_answer: str
    proposed_status: Literal["answered", "insufficient_evidence"]
    claims: list[ProposedClaim]
    citations: list[CitationRequest] = Field(default_factory=list)
    approval_requests: list[ApprovalRequest] = Field(default_factory=list)
    insufficiency_statement: str | None = None


class SourceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    evidence_id: str
    evidence_type: Literal["operational", "knowledge"]
    source: str
    fact: dict[str, Any] | None = None
    document_id: str | None = None
    title: str | None = None
    document_type: str | None = None
    section: str | None = None
    snippet: str | None = None


class VerifiedClaim(BaseModel):
    claim: ProposedClaim
    supported: bool
    sources: list[SourceRecord] = Field(default_factory=list)
    reason: str | None = None


def build_source_catalog(bundle: EvidenceBundle) -> dict[str, SourceRecord]:
    catalog: dict[str, SourceRecord] = {}
    operational_index = knowledge_index = 0
    for item in bundle.items:
        if item.status != "ok":
            continue
        if item.evidence_type == "operational" and item.fact:
            operational_index += 1
            evidence_id = f"operational-{operational_index:03d}"
            catalog[evidence_id] = SourceRecord(
                evidence_id=evidence_id, evidence_type="operational",
                source=item.source, fact=item.fact,
            )
        elif item.evidence_type == "knowledge" and item.document_id and item.snippet:
            knowledge_index += 1
            evidence_id = f"knowledge-{knowledge_index:03d}"
            catalog[evidence_id] = SourceRecord(
                evidence_id=evidence_id, evidence_type="knowledge", source=item.source,
                document_id=item.document_id, title=item.document_title,
                document_type=item.document_type, section=item.section, snippet=item.snippet,
            )
    return catalog


def _contains_subset(container: Any, subset: Any) -> bool:
    if isinstance(subset, dict):
        return isinstance(container, dict) and all(
            key in container and _contains_subset(container[key], value)
            for key, value in subset.items()
        )
    if isinstance(subset, list):
        return isinstance(container, list) and all(
            any(_contains_subset(candidate, value) for candidate in container)
            for value in subset
        )
    return container == subset


def _scalar_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return [item for child in value.values() for item in _scalar_values(child)]
    if isinstance(value, list):
        return [item for child in value for item in _scalar_values(child)]
    return [value]


def _quote_supports_claim(claim: str, quote: str) -> bool:
    """Policy/procedure claims are extractive so inversions cannot pass lexical overlap."""

    normalise = lambda value: " ".join(value.split()).casefold()
    return bool(claim.strip()) and normalise(claim) == normalise(quote)


class ClaimVerifier:
    def verify(self, draft: SynthesisDraft, catalog: dict[str, SourceRecord]) -> list[VerifiedClaim]:
        return [self._verify_claim(claim, catalog) for claim in draft.claims]

    def _verify_claim(self, claim: ProposedClaim, catalog: dict[str, SourceRecord]) -> VerifiedClaim:
        if not claim.evidence_ids or any(source_id not in catalog for source_id in claim.evidence_ids):
            return VerifiedClaim(claim=claim, supported=False, reason="Unknown evidence reference")
        sources = [catalog[source_id] for source_id in claim.evidence_ids]
        if claim.claim_type == "operational":
            if claim.supporting_fact is None or any(source.evidence_type != "operational" for source in sources):
                return VerifiedClaim(claim=claim, supported=False, reason="Operational evidence required")
            if not any(_contains_subset(source.fact, claim.supporting_fact) for source in sources):
                return VerifiedClaim(claim=claim, supported=False, reason="Operational fact mismatch")
            text = claim.text.casefold()
            for value in _scalar_values(claim.supporting_fact):
                if value is not None and str(value).casefold() not in text:
                    return VerifiedClaim(claim=claim, supported=False, reason="Claim does not state supported value")
            return VerifiedClaim(claim=claim, supported=True, sources=sources)
        if claim.claim_type in {"policy", "procedure"}:
            if any(
                source.evidence_type != "knowledge" or source.document_type != claim.claim_type
                for source in sources
            ):
                return VerifiedClaim(claim=claim, supported=False, reason=f"{claim.claim_type.title()} evidence required")
            quote = claim.evidence_quote or ""
            if not quote or not any(quote in (source.snippet or "") for source in sources):
                return VerifiedClaim(claim=claim, supported=False, reason="Evidence quote not retrieved")
            if not _quote_supports_claim(claim.text, quote):
                return VerifiedClaim(claim=claim, supported=False, reason="Claim exceeds quoted evidence")
            return VerifiedClaim(claim=claim, supported=True, sources=sources)
        if claim.claim_type == "limitation":
            return VerifiedClaim(claim=claim, supported=True, sources=sources)
        return VerifiedClaim(claim=claim, supported=False, reason="Unsupported claim type")
