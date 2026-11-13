"""Closed schemas: missing evidence is never a numerical zero."""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SHA = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
DIMENSIONS = (
    "contract_consistency",
    "completeness",
    "static_executability",
    "verification_quality",
    "maintainability",
    "provenance_license",
    "cost_awareness",
    "safety_documentation",
)


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class ObsState(StrEnum):
    OBSERVED = "observed"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    INVALID = "invalid"


class EvidenceKind(StrEnum):
    SOURCE_TEXT = "source_text"
    STATIC_CHECK = "static_check"
    LLM_JUDGMENT = "llm_judgment"
    HUMAN_LABEL = "human_label"
    EXECUTION_VERIFIED = "execution_verified"
    PAIRED_CONTRIBUTION = "paired_contribution"


class Resource(ClosedModel):
    path: str
    sha256: SHA
    bytes: int = Field(ge=0, strict=True)


class SkillSnapshot(ClosedModel):
    skill_uid: SHA
    name: str
    domain: str
    source_repo: str
    repo_family_id: str
    source_commit: str
    source_path: str
    document: str
    document_sha256: SHA
    source_kind: Literal["original_skill_md", "derived_catalog_card"]
    declared_license: str
    license_review: Literal["not_reviewed"] = "not_reviewed"
    resources: tuple[Resource, ...] = ()
    package_integrity: Literal["verified", "not_applicable"]
    card_sha256: SHA
    execution_status: Literal["not_tested"] = "not_tested"

    @model_validator(mode="after")
    def check_identity(self) -> Self:
        from .manifest import digest

        if hashlib.sha256(self.document.encode("utf-8")).hexdigest() != self.document_sha256:
            raise ValueError("Document SHA mismatch")
        identity = [self.source_repo, self.source_commit, self.source_path, self.document_sha256]
        if digest(identity) != self.skill_uid:
            raise ValueError("Skill UID mismatch")
        if not self.document.strip():
            raise ValueError("Missing body")
        return self


class Evidence(ClosedModel):
    evidence_id: str
    skill_uid: SHA
    kind: EvidenceKind
    source_sha256: SHA
    file_path: str | None = None
    start_line: int | None = Field(default=None, ge=1, strict=True)
    end_line: int | None = Field(default=None, ge=1, strict=True)
    quote: str | None = None
    run_id: str | None = None
    validity: ObsState
    reason: str

    @model_validator(mode="after")
    def check_kind(self) -> Self:
        if self.kind in (EvidenceKind.EXECUTION_VERIFIED, EvidenceKind.PAIRED_CONTRIBUTION):
            if not self.run_id:
                raise ValueError("Execution evidence needs an independent verifier run ID")
        if self.kind == EvidenceKind.SOURCE_TEXT:
            if not self.file_path or self.start_line is None or self.end_line is None:
                raise ValueError("Source evidence needs a path and line span")
            if self.end_line < self.start_line:
                raise ValueError("Reversed line span")
        return self


class DimensionRating(ClosedModel):
    dimension: str
    score: int | None = Field(default=None, ge=0, le=4, strict=True)
    status: ObsState
    evidence_ids: tuple[str, ...] = ()
    reason: str

    @model_validator(mode="after")
    def check_observation(self) -> Self:
        if self.dimension not in DIMENSIONS:
            raise ValueError("Unknown rubric dimension")
        if self.status == ObsState.OBSERVED:
            if self.score is None or not self.evidence_ids:
                raise ValueError("Observed score requires evidence")
        elif self.score is not None:
            raise ValueError("Missing/invalid/not-applicable scores must be null")
        return self


class QualityRating(ClosedModel):
    skill_uid: SHA
    source_sha256: SHA
    rubric_version: str
    method_id: str
    model_id: str | None = None
    provider_id: str | None = None
    dimensions: tuple[DimensionRating, ...]
    review_required: bool
    security_flags: tuple[str, ...] = ()
    raw_response_sha256: SHA | None = None

    @model_validator(mode="after")
    def check_dimensions(self) -> Self:
        names = [r.dimension for r in self.dimensions]
        if len(names) != 8 or set(names) != set(DIMENSIONS):
            raise ValueError("Exactly eight unique dimensions are required")
        return self


def validate_evidence(
    rating: QualityRating,
    evidence: tuple[Evidence, ...],
    snapshot: SkillSnapshot,
    *,
    trusted_non_text_ids: frozenset[str] = frozenset(),
) -> None:
    """Prove identity/span/quote integrity, not semantic relevance or correctness."""
    if rating.skill_uid != snapshot.skill_uid or rating.source_sha256 != snapshot.document_sha256:
        raise ValueError("Rating is bound to a different snapshot")
    by_id = {e.evidence_id: e for e in evidence}
    if len(by_id) != len(evidence):
        raise ValueError("Duplicate evidence ID")
    lines = snapshot.document.splitlines()
    for dim in rating.dimensions:
        for ref in dim.evidence_ids:
            item = by_id.get(ref)
            if item is None or item.validity != ObsState.OBSERVED:
                raise ValueError("Missing or invalid evidence")
            if item.kind != EvidenceKind.SOURCE_TEXT and ref not in trusted_non_text_ids:
                raise ValueError("Untrusted assessor cannot manufacture independent evidence")
            if item.skill_uid != snapshot.skill_uid or item.source_sha256 != snapshot.document_sha256:
                raise ValueError("Evidence belongs to a different source")
            if item.kind == EvidenceKind.SOURCE_TEXT:
                if item.file_path != snapshot.source_path:
                    raise ValueError("Evidence path mismatch")
                if item.start_line is None or item.end_line is None or item.end_line > len(lines):
                    raise ValueError("Fabricated line span")
                span = "\n".join(lines[item.start_line - 1 : item.end_line])
                if not item.quote or item.quote not in span:
                    raise ValueError("Quote not found in source span")


class RunOutcome(ClosedModel):
    run_id: str
    task_family_id: str
    task_uid: SHA
    arm_id: str
    seed: int = Field(strict=True)
    snapshot_sha256: SHA
    verifier_sha256: SHA
    verifier_run_id: str | None = None
    verification_status: Literal["verified", "not_run", "infra_failure", "unsafe_block", "invalid"]
    success: bool | None
    latency_seconds: float | None = Field(default=None, ge=0, strict=True)
    billed_usd: float | None = Field(default=None, ge=0, strict=True)
    cost_status: Literal["billed", "unverified", "not_called"] = "unverified"
    artifact_hashes: tuple[SHA, ...] = ()

    @model_validator(mode="after")
    def check_outcome(self) -> Self:
        if self.verification_status == "verified":
            if self.success is None or not self.verifier_run_id:
                raise ValueError("Verified outcomes require verifier identity and binary outcome")
        elif self.success is not None:
            raise ValueError("Unverified outcomes cannot report success or failure")
        if self.cost_status == "billed" and self.billed_usd is None:
            raise ValueError("Billed cost requires actual amount")
        if self.cost_status == "unverified" and self.billed_usd is not None:
            raise ValueError("Unknown cost cannot be encoded as zero")
        return self
