from pathlib import Path

from readily.application.use_cases.build_inventory import policy_inventory


def test_policy_inventory_extracts_code_from_caloptima_filename(tmp_path: Path):
    (tmp_path / "GG.1234_CEO20250206_v20250201.pdf").write_bytes(b"")
    (tmp_path / "AA.1000_CEO20250206_v20250201.pdf").write_bytes(b"")
    inv = policy_inventory(str(tmp_path / "*.pdf"))
    codes = {m.code for m in inv}
    assert codes == {"GG.1234", "AA.1000"}
    assert all(m.title is None for m in inv), "title is populated later by LLM ingest, not here"
    assert all(m.file_path.endswith(".pdf") for m in inv)


def test_policy_inventory_falls_back_to_full_stem_for_uncoded_filenames(tmp_path: Path):
    (tmp_path / "random-policy-name.pdf").write_bytes(b"")
    inv = policy_inventory(str(tmp_path / "*.pdf"))
    assert len(inv) == 1
    assert inv[0].code == "random-policy-name"


def test_policy_inventory_empty_glob_returns_empty(tmp_path: Path):
    inv = policy_inventory(str(tmp_path / "*.pdf"))
    assert inv == []
