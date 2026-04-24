from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import write_json


def _result(question_number: int) -> dict:
    return {
        "question_number": question_number,
        "question_claim": {
            "claim": "stub",
            "source_text": "stub",
            "page": None,
            "metadata": {
                "topic_keywords": [],
                "entity_refs": [],
            },
        },
        "best_match": None,
        "contradictions": [],
    }


def test_list_results(api_client: TestClient, settings) -> None:
    write_json(settings.results_json, [_result(1), _result(2)])
    resp = api_client.get("/results")
    assert resp.status_code == 200
    assert [r["question_number"] for r in resp.json()] == [1, 2]


def test_list_results_filtered_by_question_number(api_client: TestClient, settings) -> None:
    write_json(settings.results_json, [_result(1), _result(2), _result(1)])
    resp = api_client.get("/results?question_number=1")
    assert [r["question_number"] for r in resp.json()] == [1, 1]
