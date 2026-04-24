from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from readily.interface.api.deps import SettingsDep

router = APIRouter(tags=["info"])


class Info(BaseModel):
    ready: bool
    using_sample: bool
    has_questions: bool
    has_policies: bool
    has_results: bool


def _nonempty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 2


@router.get("/info", response_model=Info)
def info(settings: SettingsDep) -> Info:
    has_q = _nonempty(settings.questions_json)
    has_p = _nonempty(settings.policies_json)
    has_r = _nonempty(settings.results_json)
    ready = has_q and has_p and has_r
    return Info(
        ready=ready,
        using_sample=not ready,
        has_questions=has_q,
        has_policies=has_p,
        has_results=has_r,
    )
