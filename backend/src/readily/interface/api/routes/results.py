from __future__ import annotations

from fastapi import APIRouter

from readily.config import Settings
from readily.domain.entities import QuestionClaimResult
from readily.interface.api._fallback import load_or_sample
from readily.interface.api.deps import SettingsDep

router = APIRouter(tags=["results"])


def _load(settings: Settings) -> list[QuestionClaimResult]:
    items, _ = load_or_sample(
        settings.results_json,
        settings.sample_data_dir / "results.json",
        QuestionClaimResult,
    )
    return items


@router.get("/results", response_model=list[QuestionClaimResult])
def list_results(
    settings: SettingsDep,
    question_number: int | None = None,
) -> list[QuestionClaimResult]:
    results = _load(settings)
    if question_number is not None:
        return [r for r in results if r.question_number == question_number]
    return results
