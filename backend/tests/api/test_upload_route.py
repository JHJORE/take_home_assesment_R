from __future__ import annotations

from fastapi.testclient import TestClient


def test_upload_pdf_saves_and_returns_metadata(api_client: TestClient, settings) -> None:
    resp = api_client.post(
        "/upload",
        files={"file": ("questionnaire.pdf", b"%PDF-1.4 stub", "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["filename"] == "questionnaire.pdf"
    assert body["bytes"] == len(b"%PDF-1.4 stub")
    assert (settings.upload_dir / "questionnaire.pdf").read_bytes() == b"%PDF-1.4 stub"


def test_upload_rejects_non_pdf(api_client: TestClient) -> None:
    resp = api_client.post("/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 415
