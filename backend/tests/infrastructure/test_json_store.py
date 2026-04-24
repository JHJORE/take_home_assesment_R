from __future__ import annotations

from pathlib import Path

from readily.domain.entities import Claim, ClaimMetadata
from readily.infrastructure.storage.json_store import load_list, save_list


def test_save_then_load_roundtrips_claims(tmp_path: Path) -> None:
    items = [
        Claim(
            claim="MCPs must respond within 14 days.",
            source_text="within 14 days",
            page=3,
            metadata=ClaimMetadata(
                topic_keywords=["response time"],
                entity_refs=["MCP"],
            ),
        )
    ]
    target = tmp_path / "claims.json"

    save_list(target, items)
    loaded = load_list(target, Claim)

    assert len(loaded) == 1
    assert loaded[0].claim == items[0].claim
    assert loaded[0].page == 3
    assert loaded[0].metadata.topic_keywords == ["response time"]


def test_save_emits_pretty_utf8(tmp_path: Path) -> None:
    items = [Claim(claim="Señor § 1", source_text="Señor § 1", metadata=ClaimMetadata())]
    target = tmp_path / "claims.json"
    save_list(target, items)
    text = target.read_text(encoding="utf-8")
    assert "Señor" in text
    assert "\n" in text


def test_load_list_empty_file_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "empty.json"
    save_list(target, [])
    assert load_list(target, Claim) == []
