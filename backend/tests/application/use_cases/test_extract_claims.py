from readily.application.use_cases.extract_claims import extract_claims
from tests._stubs import StubGemini


def test_extract_claims_returns_claims_from_structured_response():
    client = StubGemini(
        # stage 1: extract statements
        {
            "statements": [
                {
                    "claim": "MCPs must provide hospice services on Member election.",
                    "source_text": "MCPs are required to provide hospice services upon Member election",
                },
                {
                    "claim": "Hospice coverage includes two 90-day periods.",
                    "source_text": "Two 90-day periods",
                },
            ]
        },
        # stage 2: one disambiguate per statement
        {"disambiguated": "MCPs must provide hospice services on Member election."},
        {"disambiguated": "Hospice coverage includes two 90-day periods."},
    )
    claims = extract_claims(
        text="MCPs are required to provide hospice services upon Member election. Two 90-day periods.",
        client=client,
        context="APL 25-008",
        page=1,
    )
    assert [c.claim for c in claims] == [
        "MCPs must provide hospice services on Member election.",
        "Hospice coverage includes two 90-day periods.",
    ]
    assert all(c.page == 1 for c in claims)
    assert len(client.calls) == 3


def test_extract_claims_drops_empty_text():
    client = StubGemini(
        {
            "statements": [
                {"claim": "", "source_text": "x"},
                {"claim": "Z", "source_text": "z"},
            ]
        },
        # only one disambig call expected — empty stage-1 items are skipped before stage 2
        {"disambiguated": "Z"},
    )
    claims = extract_claims(text="z", client=client)
    assert [c.claim for c in claims] == ["Z"]
    assert len(client.calls) == 2


def test_extract_claims_compound_question_splits_and_flips_interrogative():
    question = (
        "Does the P&P state that MCPs must provide hospice services to Members who elect "
        "hospice care, and that hospice coverage is provided in two 90-day periods followed "
        "by unlimited 60-day periods?"
    )
    client = StubGemini(
        {
            "statements": [
                {
                    "claim": "MCPs must provide hospice services to Members who elect hospice care.",
                    "source_text": "MCPs must provide hospice services to Members who elect hospice care",
                },
                {
                    "claim": "Hospice coverage is provided in two 90-day periods followed by unlimited 60-day periods.",
                    "source_text": "hospice coverage is provided in two 90-day periods followed by unlimited 60-day periods",
                },
            ]
        },
        {"disambiguated": "MCPs must provide hospice services to Members who elect hospice care."},
        {
            "disambiguated": "Hospice coverage is provided in two 90-day periods followed by unlimited 60-day periods."
        },
    )
    claims = extract_claims(text=question, client=client, context="APL 25-008, page 1")
    assert len(claims) == 2
    assert all(not c.claim.endswith("?") for c in claims), "question flipped to declarative"
    for c in claims:
        assert c.source_text in question, (
            f"source_text must be a verbatim substring: {c.source_text!r}"
        )


def test_extract_claims_drops_statement_with_empty_disambiguation():
    client = StubGemini(
        {
            "statements": [
                {"claim": "A must do X.", "source_text": "A must do X"},
                {
                    "claim": "Such requests are handled by them.",
                    "source_text": "such requests are handled by them",
                },
            ]
        },
        {"disambiguated": "A must do X."},
        {"disambiguated": ""},
    )
    claims = extract_claims(text="A must do X. Such requests are handled by them.", client=client)
    assert [c.claim for c in claims] == ["A must do X."]
    assert len(client.calls) == 3


def test_extract_claims_empty_stage1_issues_no_stage2_calls():
    client = StubGemini({"statements": []})
    claims = extract_claims(text="PURPOSE", client=client)
    assert claims == []
    assert len(client.calls) == 1


def test_extract_claims_empty_input_short_circuits():
    client = StubGemini()  # no responses — any call would fail
    assert extract_claims(text="   ", client=client) == []
    assert client.calls == []
