"""FastAPI dependency providers.

Each provider is a factory function registered with `Depends()`. Settings is
cached for the app lifetime; per-request callers get the same instance. Heavy
adapters (`GoogleGeminiClient`) are only constructed where they're needed —
the read-only endpoints never touch them.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from readily.config import Settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


SettingsDep = Annotated[Settings, Depends(get_settings)]
