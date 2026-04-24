from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import write_json


def test_info_reports_unready_when_data_missing(api_client: TestClient) -> None:
    resp = api_client.get("/info")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "ready": False,
        "using_sample": True,
        "has_questions": False,
        "has_policies": False,
        "has_results": False,
    }


def test_info_reports_ready_when_all_three_present(api_client: TestClient, settings) -> None:
    write_json(settings.questions_json, [{"stub": True}])
    write_json(settings.policies_json, [{"stub": True}])
    write_json(settings.results_json, [{"stub": True}])

    resp = api_client.get("/info")
    body = resp.json()
    assert body["ready"] is True
    assert body["using_sample"] is False
