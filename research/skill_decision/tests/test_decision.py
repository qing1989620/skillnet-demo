from __future__ import annotations

import copy
from pathlib import Path

import pytest

from research.skill_decision.benchmark import make_static_cases
from research.skill_decision.gate import Bundle, evaluate, from_texts
from research.skill_decision.owned import make_inputs, program_bundle, run_owned, verify_output


def test_document_quality_cannot_mask_broken_version_or_interface() -> None:
    cases = make_static_cases()
    for kind in [
        "unknown_option",
        "missing_required",
        "invalid_choice",
        "wrong_type",
        "missing_entry",
        "tampered_resource",
        "syntax_error",
    ]:
        case = next(c for c in cases if c["kind"] == kind)
        result = evaluate(Bundle(**case["bundle"]))
        assert result["decision"] == "repair_required", kind
        assert result["findings"][0]["evidence"]["path"]


def test_consulting_skill_is_unknown_not_bad_due_to_missing_scripts() -> None:
    result = evaluate(
        from_texts("consulting", {"SKILL.md": "# Review\nDiscuss the user's scientific design."})
    )
    assert result["decision"] == "insufficient_evidence" and not result["findings"]


def test_forged_or_cross_version_runtime_success_cannot_create_acceptance() -> None:
    bundle = program_bundle("sum_correct")
    fake = {
        "receipt_id": "fake",
        "bundle_fingerprint": bundle.fingerprint,
        "task_family": "integer_sum",
        "n": 24,
        "passed": 24,
    }
    assert evaluate(bundle, task_family="integer_sum", behavior=fake)["decision"] == "insufficient_evidence"
    fake["bundle_fingerprint"] = "wrong-version"
    assert (
        evaluate(bundle, task_family="integer_sum", behavior=fake, trusted_behavior_ids=frozenset({"fake"}))[
            "decision"
        ]
        == "insufficient_evidence"
    )


def test_partial_success_and_wrong_task_cannot_be_reported_as_general_good() -> None:
    bundle = program_bundle("sum_correct")
    receipt = {
        "receipt_id": "registered",
        "bundle_fingerprint": bundle.fingerprint,
        "task_family": "integer_sum",
        "n": 24,
        "passed": 23,
    }
    options = {"behavior": receipt, "trusted_behavior_ids": frozenset({"registered"})}
    assert evaluate(bundle, task_family="integer_sum", **options)["decision"] == "repair_required"
    assert evaluate(bundle, task_family="directed_order", **options)["decision"] == "outside_tested_scope"


def test_non_strict_parser_and_factory_are_not_false_defects() -> None:
    case = next(c for c in make_static_cases() if c["kind"] == "unsupported_factory")
    assert evaluate(Bundle(**case["bundle"]))["decision"] == "insufficient_evidence"
    bundle = from_texts(
        "known-args",
        {
            "SKILL.md": "python main.py --unlisted 2",
            "main.py": "import argparse\np=argparse.ArgumentParser()\np.add_argument('--file')\np.parse_known_args()",
        },
    )
    assert evaluate(bundle)["decision"] == "insufficient_evidence"


def test_parent_split_is_disjoint_and_labels_are_not_detector_inputs() -> None:
    cases = make_static_cases()
    dev = {r["parent"] for r in cases if r["split"] == "development"}
    test = {r["parent"] for r in cases if r["split"] == "test"}
    assert len(dev) == 40 and len(test) == 20 and not dev & test
    assert len(cases) == 600
    assert not any("known_defect" in r["bundle"] for r in cases)


def test_graph_oracle_accepts_equivalent_orders_and_rejects_wrong_edges() -> None:
    fixture = {
        "family": "directed_order",
        "input": {"nodes": ["a", "b", "c"], "edges": [["a", "c"]]},
        "truth": "dag",
    }
    assert verify_output(fixture, {"status": "ok", "order": ["a", "b", "c"]})
    assert verify_output(fixture, {"status": "ok", "order": ["b", "a", "c"]})
    assert not verify_output(fixture, {"status": "ok", "order": ["c", "b", "a"]})
    assert not verify_output(fixture, {"status": "ok", "order": ["a", "c", "c"]})


def test_registry_runner_rejects_modified_package_code() -> None:
    bundle = program_bundle("sum_correct")
    files = copy.deepcopy(bundle.files)
    files["scripts/run.py"] += "raise RuntimeError('not registry bytes')\n"
    changed = Bundle(bundle.identity, files, bundle.expected_hashes, bundle.examples)
    with pytest.raises(ValueError, match="authored registry"):
        run_owned(changed, "sum_correct", make_inputs()[:3])


def test_same_family_with_unseen_input_is_outside_observed_ability() -> None:
    bundle = program_bundle("sum_correct")
    receipt = {
        "receipt_id": "registered",
        "bundle_fingerprint": bundle.fingerprint,
        "task_family": "integer_sum",
        "n": 24,
        "passed": 24,
        "input_outcomes": {"known": {"n": 1, "passed": 1}},
    }
    options = {
        "task_family": "integer_sum",
        "behavior": receipt,
        "trusted_behavior_ids": frozenset({"registered"}),
    }
    assert evaluate(bundle, task_input_sha256="unseen", **options)["decision"] == "outside_tested_scope"
    assert evaluate(bundle, task_input_sha256="known", **options)["decision"] == "tested_pass_within_scope"


def test_boolean_counts_cannot_fabricate_valid_runtime_evidence() -> None:
    bundle = program_bundle("sum_correct")
    receipt = {
        "receipt_id": "registered",
        "bundle_fingerprint": bundle.fingerprint,
        "task_family": "integer_sum",
        "n": True,
        "passed": True,
    }
    with pytest.raises(ValueError, match="counts"):
        evaluate(
            bundle,
            task_family="integer_sum",
            behavior=receipt,
            trusted_behavior_ids=frozenset({"registered"}),
        )


def test_actual_owned_program_output_separates_success_from_stub(tmp_path: Path) -> None:
    fixtures = [f for f in make_inputs() if f["family"] == "integer_sum"][:2]
    for program, expected in [("sum_correct", 2), ("sum_stub", 0)]:
        bundle = program_bundle(program)
        receipt, outputs = run_owned(bundle, program, fixtures)
        assert receipt["passed"] == expected and len(outputs) == 2
        result = evaluate(
            bundle,
            task_family="integer_sum",
            behavior=receipt,
            trusted_behavior_ids=frozenset({receipt["receipt_id"]}),
        )
        assert result["decision"] == ("tested_pass_within_scope" if expected else "repair_required")
