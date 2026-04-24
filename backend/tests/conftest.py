"""Shared pytest fixtures.

`api_client` spins up a FastAPI TestClient pointed at a temp data_dir so
route tests can write seed JSON without touching the repo-level data/.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from readily.config import Settings
from readily.interface.api.app import create_app
from readily.interface.api.deps import get_settings


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def tmp_sample_dir(tmp_path: Path) -> Path:
    d = tmp_path / "sample-data"
    d.mkdir()
    return d


@pytest.fixture
def settings(tmp_data_dir: Path, tmp_sample_dir: Path) -> Settings:
    return Settings(
        gemini_api_key="test-key",  # type: ignore[call-arg]
        data_dir=tmp_data_dir,
        sample_data_dir=tmp_sample_dir,
    )


@pytest.fixture
def api_client(settings: Settings) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")
