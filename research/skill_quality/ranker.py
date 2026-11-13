"""Detached candidate replay. Baseline is canonical-equivalent, with no production writes."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .schemas import Evidence, ObsState, QualityRating, SkillSnapshot, validate_evidence


def quality_feature(rating: QualityRating, min_coverage: float = 0.75) -> tuple[float | None, float]:
    values = [r.score for r in rating.dimensions if r.status == ObsState.OBSERVED and r.score is not None]
    coverage = len(values) / 8
    if coverage < min_coverage or rating.review_required:
        return None, coverage
    return sum(values) / (4 * len(values)), coverage


def replay(
    capture: dict[str, Any],
    *,
    policy: str = "baseline",
    enable_shadow: bool = False,
    sidecar: Mapping[str, QualityRating] | None = None,
    audits: Mapping[str, dict[str, Any]] | None = None,
    evidence: Mapping[str, tuple[Evidence, ...]] | None = None,
    snapshots: Mapping[str, SkillSnapshot] | None = None,
    k: int = 5,
) -> dict[str, Any]:
    if k < 1:
        raise ValueError("Invalid top-k")
    if not enable_shadow or policy == "baseline":
        return deepcopy(capture)
    if policy not in ("rules", "evidence"):
        raise ValueError("Policy is not implemented/calibrated in Phase A")
    ratings, gates = sidecar or {}, audits or {}
    before = deepcopy(capture)
    candidates, decisions = [], []
    for candidate in before["candidates"]:
        name = candidate["name"]
        audit = gates.get(name, {})
        if audit.get("security_gate") != "allowed" or audit.get("findings"):
            decisions.append({"name": name, "action": "abstain", "reason": "safety_or_license_not_cleared"})
            continue
        score, coverage = candidate["score"], None
        if policy == "evidence":
            rating = ratings.get(name)
            if rating is None or rating.security_flags:
                decisions.append({"name": name, "action": "abstain", "reason": "no_valid_evidence_sidecar"})
                continue
            if (
                candidate.get("skill_uid") != rating.skill_uid
                or candidate.get("source_sha256") != rating.source_sha256
                or audit.get("skill_uid") != rating.skill_uid
                or audit.get("source_sha256") != rating.source_sha256
            ):
                decisions.append(
                    {"name": name, "action": "abstain", "reason": "unbound_or_stale_skill_version"}
                )
                continue
            bound_snapshot = (snapshots or {}).get(name)
            if bound_snapshot is None:
                decisions.append({"name": name, "action": "abstain", "reason": "missing_source_snapshot"})
                continue
            try:
                validate_evidence(rating, (evidence or {}).get(name, ()), bound_snapshot)
            except ValueError:
                decisions.append({"name": name, "action": "abstain", "reason": "invalid_citation_evidence"})
                continue
            feature, coverage = quality_feature(rating)
            if feature is None:
                decisions.append(
                    {"name": name, "action": "abstain", "reason": "low_evidence_or_review_required"}
                )
                continue
            score *= 0.85 + 0.3 * feature
        candidates.append({**candidate, "shadow_score": score, "evidence_coverage": coverage})
    candidates.sort(key=lambda c: (-c["shadow_score"], c["rank"]))
    return {
        "policy": policy,
        "shadow_only": True,
        "applied_to_production": False,
        "baseline": before,
        "candidates": candidates,
        "selected": [c["name"] for c in candidates[:k]],
        "decisions": decisions,
        "abstained": not candidates,
        "feature_stage": "after_existing_quality_prior_not_raw_fusion_replacement",
        "calibration_status": "not_calibrated",
        "utility_status": "not_estimated",
    }
