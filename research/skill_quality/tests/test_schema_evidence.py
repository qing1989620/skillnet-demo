from __future__ import annotations

import pytest
from pydantic import ValidationError

from research.skill_quality.schemas import (
    DimensionRating,
    Evidence,
    RunOutcome,
    SkillSnapshot,
    validate_evidence,
)

from .conftest import make_rating, make_snapshot


@pytest.mark.parametrize("score", [-1, 5, True, 1.0, "4"])
def test_invalid_ordinal_score_is_rejected(score):
    with pytest.raises(ValidationError):
        DimensionRating(
            dimension="completeness", score=score, status="observed", evidence_ids=("e",), reason="x"
        )


@pytest.mark.parametrize("state", ["unknown", "invalid", "not_applicable"])
def test_missing_is_not_zero(state):
    with pytest.raises(ValidationError):
        DimensionRating(dimension="completeness", score=0, status=state, reason="x")


def test_observed_requires_evidence_and_all_eight_dimensions(snapshot):
    with pytest.raises(ValidationError):
        DimensionRating(dimension="completeness", score=2, status="observed", reason="x")
    rating = make_rating(snapshot)
    with pytest.raises(ValidationError):
        type(rating).model_validate({**rating.model_dump(), "dimensions": [rating.dimensions[0]] * 8})


@pytest.mark.parametrize("fault", ["hash", "uid", "span", "quote", "path", "unbound"])
def test_fabricated_evidence_fails(snapshot, fault):
    evidence = dict(
        evidence_id="e1",
        skill_uid=snapshot.skill_uid,
        kind="source_text",
        source_sha256=snapshot.document_sha256,
        file_path=snapshot.source_path,
        start_line=2,
        end_line=2,
        quote="Write CSV.",
        validity="observed",
        reason="fixture",
    )
    rating = make_rating(snapshot, observed=1)
    if fault == "hash":
        evidence["source_sha256"] = "a" * 64
    if fault == "uid":
        evidence["skill_uid"] = "b" * 64
    if fault == "span":
        evidence["end_line"] = 999
    if fault == "quote":
        evidence["quote"] = "not actually here"
    if fault == "path":
        evidence["file_path"] = "other.md"
    if fault == "unbound":
        evidence["evidence_id"] = "e2"
    with pytest.raises(ValueError):
        validate_evidence(rating, (Evidence(**evidence),), snapshot)


def test_source_integrity_is_not_semantic_correctness(snapshot):
    evidence = Evidence(
        evidence_id="e1",
        skill_uid=snapshot.skill_uid,
        kind="source_text",
        source_sha256=snapshot.document_sha256,
        file_path=snapshot.source_path,
        start_line=2,
        end_line=2,
        quote="Write CSV.",
        validity="observed",
        reason="fixture",
    )
    validate_evidence(make_rating(snapshot, observed=1), (evidence,), snapshot)


def test_snapshot_uid_includes_version_and_rejects_changed_bytes(snapshot):
    assert make_snapshot(commit="b" * 40).skill_uid != snapshot.skill_uid
    with pytest.raises(ValidationError):
        SkillSnapshot.model_validate({**snapshot.model_dump(), "document": "tampered"})


def test_execution_evidence_needs_independent_run(snapshot):
    with pytest.raises(ValidationError):
        Evidence(
            evidence_id="e",
            skill_uid=snapshot.skill_uid,
            kind="execution_verified",
            source_sha256=snapshot.document_sha256,
            validity="observed",
            reason="x",
        )


@pytest.mark.parametrize(
    "fault", ["unverified_success", "unknown_zero", "negative_cost", "negative_latency", "verified_no_run"]
)
def test_outcome_cannot_fabricate_verification_or_cost(fault):
    data = dict(
        run_id="x",
        task_family_id="f",
        task_uid="a" * 64,
        arm_id="A2",
        seed=1,
        snapshot_sha256="b" * 64,
        verifier_sha256="c" * 64,
        verification_status="not_run",
        success=None,
    )
    if fault == "unverified_success":
        data["success"] = False
    if fault == "unknown_zero":
        data["billed_usd"] = 0
    if fault == "negative_cost":
        data.update(billed_usd=-1, cost_status="billed")
    if fault == "negative_latency":
        data["latency_seconds"] = -1
    if fault == "verified_no_run":
        data.update(verification_status="verified", success=True)
    with pytest.raises(ValidationError):
        RunOutcome(**data)
