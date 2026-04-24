from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter

T = TypeVar("T", bound=BaseModel)


def save_list(path: Path | str, items: Sequence[BaseModel]) -> None:
    payload = [item.model_dump(mode="json") for item in items]
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_list(path: Path | str, model: type[T]) -> list[T]:
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    adapter: TypeAdapter[list[T]] = TypeAdapter(list[model])  # type: ignore[valid-type]
    return adapter.validate_python(data)
