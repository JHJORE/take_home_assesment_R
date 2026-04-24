"""POST /upload — stub handler.

Intentionally does not trigger the pipeline; the pipeline runs offline via
the CLI. This route exists only so the frontend's upload gate can move past
its sessionStorage check after dropping a real PDF.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from readily.interface.api.deps import SettingsDep

router = APIRouter(tags=["upload"])


class UploadResponse(BaseModel):
    filename: str
    path: str
    bytes: int


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile,
    settings: SettingsDep,
) -> UploadResponse:
    if file.content_type != "application/pdf" and not (
        file.filename and file.filename.lower().endswith(".pdf")
    ):
        raise HTTPException(status_code=415, detail="Only PDFs are accepted")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    filename = file.filename or "upload.pdf"
    dest = settings.upload_dir / filename
    payload = await file.read()
    dest.write_bytes(payload)
    return UploadResponse(filename=filename, path=str(dest), bytes=len(payload))
