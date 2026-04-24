"""Shared data-loading helper for read routes.

When `data/*.json` is missing or empty, fall back to the bundled sample
fixtures in `backend/sample-data/`. Returns `(items, using_sample)` so the
route can surface the fallback via `/info`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from readily.infrastructure.storage.json_store import load_list

T = TypeVar("T", bound=BaseModel)


def load_or_sample(primary: Path, sample: Path, model: type[T]) -> tuple[list[T], bool]:
    if primary.exists() and primary.stat().st_size > 2:
        return load_list(primary, model), False
    if sample.exists():
        return load_list(sample, model), True
    return [], True
