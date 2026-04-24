from readily.application.candidate_selector import select_candidates
from readily.domain.entities import (
    Claim,
    ClaimMetadata,
    PolicyMeta,
    Question,
    QuestionMetadata,
)


def _q(text: str, lob=("Medi-Cal",), question_topics=(), claim_topics=()) -> Question:
    return Question(
        number=1,
        text=text,
        reference="APL 25-008",
        metadata=QuestionMetadata(
            lob=list(lob), reference="APL 25-008", question_topics=list(question_topics)
        ),
        claims=[
            Claim(
                claim=text,
                source_text=text,
                metadata=ClaimMetadata(
                    topic_keywords=list(claim_topics),
                    entity_refs=["APL 25-008"],
                ),
            )
        ],
    )


def _policy(
    code: str,
    *,
    title: str = "",
    applicable_to=("Medi-Cal",),
    document_topics=(),
    entity_refs=(),
) -> PolicyMeta:
    return PolicyMeta(
        code=code,
        file_path=f"/fake/{code}.pdf",
        title=title or code,
        applicable_to=list(applicable_to),
        document_topics=list(document_topics),
        entity_refs=list(entity_refs),
    )


def test_medi_cal_hospice_question_picks_hospice_policy():
    q = _q(
        "Does the P&P state that MCPs must provide hospice services?",
        question_topics=["hospice", "election"],
        claim_topics=["hospice services", "benefit period"],
    )
    inventory = [
        _policy("GG.1503", title="Hospice Coverage", document_topics=["hospice", "benefit period"]),
        _policy("GG.1550", title="Palliative Care Services", document_topics=["palliative care"]),
        _policy("MA.2001", applicable_to=["OneCare"], document_topics=["marketing"]),
        _policy("PA.1003", applicable_to=["PACE"], document_topics=["pace center"]),
    ]
    codes = select_candidates(q, inventory, top_k=3)
    assert codes[0] == "GG.1503"
    assert "PA.1003" not in codes, "PACE policy must not leak into Medi-Cal routing"
    assert "MA.2001" not in codes, "OneCare policy must not leak into Medi-Cal routing"


def test_lob_hard_filter_excludes_wrong_line_of_business():
    q = _q(
        "Does the P&P cover hospice prior authorization?",
        claim_topics=["prior authorization"],
    )
    inventory = [
        _policy("PA.1002", applicable_to=["PACE"], document_topics=["prior authorization", "pace"]),
        _policy("GG.1500", applicable_to=["Medi-Cal"], document_topics=["prior authorization"]),
    ]
    codes = select_candidates(q, inventory, top_k=3)
    assert codes == ["GG.1500"]


def test_no_metadata_overlap_returns_empty():
    # Bare-code inventory with no doc-level metadata: no overlap signal, so no
    # candidate should be returned. Better "not found" than a wrong guess.
    q = _q(
        "Does the P&P describe hospice benefit periods?",
        lob=(),
        question_topics=[],
        claim_topics=[],
    )
    inventory = [
        PolicyMeta(code="GG.1503", file_path="/x.pdf"),
        PolicyMeta(code="HH.1101", file_path="/y.pdf"),
    ]
    assert select_candidates(q, inventory, top_k=3) == []


def test_empty_inventory_returns_empty():
    q = _q("Any question", claim_topics=["anything"])
    assert select_candidates(q, [], top_k=3) == []


def test_top_k_respected():
    q = _q(
        "Hospice question",
        question_topics=["hospice"],
        claim_topics=["hospice"],
    )
    inventory = [_policy(f"GG.{i}", document_topics=["hospice"]) for i in range(1500, 1510)]
    codes = select_candidates(q, inventory, top_k=3)
    assert len(codes) == 3


def test_lob_empty_on_question_does_not_drop_all_policies():
    # If the question's lob is empty, we should not hard-filter — topic signals
    # still guide us.
    q = _q(
        "Generic compliance question about audits.",
        lob=(),
        question_topics=["audit", "compliance"],
        claim_topics=["audit", "compliance"],
    )
    inventory = [
        _policy("HH.1107", applicable_to=["Medi-Cal"], document_topics=["audit", "compliance"]),
        _policy("MA.9999", applicable_to=["OneCare"], document_topics=["marketing"]),
    ]
    codes = select_candidates(q, inventory, top_k=3)
    assert "HH.1107" in codes
