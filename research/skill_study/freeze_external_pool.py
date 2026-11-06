"""Blindly freeze candidate source archives and check text overlap; no scoring.

Archives are never extracted or executed. Root licenses are evidence only;
component-level review, semantic duplication and final test eligibility remain
pending. Reading bytes for hashing/dedup is not a human/model content review.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx

from research.skill_quality.datasets import deduplicate
from research.skill_quality.manifest import digest, file_sha, freeze_files, read_jsonl, write_once
from research.skill_quality.schemas import SkillSnapshot


@dataclass(frozen=True)
class TextObject:
    skill_uid: str
    document: str
    document_sha256: str


def run(
    inventory_path: Path, frozen: Path, output: Path, archive_cache: Path | None = None
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("Source snapshots are write-once")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=False)
    old = [
        TextObject(r["skill_uid"], r["document"], r["document_sha256"])
        for r in read_jsonl(frozen / "snapshots/skills.jsonl")
    ]
    documents, packages, archives = [], [], []
    selected_repos = {"https://github.com/huggingface/skills", "https://github.com/expo/skills"}
    with httpx.Client(follow_redirects=True, timeout=90) as client:
        for source in inventory["sources"]:
            if source["source_repo"] not in selected_repos:
                continue
            repo = source["source_repo"].removeprefix("https://github.com/")
            url = f"https://codeload.github.com/{repo}/zip/{source['commit']}"
            archive_path = output / (repo.replace("/", "__") + ".zip")
            cached = archive_cache / archive_path.name if archive_cache else None
            raw = bytearray(cached.read_bytes()) if cached and cached.is_file() else bytearray()
            if not raw:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    for block in response.iter_bytes(1024 * 1024):
                        raw.extend(block)
                        if len(raw) > 80_000_000:
                            raise ValueError("Archive byte bound exceeded")
            if len(raw) > 80_000_000:
                raise ValueError("Cached archive byte bound exceeded")
            archive_path.write_bytes(raw)
            archive = zipfile.ZipFile(io.BytesIO(raw))
            members = {}
            for member in archive.infolist():
                if member.is_dir():
                    continue
                parts = member.filename.split("/")[1:]
                if not parts or any(p in {"", ".", ".."} for p in parts) or "\\" in member.filename:
                    raise ValueError("Invalid archive member path")
                if stat.S_ISLNK(member.external_attr >> 16):
                    continue
                members["/".join(parts)] = member
            if sum(m.file_size for m in members.values()) > 300_000_000:
                raise ValueError("Archive expansion bound exceeded")
            root_licenses = [
                p for p in members if "/" not in p and p.lower().startswith(("license", "copying", "notice"))
            ]
            archives.append(
                {
                    "repo": source["source_repo"],
                    "commit": source["commit"],
                    "archive_sha256": file_sha(archive_path),
                    "archive_bytes": len(raw),
                    "root_license_files": root_licenses,
                    "declared_root_license": source["declared_root_license"],
                }
            )
            for document in source["documents"]:
                path = document["path"]
                if path not in members or members[path].file_size > 2_000_000:
                    raise ValueError("Registered Skill document missing/oversized")
                content = archive.read(members[path])
                git_blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
                if git_blob != document["git_blob_sha"]:
                    raise ValueError("Git blob identity mismatch")
                text = content.decode("utf-8")
                sha = hashlib.sha256(content).hexdigest()
                uid = digest([source["source_repo"], source["commit"], path, sha])
                prefix = path.removesuffix("SKILL.md")
                resources = []
                for resource_path, member in members.items():
                    if not resource_path.startswith(prefix):
                        continue
                    if member.file_size > 8_000_000:
                        raise ValueError("Individual package resource too large")
                    blob = archive.read(member)
                    resources.append(
                        {
                            "path": resource_path,
                            "bytes": len(blob),
                            "sha256": hashlib.sha256(blob).hexdigest(),
                        }
                    )
                documents.append(TextObject(uid, text, sha))
                packages.append(
                    {
                        "skill_uid": uid,
                        "source_repo": source["source_repo"],
                        "commit": source["commit"],
                        "path": path,
                        "sha256": sha,
                        "resources": resources,
                        "root_license_files": root_licenses,
                        "component_license_review": "pending",
                        "final_test_eligibility": "pending",
                    }
                )
    # Existing implementation is a structural reader of the three text fields;
    # these objects are not fabricated production SkillSnapshot records.
    dedup = deduplicate(cast(list[SkillSnapshot], old + documents), threshold=0.85)
    old_ids, new_ids = {r.skill_uid for r in old}, {r.skill_uid for r in documents}
    # The old deduplicator reports content_clusters as lists of IDs.
    clusters = dedup["content_clusters"]
    if not isinstance(clusters, dict):
        raise ValueError("Unexpected deduplicator result schema: " + repr(list(dedup)))
    old_connected, new_only_groups = set(), []
    for group in clusters.values():
        ids = set(group)
        if ids & old_ids:
            old_connected.update(ids & new_ids)
        elif ids & new_ids:
            new_only_groups.append(sorted(ids & new_ids))
    connected_repos = {p["source_repo"] for p in packages if p["skill_uid"] in old_connected}
    summary = {
        "experiment": "blind_external_candidate_freeze_and_lexical_overlap",
        "source_repositories": len(archives),
        "candidate_original_documents": len(documents),
        "registered_package_resources": sum(len(p["resources"]) for p in packages),
        "new_documents_linked_to_existing_content_clusters": len(old_connected),
        "new_only_lexical_content_groups": len(new_only_groups),
        "new_source_repositories_connected_to_existing_by_text": sorted(connected_repos),
        "packages_in_repository_disjoint_new_sources": sum(
            p["source_repo"] not in connected_repos for p in packages
        ),
        "threshold": 0.85,
        "human_or_model_body_review": False,
        "automatic_hashing_and_lexical_text_processing": True,
        "final_d2_changed": False,
        "final_test_eligibility": "pending_license_and_semantic_review",
        "community_code_executed": False,
        "api_calls": 0,
        "archives": archives,
        "inventory_sha256": file_sha(inventory_path),
    }
    write_once(output / "packages.json", packages)
    write_once(output / "dedup.json", dedup)
    write_once(output / "summary.json", summary)
    write_once(output / "manifest.json", freeze_files(output, output.iterdir()))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("out/research/skill-study/20261106-external-source-inventory.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive-cache", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.inventory,
                Path("out/research/skill-quality/20261104-phase-a-v3"),
                args.output,
                args.archive_cache,
            ),
            indent=2,
        )
    )
