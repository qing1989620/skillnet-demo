from __future__ import annotations

import hashlib
from pathlib import Path

from research.skill_study.bind_judge_evidence import bind_registered
from research.skill_study.deepseek_pilot import Citation


def setup_source(tmp_path: Path) -> tuple[dict, Citation]:
    target = tmp_path / "package"
    target.mkdir()
    data = b"first line\nsecond line\n"
    (target / "file.md").write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    inventory = {"file.md": (sha, len(data))}
    citation = Citation(
        path="file.md", sha256=sha, start_line=1, end_line=1, exact_quote="first line", relation="support"
    )
    return inventory, citation


def test_binding_does_not_turn_an_existing_quote_into_semantic_or_runtime_proof(tmp_path: Path) -> None:
    inventory, citation = setup_source(tmp_path)
    result = bind_registered(tmp_path, "package", inventory, citation, {"file.md"})
    assert result["status"] == "source_window_bound"
    assert result["model_quote_exact"] is True
    assert result["semantic_support"] == result["runtime_ability"] == "not_assessed"


def test_model_paths_cannot_fetch_an_unregistered_file(tmp_path: Path) -> None:
    inventory, citation = setup_source(tmp_path)
    citation = citation.model_copy(update={"path": "../private"})
    assert bind_registered(tmp_path, "package", inventory, citation, set())["status"] == "unregistered_path"


def test_changed_resource_cannot_inherit_a_frozen_version(tmp_path: Path) -> None:
    inventory, citation = setup_source(tmp_path)
    (tmp_path / "package/file.md").write_bytes(b"rewritten source")
    assert (
        bind_registered(tmp_path, "package", inventory, citation, set())["status"]
        == "registered_resource_changed"
    )


def test_system_fetch_and_model_quote_error_remain_visible(tmp_path: Path) -> None:
    inventory, citation = setup_source(tmp_path)
    citation = citation.model_copy(update={"exact_quote": "model paraphrase"})
    result = bind_registered(tmp_path, "package", inventory, citation, set())
    assert result["origin"] == "additional_registered_resource_fetch"
    assert result["model_quote_exact"] is False
    assert result["server_extracted_quote"] == "first line"
    assert result["model_quote_preserved"] == "model paraphrase"


def test_model_version_conflict_is_not_silently_replaced(tmp_path: Path) -> None:
    inventory, citation = setup_source(tmp_path)
    citation = citation.model_copy(update={"sha256": "b" * 64})
    assert (
        bind_registered(tmp_path, "package", inventory, citation, set())["status"]
        == "claimed_version_conflict"
    )
