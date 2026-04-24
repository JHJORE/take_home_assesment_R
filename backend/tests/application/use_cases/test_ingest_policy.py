import readily.application.use_cases.ingest_policy as pmod
from readily.application.use_cases.ingest_policy import ingest_policy
from tests._stubs import StubGemini


def test_ingest_policy_parses_meta_and_sections(monkeypatch):
    monkeypatch.setattr(pmod, "pages", lambda _p: ["page1 text", "page2 text"])
    client = StubGemini(
        {
            "meta": {
                "code": "GG.1234",
                "title": "Hospice Services",
                "applicable_to": ["Medi-Cal"],
            },
            "sections": [
                {"heading": "II.A Hospice Coverage", "page": 1, "text": "Hospice is covered..."},
                {"heading": "II.B Benefit Periods", "page": 2, "text": "Two 90-day periods..."},
            ],
        }
    )
    meta, sections = ingest_policy("/any/path.pdf", client=client)
    assert meta.code == "GG.1234"
    assert meta.title == "Hospice Services"
    assert meta.applicable_to == ["Medi-Cal"]
    assert meta.file_path == "/any/path.pdf"
    assert [s.heading for s in sections] == ["II.A Hospice Coverage", "II.B Benefit Periods"]
    assert [s.page for s in sections] == [1, 2]


def test_ingest_policy_handles_missing_meta_fields(monkeypatch):
    monkeypatch.setattr(pmod, "pages", lambda _p: ["body only"])
    client = StubGemini(
        {
            "meta": {"code": "X.1"},
            "sections": [{"heading": "Body", "page": 1, "text": "..."}],
        }
    )
    meta, sections = ingest_policy("/tmp/X.1_foo.pdf", client=client)
    assert meta.code == "X.1"
    assert meta.title is None
    assert meta.applicable_to == []
    assert len(sections) == 1


def test_ingest_policy_falls_back_to_filename_code(monkeypatch):
    monkeypatch.setattr(pmod, "pages", lambda _p: ["text"])
    client = StubGemini(
        {
            "meta": {"title": "Nameless policy"},
            "sections": [{"heading": "Body", "page": 1, "text": "."}],
        }
    )
    meta, _ = ingest_policy("/tmp/HH.4999_CEO.pdf", client=client)
    assert meta.code == "HH.4999"


def test_ingest_policy_injects_page_markers_in_prompt(monkeypatch):
    monkeypatch.setattr(pmod, "pages", lambda _p: ["alpha", "beta", "gamma"])
    client = StubGemini({"meta": {"code": "Z.1"}, "sections": []})
    ingest_policy("/any/path.pdf", client=client)
    prompt, _schema = client.calls[0]
    assert "[page 1]" in prompt and "[page 2]" in prompt and "[page 3]" in prompt
    assert "alpha" in prompt and "beta" in prompt and "gamma" in prompt


def test_ingest_policy_drops_sections_with_empty_text(monkeypatch):
    monkeypatch.setattr(pmod, "pages", lambda _p: ["x"])
    client = StubGemini(
        {
            "meta": {"code": "Q.1"},
            "sections": [
                {"heading": "A", "page": 1, "text": ""},
                {"heading": "B", "page": 1, "text": "real"},
            ],
        }
    )
    _, sections = ingest_policy("/any/path.pdf", client=client)
    assert [s.heading for s in sections] == ["B"]
