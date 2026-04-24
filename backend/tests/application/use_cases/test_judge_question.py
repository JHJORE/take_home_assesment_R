from readily.application.use_cases.judge_question import judge_question_claim, pick_best_match
from readily.domain.entities import Claim, MatchRecord, PolicyDoc, PolicyMeta, PolicySection
from tests._stubs import StubGemini


def _qc() -> Claim:
    return Claim(
        claim="MCPs must provide hospice services upon Member election.",
        source_text="...",
    )


def _candidate_docs() -> list[PolicyDoc]:
    return [
        PolicyDoc(
            meta=PolicyMeta(
                code="GG.1503",
                file_path="ENG #4/Public Policies/GG/GG.1503.pdf",
                title="Hospice Coverage",
            ),
            sections=[
                PolicySection(
                    heading="II.A Hospice Coverage",
                    page=1,
                    claims=[
                        Claim(
                            claim="CalOptima Health shall ensure provision of Hospice Care upon Member election.",
                            source_text="CalOptima Health and its Health Networks shall...",
                            page=1,
                        ),
                        Claim(
                            claim="Hospice services require prior authorization in all cases.",
                            source_text="...",
                            page=1,
                        ),
                    ],
                ),
                PolicySection(
                    heading="I. PURPOSE",
                    page=1,
                    claims=[
                        Claim(
                            claim="The policy's effective date is 06/01/2001.",
                            source_text="Effective Date: 06/01/2001",
                            page=1,
                        ),
                    ],
                ),
            ],
        )
    ]


def test_judge_picks_best_match_and_surfaces_contradictions():
    client = StubGemini(
        [
            {"index": 0, "verdict": "MATCH", "rationale": "entails on election", "confidence": 85},
            {"index": 1, "verdict": "CONTRADICTION", "rationale": "APL bars PA", "confidence": 90},
            {"index": 2, "verdict": "UNRELATED", "rationale": "effective date only"},
        ]
    )
    best, contradictions = judge_question_claim(_qc(), _candidate_docs(), client=client)
    assert best is not None
    assert best.policy_code == "GG.1503"
    assert best.section == "II.A Hospice Coverage"
    assert best.confidence == 85.0
    assert "entails" in best.rationale
    assert len(contradictions) == 1
    assert contradictions[0].section == "II.A Hospice Coverage"
    assert "PA" in contradictions[0].rationale


def test_judge_stamps_provenance_from_candidate_docs_onto_match_record():
    client = StubGemini(
        [
            {"index": 0, "verdict": "MATCH", "rationale": "entails", "confidence": 80},
            {"index": 1, "verdict": "UNRELATED", "rationale": "n/a"},
            {"index": 2, "verdict": "UNRELATED", "rationale": "n/a"},
        ]
    )
    best, _ = judge_question_claim(_qc(), _candidate_docs(), client=client)
    assert best is not None
    assert best.policy_file_path.endswith("GG.1503.pdf")
    assert best.policy_title == "Hospice Coverage"
    assert best.policy_claim.claim.startswith("CalOptima Health shall ensure")


def test_judge_picks_highest_confidence_match_when_multiple():
    client = StubGemini(
        [
            {"index": 0, "verdict": "MATCH", "rationale": "okay", "confidence": 60},
            {"index": 1, "verdict": "MATCH", "rationale": "stronger", "confidence": 92},
            {"index": 2, "verdict": "UNRELATED", "rationale": "n/a"},
        ]
    )
    best, _ = judge_question_claim(_qc(), _candidate_docs(), client=client)
    assert best is not None
    assert best.confidence == 92.0
    assert best.rationale == "stronger"


def test_judge_no_match_returns_none_but_keeps_contradictions():
    client = StubGemini(
        [
            {"index": 0, "verdict": "UNRELATED", "rationale": "n/a"},
            {"index": 1, "verdict": "CONTRADICTION", "rationale": "conflicts", "confidence": 75},
            {"index": 2, "verdict": "UNRELATED", "rationale": "n/a"},
        ]
    )
    best, contradictions = judge_question_claim(_qc(), _candidate_docs(), client=client)
    assert best is None
    assert len(contradictions) == 1
    assert contradictions[0].confidence == 75.0


def test_judge_no_candidates_returns_none_without_llm_call():
    client = StubGemini()  # any call would fail
    best, contradictions = judge_question_claim(_qc(), [], client=client)
    assert best is None and contradictions == []
    assert client.calls == []


def test_judge_docs_with_no_claims_returns_none_without_llm_call():
    empty_doc = PolicyDoc(meta=PolicyMeta(code="AA.0", file_path="/x.pdf"))
    client = StubGemini()
    best, contradictions = judge_question_claim(_qc(), [empty_doc], client=client)
    assert best is None and contradictions == []
    assert client.calls == []


def test_pick_best_match_returns_first_or_none():
    assert pick_best_match([]) is None
    record = pick_best_match(
        [
            MatchRecord(
                policy_code="GG.1503", policy_claim=Claim(claim="x", source_text="x"), rationale="r"
            )
        ]
    )
    assert record is not None and record.policy_code == "GG.1503"
