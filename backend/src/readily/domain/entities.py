from __future__ import annotations

from pydantic import BaseModel, Field


class ClaimMetadata(BaseModel):
    """Metadata attached to a single Claim. Symmetric on both sides (question-claims
    and policy-claims) so a deterministic set-overlap matcher can compare them directly.
    """

    topic_keywords: list[str] = Field(default_factory=list)
    entity_refs: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    claim: str
    source_text: str
    page: int | None = None
    metadata: ClaimMetadata = Field(default_factory=ClaimMetadata)


class QuestionMetadata(BaseModel):
    """Question-level metadata shared across every claim extracted from one question.
    `lob` is derived from the APL reference; `question_topics` captures the question's
    subject area; `reference` carries the APL citation itself for entity-ref matching.
    """

    lob: list[str] = Field(default_factory=list)
    reference: str = ""
    question_topics: list[str] = Field(default_factory=list)


class Question(BaseModel):
    number: int
    text: str
    reference: str
    claims: list[Claim] = Field(default_factory=list)
    candidate_codes: list[str] = Field(default_factory=list)
    metadata: QuestionMetadata = Field(default_factory=QuestionMetadata)


class PolicyMeta(BaseModel):
    """Policy-document metadata. Includes doc-level `document_topics` and `entity_refs`
    used by the candidate selector to route a question to the right documents. LOB is
    carried on `applicable_to` (from page-1 ☒/☐ checkboxes).
    """

    code: str
    file_path: str
    title: str | None = None
    applicable_to: list[str] = Field(default_factory=list)
    document_topics: list[str] = Field(default_factory=list)
    entity_refs: list[str] = Field(default_factory=list)


class PolicySection(BaseModel):
    """A policy section: heading, starting page, section-level metadata, and the
    atomic claims extracted from it. The section's verbatim body is not persisted
    — it's only needed as input to claim extraction, and every claim already
    carries its own `source_text`.
    """

    heading: str
    page: int
    metadata: ClaimMetadata = Field(default_factory=ClaimMetadata)
    claims: list[Claim] = Field(default_factory=list)


class PolicyDoc(BaseModel):
    meta: PolicyMeta
    sections: list[PolicySection] = Field(default_factory=list)


class MatchRecord(BaseModel):
    policy_code: str
    policy_claim: Claim
    section: str | None = None
    rationale: str
    confidence: float | None = None
    policy_file_path: str = ""
    policy_title: str = ""


class QuestionClaimResult(BaseModel):
    question_number: int
    question_claim: Claim
    best_match: MatchRecord | None = None
    contradictions: list[MatchRecord] = Field(default_factory=list)
