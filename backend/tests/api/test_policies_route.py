from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import write_json


def _policy(code: str, pdf_path: str) -> dict:
    return {
        "meta": {
            "code": code,
            "file_path": pdf_path,
            "title": f"Policy {code}",
            "applicable_to": [],
            "document_topics": [],
            "entity_refs": [],
        },
        "sections": [],
    }


def test_list_policies_returns_data(api_client: TestClient, settings) -> None:
    write_json(settings.policies_json, [_policy("GG.1503", "somewhere.pdf")])
    resp = api_client.get("/policies")
    assert resp.status_code == 200
    assert [p["meta"]["code"] for p in resp.json()] == ["GG.1503"]


def test_get_policy_pdf_streams_file(api_client: TestClient, settings, tmp_path: Path) -> None:
    pdf = tmp_path / "GG.1503.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%% minimal\n%%EOF")
    write_json(settings.policies_json, [_policy("GG.1503", str(pdf))])

    resp = api_client.get("/policy/GG.1503/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_get_policy_pdf_404_when_code_unknown(api_client: TestClient, settings) -> None:
    write_json(settings.policies_json, [])
    resp = api_client.get("/policy/XX.9999/pdf")
    assert resp.status_code == 404


def test_get_policy_pdf_404_when_file_missing(api_client: TestClient, settings) -> None:
    write_json(settings.policies_json, [_policy("GG.1503", "/nonexistent/path.pdf")])
    resp = api_client.get("/policy/GG.1503/pdf")
    assert resp.status_code == 404
