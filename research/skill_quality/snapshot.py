"""Read fixed library/package bytes without executing any community module."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Literal

from .manifest import canonical, digest, safe_read
from .schemas import Resource, SkillSnapshot

PROJECT_REPO = "https://github.com/qing1989620/skillnet-demo"
CARD_FIELDS = (
    "name",
    "description",
    "domain",
    "tags",
    "capability",
    "inputs",
    "outputs",
    "use_when",
    "steps",
    "pitfalls",
    "verification",
    "compatibility",
    "allowed_tools",
)


def git_commit(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def snapshot_library(
    root: Path, library: Any, *, base_commit: str | None = None
) -> tuple[list[SkillSnapshot], list[dict[str, Any]]]:
    """Every registered resource is rehashed; errors abort rather than silently skip."""
    packages = json.loads(safe_read(root, "seed/community/packages.json", max_bytes=20_000_000))
    commit = base_commit or git_commit(root)
    snapshots, baseline = [], []
    from skillnet.schema import assess_quality, quality_score

    for skill in sorted(library.all(), key=lambda s: s.name):
        card = {key: getattr(skill, key) for key in CARD_FIELDS}
        resources: list[Resource] = []
        source_kind: Literal["original_skill_md", "derived_catalog_card"]
        integrity: Literal["verified", "not_applicable"]
        if skill.source == "github":
            pack = packages[skill.name]
            meta = skill.metadata
            if (
                pack["package_path"] != meta["package_path"]
                or pack["skill_md_sha256"] != meta["content_sha256"]
            ):
                raise ValueError("Package metadata mismatch: " + skill.name)
            expected_package_sha = pack["package_sha256"]
            if digest({k: v for k, v in pack.items() if k != "package_sha256"}) != expected_package_sha:
                raise ValueError("Package manifest mismatch: " + skill.name)
            base = str(pack["package_path"])
            if not base.startswith("seed/community/skills/"):
                raise ValueError("Unapproved package root")
            document_raw = None
            seen = set()
            for row in pack["files"]:
                if row["path"] in seen:
                    raise ValueError("Duplicate resource path")
                seen.add(row["path"])
                raw = safe_read(root, base + "/" + row["path"])
                if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
                    raise ValueError("Resource integrity mismatch: " + skill.name + "/" + row["path"])
                resources.append(Resource(**row))
                if row["path"] == "SKILL.md":
                    document_raw = raw
            if document_raw is None or hashlib.sha256(document_raw).hexdigest() != pack["skill_md_sha256"]:
                raise ValueError("Missing or changed SKILL.md")
            repo = "https://github.com/" + pack["repository"].lower().removesuffix(".git")
            source_commit, source_path = pack["commit"], meta["original_path"]
            document = document_raw.decode("utf-8")
            source_kind, integrity = "original_skill_md", "verified"
        else:
            repo, source_commit = PROJECT_REPO, commit
            source_path = "catalog-cards/" + skill.name + ".json"
            # Derived cards avoid adding historical quality/stats to a judge input.
            document = canonical(card).decode("utf-8") + "\n"
            source_kind, integrity = "derived_catalog_card", "not_applicable"
        doc_sha = hashlib.sha256(document.encode("utf-8")).hexdigest()
        uid = digest([repo, source_commit, source_path, doc_sha])
        item = SkillSnapshot(
            skill_uid=uid,
            name=skill.name,
            domain=skill.domain,
            source_repo=repo,
            repo_family_id=repo.lower(),
            source_commit=source_commit,
            source_path=source_path,
            document=document,
            document_sha256=doc_sha,
            source_kind=source_kind,
            declared_license=skill.license or "unknown",
            resources=tuple(resources),
            package_integrity=integrity,
            card_sha256=digest(card),
        )
        snapshots.append(item)
        assessed = assess_quality(skill)
        baseline.append(
            {
                "skill_uid": uid,
                "name": skill.name,
                "source_card_sha256": digest(card),
                "stored_quality": skill.quality,
                "stored_score": quality_score(skill.quality),
                "recomputed_quality": assessed,
                "recomputed_score": quality_score(assessed),
                "scope": "existing_card_fields_not_full_package",
                "utility_status": "not_estimated",
            }
        )
    return snapshots, baseline
