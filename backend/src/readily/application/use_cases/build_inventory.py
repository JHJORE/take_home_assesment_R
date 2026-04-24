from __future__ import annotations

import glob as _glob
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

from readily.domain.entities import PolicyMeta
from readily.infrastructure.llm.gemini import GeminiClient
from readily.infrastructure.llm.prompts import INVENTORY_POLICY_PROMPT
from readily.infrastructure.pdf.pdftotext import pdf_to_text

CACHE_VERSION = 1


class InventoryMetaResponse(BaseModel):
    """Response schema for INVENTORY_POLICY_PROMPT (one page-1 call per PDF).

    Mirrors PolicyMeta without `file_path` — that's set by the caller from the
    glob path, not the LLM.
    """

    code: str | None = None
    title: str | None = None
    applicable_to: list[str] = Field(default_factory=list)
    document_topics: list[str] = Field(default_factory=list)
    entity_refs: list[str] = Field(default_factory=list)


class InventoryEntry(BaseModel):
    hash: str
    file_path: str
    meta: PolicyMeta


def policy_inventory(glob_pattern: str) -> list[PolicyMeta]:
    """Cheap filename-only inventory. No LLM, no cache, no PDF reads."""
    out: list[PolicyMeta] = []
    for path in sorted(_glob.glob(glob_pattern)):
        stem = Path(path).stem
        code = stem.split("_", 1)[0]
        out.append(PolicyMeta(code=code, file_path=path))
    return out


def build_inventory(
    glob_pattern: str,
    client: GeminiClient,
    cache_path: Path | str = Path("data/inventory.json"),
) -> list[PolicyMeta]:
    """Build (or refresh) a rich policy inventory, keyed by file-content hash."""
    cache = _load_cache(Path(cache_path))
    by_hash: dict[str, InventoryEntry] = {e.hash: e for e in cache}

    out: list[PolicyMeta] = []
    fresh_entries: list[InventoryEntry] = []
    for path_str in sorted(_glob.glob(glob_pattern)):
        path = Path(path_str)
        digest = _file_sha256(path)
        cached = by_hash.get(digest)
        if cached is not None:
            if cached.file_path != path_str:
                cached.file_path = path_str
                cached.meta.file_path = path_str
            fresh_entries.append(cached)
            out.append(cached.meta)
            continue
        meta = _extract_inventory_meta(path, client=client)
        entry = InventoryEntry(hash=digest, file_path=path_str, meta=meta)
        fresh_entries.append(entry)
        out.append(meta)

    _save_cache(Path(cache_path), fresh_entries)
    return out


def load_inventory(
    cache_path: Path | str = Path("data/inventory.json"),
) -> list[PolicyMeta]:
    """Load a previously-built inventory cache. Returns an empty list if no cache."""
    cache = _load_cache(Path(cache_path))
    return [e.meta for e in cache]


def update_inventory_with_full_ingest(
    cache_path: Path | str,
    enriched: PolicyMeta,
) -> None:
    """Back-fill a cache entry with richer metadata from the full-document ingest."""
    cache = _load_cache(Path(cache_path))
    for entry in cache:
        if entry.meta.code == enriched.code:
            entry.meta = enriched.model_copy(update={"file_path": entry.file_path})
            break
    _save_cache(Path(cache_path), cache)


def _extract_inventory_meta(pdf_path: Path, *, client: GeminiClient) -> PolicyMeta:
    page_text = pdf_to_text(pdf_path, first_page=1, last_page=1)
    prompt = INVENTORY_POLICY_PROMPT.format(page_text=page_text)
    response: InventoryMetaResponse = client.generate_structured(prompt, InventoryMetaResponse)

    code = (response.code or pdf_path.stem.split("_", 1)[0]).strip()
    return PolicyMeta(
        code=code,
        file_path=str(pdf_path),
        title=(response.title or "").strip() or None,
        applicable_to=response.applicable_to,
        document_topics=response.document_topics,
        entity_refs=response.entity_refs,
    )


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_cache(cache_path: Path) -> list[InventoryEntry]:
    if not cache_path.exists():
        return []
    try:
        data = json.loads(cache_path.read_text())
    except json.JSONDecodeError:
        return []
    entries_raw = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries_raw, list):
        return []
    entries: list[InventoryEntry] = []
    for raw in entries_raw:
        try:
            entries.append(InventoryEntry.model_validate(raw))
        except Exception:
            continue
    return entries


def _save_cache(cache_path: Path, entries: list[InventoryEntry]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    data = {"version": CACHE_VERSION, "entries": [e.model_dump() for e in entries]}
    cache_path.write_text(json.dumps(data, indent=2))
