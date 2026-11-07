from __future__ import annotations

import hashlib

import pytest

from research.skill_quality.manifest import digest
from research.skill_quality.schemas import DIMENSIONS, DimensionRating, QualityRating, SkillSnapshot


def make_snapshot(
    text: str = "# Example\nWrite CSV.\nVerify row count.\n",
    *,
    repo: str = "https://github.com/fixture/one",
    name: str = "example",
    commit: str = "a" * 40,
) -> SkillSnapshot:
    sha = hashlib.sha256(text.encode()).hexdigest()
    path = "skills/" + name + "/SKILL.md"
    return SkillSnapshot(
        skill_uid=digest([repo, commit, path, sha]),
        name=name,
        domain="fixture",
        source_repo=repo,
        repo_family_id=repo,
        source_commit=commit,
        source_path=path,
        document=text,
        document_sha256=sha,
        source_kind="original_skill_md",
        declared_license="unknown",
        package_integrity="not_applicable",
        card_sha256="c" * 64,
    )


def make_rating(snapshot: SkillSnapshot, *, observed: int = 0, review: bool = True) -> QualityRating:
    dims = tuple(
        DimensionRating(
            dimension=dim,
            score=4 if i < observed else None,
            status="observed" if i < observed else "unknown",
            evidence_ids=("e1",) if i < observed else (),
            reason="fixture",
        )
        for i, dim in enumerate(DIMENSIONS)
    )
    return QualityRating(
        skill_uid=snapshot.skill_uid,
        source_sha256=snapshot.document_sha256,
        rubric_version="quality-rubric-v1",
        method_id="fixture",
        dimensions=dims,
        review_required=review,
    )


@pytest.fixture
def snapshot():
    return make_snapshot()
