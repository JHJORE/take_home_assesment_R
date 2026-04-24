"""Deterministic candidate selection — no LLM.

Ranks policies by overlap between question-side metadata and doc-level
policy metadata. Returns up to `top_k` codes. Returns an empty list when
nothing overlaps; the caller is expected to treat that as "no candidate
policy" rather than routing to a default.
"""

from __future__ import annotations

from collections.abc import Iterable

from readily.domain.entities import PolicyMeta, Question


def _lower_set(values: Iterable[str] | None) -> set[str]:
    if not values:
        return set()
    return {str(v).strip().lower() for v in values if str(v).strip()}


def select_candidates(
    question: Question,
    inventory: list[PolicyMeta],
    top_k: int = 3,
) -> list[str]:
    """Return up to `top_k` policy codes ranked by metadata overlap.

    Applies the LOB hard filter first, then scores doc-level topic and
    entity overlap. Returns `[]` when no policy matches.
    """
    q_lob = _lower_set(question.metadata.lob)
    q_topics = _lower_set(question.metadata.question_topics)
    q_entities = _lower_set([question.metadata.reference]) if question.metadata.reference else set()
    for c in question.claims:
        q_topics |= _lower_set(c.metadata.topic_keywords)
        q_entities |= _lower_set(c.metadata.entity_refs)

    scored: list[tuple[float, str]] = []
    for meta in inventory:
        p_lob = _lower_set(meta.applicable_to)
        if q_lob and p_lob and not (q_lob & p_lob):
            continue

        p_topics = _lower_set(meta.document_topics)
        p_entities = _lower_set(meta.entity_refs)

        topic_hits = len(q_topics & p_topics)
        entity_hits = len(q_entities & p_entities)
        if topic_hits == 0 and entity_hits == 0:
            continue

        score = 3.0 * topic_hits + 2.0 * entity_hits
        scored.append((score, meta.code))

    scored.sort(key=lambda s: (-s[0], s[1]))
    return [code for _, code in scored[:top_k]]
