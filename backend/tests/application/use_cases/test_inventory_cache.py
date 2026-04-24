"""Tests for the hash-keyed inventory cache built by `build_inventory`."""

import json
from pathlib import Path
from typing import Any

import readily.application.use_cases.build_inventory as invmod
from readily.application.use_cases.build_inventory import (
    InventoryMetaResponse,
    build_inventory,
    load_inventory,
    update_inventory_with_full_ingest,
)
from readily.domain.entities import PolicyMeta


class _RepeatingStubGemini:
    """Stub that returns the same parsed response for every call. Used here because
    `build_inventory` may make 1..N calls depending on cache state and the test
    writers in this file don't want to enumerate each one."""

    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[tuple[str, Any]] = []

    def generate_structured(self, prompt: str, schema: Any) -> Any:
        self.calls.append((prompt, schema))
        if isinstance(self.response, InventoryMetaResponse):
            return self.response
        return InventoryMetaResponse.model_validate(self.response)


def _write_pdf(tmp_path: Path, name: str, content: bytes = b"dummy pdf bytes") -> Path:
    p = tmp_path / name
    p.write_bytes(content)
    return p


def test_build_inventory_calls_llm_once_per_new_pdf(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(invmod, "pdf_to_text", lambda path, first_page=1, last_page=1: "page1 text")
    _write_pdf(tmp_path, "GG.1234_CEO.pdf", b"alpha")
    _write_pdf(tmp_path, "AA.1000_CEO.pdf", b"beta")
    client = _RepeatingStubGemini(
        {
            "code": "GG.1234",
            "title": "Hospice Coverage",
            "applicable_to": ["Medi-Cal"],
            "document_topics": ["hospice"],
            "entity_refs": ["APL 25-008"],
        }
    )
    cache_path = tmp_path / "inventory.json"
    metas = build_inventory(str(tmp_path / "*.pdf"), client=client, cache_path=cache_path)
    assert len(metas) == 2
    assert len(client.calls) == 2, "one LLM call per new PDF"
    assert cache_path.exists()
    data = json.loads(cache_path.read_text())
    assert data["version"] == 1
    assert len(data["entries"]) == 2
    assert all("hash" in e for e in data["entries"])


def test_build_inventory_reuses_cached_entries_for_unchanged_bytes(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(invmod, "pdf_to_text", lambda path, first_page=1, last_page=1: "page1")
    _write_pdf(tmp_path, "GG.1234_CEO.pdf", b"same bytes")
    client = _RepeatingStubGemini(
        {
            "code": "GG.1234",
            "title": "X",
            "applicable_to": ["Medi-Cal"],
            "document_topics": [],
            "entity_refs": [],
        }
    )
    cache_path = tmp_path / "inventory.json"
    build_inventory(str(tmp_path / "*.pdf"), client=client, cache_path=cache_path)
    assert len(client.calls) == 1

    # Re-run with the same bytes — should hit cache, zero new calls.
    client.calls.clear()
    metas = build_inventory(str(tmp_path / "*.pdf"), client=client, cache_path=cache_path)
    assert len(client.calls) == 0, "unchanged PDF must not trigger another LLM call"
    assert len(metas) == 1
    assert metas[0].code == "GG.1234"


def test_build_inventory_rebuilds_changed_pdfs(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(invmod, "pdf_to_text", lambda path, first_page=1, last_page=1: "page1")
    _write_pdf(tmp_path, "GG.1234_CEO.pdf", b"v1")
    client = _RepeatingStubGemini(
        {
            "code": "GG.1234",
            "title": "v1 title",
            "applicable_to": ["Medi-Cal"],
            "document_topics": [],
            "entity_refs": [],
        }
    )
    cache_path = tmp_path / "inventory.json"
    build_inventory(str(tmp_path / "*.pdf"), client=client, cache_path=cache_path)

    _write_pdf(tmp_path, "GG.1234_CEO.pdf", b"v2-different-bytes")
    client2 = _RepeatingStubGemini(
        {
            "code": "GG.1234",
            "title": "v2 title",
            "applicable_to": ["Medi-Cal"],
            "document_topics": [],
            "entity_refs": [],
        }
    )
    metas = build_inventory(str(tmp_path / "*.pdf"), client=client2, cache_path=cache_path)
    assert len(client2.calls) == 1, "changed bytes should trigger a fresh LLM call"
    assert metas[0].title == "v2 title"


def test_load_inventory_returns_metas_without_llm(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(invmod, "pdf_to_text", lambda path, first_page=1, last_page=1: "page1")
    _write_pdf(tmp_path, "GG.1234_CEO.pdf", b"bytes")
    client = _RepeatingStubGemini(
        {
            "code": "GG.1234",
            "title": "Y",
            "applicable_to": ["Medi-Cal"],
            "document_topics": ["topic"],
            "entity_refs": [],
        }
    )
    cache_path = tmp_path / "inventory.json"
    build_inventory(str(tmp_path / "*.pdf"), client=client, cache_path=cache_path)

    loaded = load_inventory(cache_path)
    assert len(loaded) == 1
    assert loaded[0].code == "GG.1234"
    assert loaded[0].document_topics == ["topic"]


def test_load_inventory_returns_empty_when_no_cache(tmp_path: Path):
    assert load_inventory(tmp_path / "does-not-exist.json") == []


def test_update_inventory_with_full_ingest_backfills_entry(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(invmod, "pdf_to_text", lambda path, first_page=1, last_page=1: "page1")
    pdf = _write_pdf(tmp_path, "GG.1234_CEO.pdf", b"b1")
    client = _RepeatingStubGemini(
        {
            "code": "GG.1234",
            "title": "seed",
            "applicable_to": ["Medi-Cal"],
            "document_topics": ["hospice"],
            "entity_refs": [],
        }
    )
    cache_path = tmp_path / "inventory.json"
    build_inventory(str(tmp_path / "*.pdf"), client=client, cache_path=cache_path)

    enriched = PolicyMeta(
        code="GG.1234",
        file_path=str(pdf),
        title="Fully Ingested Title",
        applicable_to=["Medi-Cal"],
        document_topics=["hospice", "palliative", "benefit period"],
        entity_refs=["APL 25-008", "DHCS"],
    )
    update_inventory_with_full_ingest(cache_path, enriched)

    reloaded = load_inventory(cache_path)
    assert reloaded[0].document_topics == ["hospice", "palliative", "benefit period"]
    assert reloaded[0].entity_refs == ["APL 25-008", "DHCS"]
    assert reloaded[0].title == "Fully Ingested Title"
