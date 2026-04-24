from __future__ import annotations

import subprocess
from pathlib import Path


def pdf_to_text(
    pdf_path: Path | str, first_page: int | None = None, last_page: int | None = None
) -> str:
    """Run `pdftotext -layout` against a PDF and return its text.

    Requires poppler-utils (`brew install poppler`).
    Preserves column layout so section headers and indented bullet structure are intact.
    """
    cmd = ["pdftotext", "-layout"]
    if first_page is not None:
        cmd += ["-f", str(first_page)]
    if last_page is not None:
        cmd += ["-l", str(last_page)]
    cmd += [str(pdf_path), "-"]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def pages(
    pdf_path: Path | str,
    first_page: int | None = None,
    last_page: int | None = None,
) -> list[str]:
    """Return a list of pages (one string per page).

    Uses the form-feed char `pdftotext` emits between pages. When `first_page`
    or `last_page` is set, the returned list covers only that slice; the caller
    is responsible for knowing the absolute page number of the first element
    (= `first_page or 1`).
    """
    full = pdf_to_text(pdf_path, first_page=first_page, last_page=last_page)
    # pdftotext separates pages with \f (form feed). Trailing empty page possible.
    parts = full.split("\f")
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return parts
