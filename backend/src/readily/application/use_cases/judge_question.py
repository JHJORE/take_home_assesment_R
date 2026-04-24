"""Strict LLM judge — one call per question-claim.

The judge sees every policy-claim from the candidate documents (selected by
doc-level metadata overlap upstream) and emits a MATCH / CONTRADICTION /
UNRELATED verdict for each. The best MATCH wins by confidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from readily.domain.entities import Claim, MatchRecord, PolicyDoc
from readily.infrastructure.llm.gemini import GeminiClient
from readily.infrastructure.llm.prompts import JUDGE_PROMPT

Verdict = Literal["MATCH", "CONTRADICTION", "UNRELATED"]


class JudgeVerdictItem(BaseModel):
    index: int
    verdict: Verdict
    rationale: str
    confidence: int | None = None


@dataclass
class _Candidate:
    policy_code: str
    policy_file_path: str
    policy_title: str
    section: str
    claim: Claim


def judge_question_claim(
    question_claim: Claim,
    candidate_docs: list[PolicyDoc],
    client: GeminiClient,
) -> tuple[MatchRecord | None, list[MatchRecord]]:
    """One strict Gemini call. Returns (best_match, contradictions).

    `candidate_docs` is the full top-N PolicyDocs from doc-level routing;
    every claim in every section is a candidate. When the list is empty or
    has no claims, returns (None, []).
    """
    candidates = _flatten(candidate_docs)
    if not candidates:
        return None, []

    prompt = JUDGE_PROMPT.format(
        q_claim=question_claim.claim,
        candidates_rendered=_render_candidates(candidates),
    )
    verdicts: list[JudgeVerdictItem] = client.generate_structured(prompt, list[JudgeVerdictItem])

    matches: list[MatchRecord] = []
    contradictions: list[MatchRecord] = []
    for v in verdicts:
        if v.index < 0 or v.index >= len(candidates):
            continue
        c = candidates[v.index]
        record = MatchRecord(
            policy_code=c.policy_code,
            policy_claim=c.claim,
            section=c.section,
            rationale=v.rationale.strip(),
            confidence=_coerce_confidence(v.confidence),
            policy_file_path=c.policy_file_path,
            policy_title=c.policy_title,
        )
        if v.verdict == "MATCH":
            matches.append(record)
        elif v.verdict == "CONTRADICTION":
            contradictions.append(record)

    return pick_best_match(matches), contradictions


def pick_best_match(candidates: list[MatchRecord]) -> MatchRecord | None:
    """Highest `confidence` wins; ties broken by encounter order."""
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.confidence if r.confidence is not None else -1.0)


def _flatten(docs: list[PolicyDoc]) -> list[_Candidate]:
    out: list[_Candidate] = []
    for doc in docs:
        for section in doc.sections:
            for claim in section.claims:
                out.append(
                    _Candidate(
                        policy_code=doc.meta.code,
                        policy_file_path=doc.meta.file_path,
                        policy_title=doc.meta.title or "",
                        section=section.heading,
                        claim=claim,
                    )
                )
    return out


def _coerce_confidence(raw: int | None) -> float | None:
    if raw is None:
        return None
    return max(0.0, min(100.0, float(raw)))


def _render_candidates(candidates: list[_Candidate]) -> str:
    lines: list[str] = []
    for i, c in enumerate(candidates):
        page_tag = f", page {c.claim.page}" if c.claim.page is not None else ""
        source = c.claim.source_text[:180]
        lines.append(
            f"  [{i}] {c.claim.claim}  "
            f'(policy {c.policy_code} § {c.section}{page_tag}, source: "{source}")'
        )
    return "\n".join(lines)
