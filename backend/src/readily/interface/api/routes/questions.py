from __future__ import annotations

from fastapi import APIRouter, HTTPException

from readily.config import Settings
from readily.domain.entities import Question
from readily.interface.api._fallback import load_or_sample
from readily.interface.api.deps import SettingsDep

router = APIRouter(tags=["questions"])


def _load(settings: Settings) -> list[Question]:
    items, _ = load_or_sample(
        settings.questions_json,
        settings.sample_data_dir / "questions.json",
        Question,
    )
    return items


@router.get("/questions", response_model=list[Question])
def list_questions(settings: SettingsDep) -> list[Question]:
    return _load(settings)


@router.get("/questions/{number}", response_model=Question)
def get_question(number: int, settings: SettingsDep) -> Question:
    for q in _load(settings):
        if q.number == number:
            return q
    raise HTTPException(status_code=404, detail=f"Question {number} not found")
