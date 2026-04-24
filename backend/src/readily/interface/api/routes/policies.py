from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from readily.config import Settings
from readily.domain.entities import PolicyDoc
from readily.interface.api._fallback import load_or_sample
from readily.interface.api.deps import SettingsDep

router = APIRouter(tags=["policies"])


def _load(settings: Settings) -> list[PolicyDoc]:
    items, _ = load_or_sample(
        settings.policies_json,
        settings.sample_data_dir / "policies.json",
        PolicyDoc,
    )
    return items


@router.get("/policies", response_model=list[PolicyDoc])
def list_policies(settings: SettingsDep) -> list[PolicyDoc]:
    return _load(settings)


@router.get("/policy/{code}/pdf")
def get_policy_pdf(code: str, settings: SettingsDep) -> FileResponse:
    for doc in _load(settings):
        if doc.meta.code == code:
            pdf_path = Path(doc.meta.file_path)
            if not pdf_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"PDF for {code} referenced at {pdf_path} is missing",
                )
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=pdf_path.name,
            )
    raise HTTPException(status_code=404, detail=f"Policy {code} not found")
