from __future__ import annotations

from copy import deepcopy

import pytest

from research.skill_quality.execution_eval import require_execution_approval, verify_sum_fixture
from research.skill_quality.manifest import canonical
from research.skill_quality.pairwise_judge import swap_consistent
from research.skill_quality.ranker import quality_feature, replay
from research.skill_quality.schemas import Evidence
from research.skill_quality.statistics import holm, paired_family_bootstrap

from .conftest import make_rating


def test_shadow_disabled_is_canonical_equivalent_and_detached():
    capture = {"selected": ["s"], "candidates": [{"name": "s", "score": 0.5, "rank": 1}]}
    result = replay(capture, enable_shadow=False, policy="evidence")
    assert canonical(result) == canonical(capture)
    result["selected"].clear()
    assert capture["selected"] == ["s"]


def test_shadow_safety_cannot_be_outweighed_by_perfect_quality(snapshot):
    capture = {"selected": ["s"], "candidates": [{"name": "s", "score": 1.0, "rank": 1}]}
    before = deepcopy(capture)
    result = replay(
        capture,
        enable_shadow=True,
        policy="evidence",
        sidecar={"s": make_rating(snapshot, observed=8, review=False)},
    )
    assert not result["selected"] and result["abstained"] and not result["applied_to_production"]
    assert capture == before


def test_low_coverage_is_not_a_perfect_score(snapshot):
    feature, coverage = quality_feature(make_rating(snapshot, observed=2, review=False))
    assert feature is None and coverage == 0.25


@pytest.mark.parametrize("has_citation", [False, True])
def test_shadow_ranking_requires_actual_source_evidence(snapshot, has_citation):
    identity = {"skill_uid": snapshot.skill_uid, "source_sha256": snapshot.document_sha256}
    capture = {"selected": ["s"], "candidates": [{"name": "s", "score": 1.0, "rank": 1, **identity}]}
    ev = Evidence(
        evidence_id="e1",
        skill_uid=snapshot.skill_uid,
        source_sha256=snapshot.document_sha256,
        kind="source_text",
        file_path=snapshot.source_path,
        start_line=2,
        end_line=2,
        quote="Write CSV.",
        validity="observed",
        reason="span fixture, not semantic gold",
    )
    result = replay(
        capture,
        policy="evidence",
        enable_shadow=True,
        sidecar={"s": make_rating(snapshot, observed=8, review=False)},
        audits={"s": {**identity, "security_gate": "allowed", "findings": []}},
        snapshots={"s": snapshot},
        evidence={"s": (ev,)} if has_citation else {},
    )
    assert result["selected"] == (["s"] if has_citation else [])


def test_pairwise_swap_maps_back_to_skill_identity():
    assert swap_consistent("left", "right", "A", "B") is True
    assert swap_consistent("left", "right", "A", "A") is False
    assert swap_consistent("left", "right", "unknown", "A") is None


def trial_data(lift=1):
    plan, records = [], []
    for family in range(4):
        for seed in (1, 2):
            for arm in ("A2", "A9"):
                row = {
                    "run_id": f"{family}-{seed}-{arm}",
                    "task_family_id": str(family),
                    "task_uid": str(family),
                    "arm_id": arm,
                    "seed": seed,
                }
                plan.append(row)
                records.append(
                    {
                        **row,
                        "verification_status": "verified",
                        "success": (arm == "A9") if lift == 1 else (arm == "A2") if lift == -1 else True,
                    }
                )
    return plan, records


@pytest.mark.parametrize("lift", [-1, 0, 1])
def test_family_bootstrap_does_not_count_seed_as_independent_sample(lift):
    plan, records = trial_data(lift)
    result = paired_family_bootstrap(records, plan, n_boot=300)
    assert result["families"] == 4 and result["delta_pp"] == 100 * lift
    assert result["ci95_low_pp"] == result["ci95_high_pp"] == 100 * lift


@pytest.mark.parametrize(
    "fault", ["missing_trial", "duplicate_run", "missing_arm", "changed_seed", "invalid_binary"]
)
def test_incomplete_or_invalid_cohort_is_rejected(fault):
    plan, records = trial_data()
    if fault == "missing_trial":
        records.pop()
    if fault == "duplicate_run":
        records.append(records[0])
    if fault == "missing_arm":
        plan = [r for r in plan if r["arm_id"] != "A9"]
        records = [r for r in records if r["arm_id"] != "A9"]
    if fault == "changed_seed":
        records[0]["seed"] = 99
    if fault == "invalid_binary":
        records[0]["success"] = 0.5
    with pytest.raises(ValueError):
        paired_family_bootstrap(records, plan, n_boot=300)


def test_unverified_record_requires_explicit_itt_policy():
    plan, records = trial_data()
    records[0].update(verification_status="infra_failure", success=None)
    with pytest.raises(ValueError):
        paired_family_bootstrap(records, plan, n_boot=300)
    result = paired_family_bootstrap(records, plan, n_boot=300, unverified_policy="itt_failure")
    assert result["unverified_counts"] == {"infra_failure": 1}


def test_holm_keeps_original_order():
    assert holm([0.04, 0.001, 0.02]) == pytest.approx([0.04, 0.003, 0.04])


@pytest.mark.parametrize("raw", [b"", b"wrong\n1\n2\n", b"value\n1\n9\n", b"value\nNaN\n3\n", b"value\n3\n"])
def test_fixture_verifier_rejects_mutated_artifacts(raw):
    assert not verify_sum_fixture(raw, expected_count=2, expected_sum="3")


def test_fixture_verifier_accepts_expected_bytes():
    assert verify_sum_fixture(b"value\n1\n2\n", expected_count=2, expected_sum="3")


@pytest.mark.parametrize(
    "docker,approved,frozen", [(False, True, True), (True, False, True), (True, True, False)]
)
def test_execution_has_no_local_fallback(docker, approved, frozen):
    with pytest.raises(PermissionError):
        require_execution_approval(docker_available=docker, approved=approved, manifest_frozen=frozen)
