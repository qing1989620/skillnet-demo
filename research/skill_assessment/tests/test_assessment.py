"""Negative controls for evidence, preflight and independent artifact checks."""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from research.skill_assessment.boundary import Clause, Contract, preflight
from research.skill_assessment.evidence import Bundle, Citation, SourceFile
from research.skill_assessment.static_checks import inspect_package
from research.skill_assessment.verifier import (
    CSV_INPUT,
    mutation_diagnostics,
    reference_fixture,
    verify_artifact,
)
from research.skill_quality.manifest import safe_read


def bundle(text: str, extra: dict[str, str] | None = None) -> Bundle:
    files = {"SKILL.md": text, **(extra or {})}
    return Bundle(
        "f" * 64,
        "fixture",
        "owned",
        "owned",
        "SKILL.md",
        {
            path: SourceFile(path, hashlib.sha256(content.encode("utf-8")).hexdigest(), content)
            for path, content in files.items()
        },
    )


@pytest.fixture
def source() -> Bundle:
    return bundle("requires permission\nnot a security certificate\nrisk: safe\n")


@pytest.fixture
def contract(source: Bundle) -> Contract:
    evidence = (source.cite("SKILL.md", 1),)
    return Contract(
        "test",
        ("audit",),
        ("certificate",),
        (Clause("permission", True, "Need permission", "source_declared", evidence),),
        (Clause("delete_shared", True, "Never delete shared data", "reviewer_operationalization", evidence),),
        "owned negative-control contract",
        (source.cite("SKILL.md", 2),),
    )


@pytest.mark.parametrize(
    "change",
    [
        {"sha256": "0" * 64},
        {"path": "outside.md"},
        {"start_line": 0},
        {"end_line": 99},
        {"start_line": 2, "end_line": 1},
        {"quote": "fabricated"},
        {"start_line": True},
    ],
)
def test_forged_citations_are_rejected(source: Bundle, change: dict) -> None:
    citation = replace(source.cite("SKILL.md", 1), **change)
    with pytest.raises(ValueError):
        source.verify(citation)


def test_real_quote_does_not_certify_relevance_or_safety(source: Bundle) -> None:
    # This quote genuinely exists, but cannot support "safe to execute".
    source.verify(source.cite("SKILL.md", 3))
    result = inspect_package(source)
    assert result["self_attestations"][0]["meaning"] == "author_claim_not_independent_safety_evidence"
    assert result["safety_verdict"] == "not_established"


def test_untrusted_source_is_parsed_without_running(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-exist"
    code = f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
    code += "parser.add_argument('--file', required=True)\n"
    source = bundle("python3 scripts/check.py --file input.csv --invented\n", {"scripts/check.py": code})
    result = inspect_package(source)
    assert result["cli_checks"][0]["not_found_flags"] == ["--invented"]
    assert not marker.exists()
    assert result["executed_community_code"] is False


def test_literal_flags_do_not_mean_runtime_pass() -> None:
    source = bundle(
        "python3 scripts/a.py --file x.csv\n",
        {"scripts/a.py": "raise RuntimeError('always fails')\nparser.add_argument('--file')\n"},
    )
    result = inspect_package(source)["cli_checks"][0]
    assert result["status"] == "literal_flags_found"
    assert "runtime_success" in result["not_proven"]


def test_missing_link_and_constant_measurement_are_review_leads() -> None:
    source = bundle(
        "See **references/missing.md** and `scripts/a.py`.\n",
        {"scripts/a.py": "# Timeliness placeholder\ntimeliness = 85.0\n"},
    )
    result = inspect_package(source)
    assert result["missing_resources"][0]["target"] == "references/missing.md"
    assert result["default_measurements"][0]["dimension"] == "timeliness"
    assert result["safety_verdict"] == "not_established"


@pytest.mark.parametrize(
    "task,facts,expected",
    [
        ("audit", {"permission": True, "delete_shared": False}, "matches_documented_conditions_not_executed"),
        ("audit", {"permission": False, "delete_shared": False}, "preconditions_unmet"),
        ("audit", {"delete_shared": False}, "preconditions_unknown"),
        ("audit", {"permission": True}, "preconditions_unknown"),
        ("audit", {"permission": True, "delete_shared": True}, "prohibited_action_in_declared_contract"),
        ("certificate", {"permission": True, "delete_shared": False}, "outside_declared_scope"),
        ("unlisted", {"permission": True, "delete_shared": False}, "scope_unknown"),
    ],
)
def test_boundary_negative_controls(contract: Contract, task: str, facts: dict, expected: str) -> None:
    result = preflight(contract, task, facts)
    assert result["status"] == expected
    assert result["execution_verified"] is False
    assert result["utility"] == "not_measured"


def test_string_true_is_not_authenticated_permission(contract: Contract) -> None:
    with pytest.raises(ValueError, match="type mismatch"):
        preflight(contract, "audit", {"permission": "true", "delete_shared": False})


@pytest.mark.parametrize("relative", ["../outside", "C:/outside", "a\\b", "/outside", "a/../b"])
def test_source_path_escape_is_rejected(tmp_path: Path, relative: str) -> None:
    with pytest.raises(ValueError):
        safe_read(tmp_path, relative)


def test_reference_oracle_cross_checked_from_input() -> None:
    # An independent calculation cross-checks the hand-constructed oracle.
    rows = list(csv.DictReader(io.StringIO(CSV_INPUT)))
    known = reference_fixture()
    assert len(rows) == known["row_count"]
    assert {k: sum(r[k] == "" for r in rows) for k in rows[0]} == known["missing_by_column"]
    assert len(rows) - len({tuple(r.values()) for r in rows}) == known["duplicate_extra_rows"]
    ages = [(date(2026, 11, 5) - date.fromisoformat(r["observed_at"])).days for r in rows]
    assert sum(age > 7 for age in ages) == known["stale_rows"]
    assert max(ages) == known["max_age_days"]


def test_mutation_controls_reject_false_successes() -> None:
    diagnostics = mutation_diagnostics()
    assert len([d for d in diagnostics if d["expected_accept"]]) == 1
    assert len([d for d in diagnostics if not d["expected_accept"]]) == 10
    assert all(d["diagnostic_pass"] for d in diagnostics)
    assert not verify_artifact({"score": 100, "safe": True})["task_success"]


def test_source_object_tampering_fails(source: Bundle) -> None:
    old = source.cite("SKILL.md", 1)
    source.files["SKILL.md"] = replace(source.files["SKILL.md"], text="changed")
    with pytest.raises(ValueError, match="changed"):
        source.verify(old)


def test_invalid_coordinate_types_rejected(source: Bundle) -> None:
    with pytest.raises(ValueError):
        source.cite("SKILL.md", True)
    with pytest.raises(ValueError):
        source.verify(Citation("SKILL.md", source.files["SKILL.md"].sha256, 1.0, 1, "requires permission"))
