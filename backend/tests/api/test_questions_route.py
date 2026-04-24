from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import write_json


def _question(number: int, text: str = "Does the P&P require X?") -> dict:
    return {
        "number": number,
        "text": text,
        "reference": "APL 24-004",
        "candidate_codes": [],
        "metadata": {"lob": [], "reference": "", "question_topics": []},
        "claims": [],
    }


def test_list_questions_falls_back_to_sample(api_client: TestClient, settings) -> None:
    write_json(settings.sample_data_dir / "questions.json", [_question(1)])
    resp = api_client.get("/questions")
    assert resp.status_code == 200
    assert [q["number"] for q in resp.json()] == [1]


def test_list_questions_prefers_primary(api_client: TestClient, settings) -> None:
    write_json(settings.sample_data_dir / "questions.json", [_question(99)])
    write_json(settings.questions_json, [_question(1), _question(2)])
    resp = api_client.get("/questions")
    assert [q["number"] for q in resp.json()] == [1, 2]


def test_get_question_by_number(api_client: TestClient, settings) -> None:
    write_json(settings.questions_json, [_question(1), _question(2)])
    resp = api_client.get("/questions/2")
    assert resp.status_code == 200
    assert resp.json()["number"] == 2


def test_get_question_404_when_unknown(api_client: TestClient, settings) -> None:
    write_json(settings.questions_json, [_question(1)])
    resp = api_client.get("/questions/42")
    assert resp.status_code == 404
