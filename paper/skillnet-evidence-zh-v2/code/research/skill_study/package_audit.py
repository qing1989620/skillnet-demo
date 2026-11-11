"""Hash-check original D1 packages; text analysis is read-only and bounded."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from research.skill_quality.manifest import digest, read_jsonl, safe_read
from research.skill_quality.schemas import SkillSnapshot

from .cli_contracts import check_command, parse_contract


@dataclass(frozen=True)
class Package:
    snapshot: SkillSnapshot
    inventory: dict[str, tuple[str, int]]
    texts: dict[str, str]
    opaque: tuple[str, ...]


def load_d1(root: Path, frozen: Path) -> list[Package]:
    dataset = json.loads((frozen / "dataset_manifest.json").read_text(encoding="utf-8"))
    d1 = set(dataset["sample_ids"]["D1"])
    d2 = set(dataset["sample_ids"]["D2"])
    if d1 & d2:
        raise ValueError("Overlapping development/test IDs")
    # All-snapshot storage is read; only D1 records are materialized/inspected.
    snapshots = [
        SkillSnapshot.model_validate(r)
        for r in read_jsonl(frozen / "snapshots/skills.jsonl")
        if r["skill_uid"] in d1
    ]
    if len(snapshots) != len(d1) or any(s.source_kind != "original_skill_md" for s in snapshots):
        raise ValueError("D1 originals missing")
    registry = json.loads(safe_read(root, "seed/community/packages.json", max_bytes=20_000_000))
    packages = []
    suffixes = {".md", ".py", ".sh", ".txt", ".json", ".yaml", ".yml", ".toml"}
    for snapshot in sorted(snapshots, key=lambda s: s.skill_uid):
        registered = registry[snapshot.name]
        if (
            digest({k: v for k, v in registered.items() if k != "package_sha256"})
            != registered["package_sha256"]
        ):
            raise ValueError("Package manifest changed")
        expected = {r.path: (r.sha256, r.bytes) for r in snapshot.resources}
        if len(expected) != len(snapshot.resources):
            raise ValueError("Duplicate resources")
        expected_root = "seed/community/skills/" + snapshot.name
        if registered["package_path"] != expected_root or registered["commit"] != snapshot.source_commit:
            raise ValueError("Unbound package origin")
        if snapshot.source_repo != "https://github.com/" + registered["repository"].lower().removesuffix(
            ".git"
        ):
            raise ValueError("Unbound source repository")
        seen, texts, opaque = set(), {}, []
        for row in registered["files"]:
            relative = row["path"]
            if relative in seen or expected.get(relative) != (row["sha256"], row["bytes"]):
                raise ValueError("Resource registry mismatch")
            seen.add(relative)
            raw = safe_read(root, expected_root + "/" + relative)
            if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
                raise ValueError("Resource bytes changed")
            if PurePosixPath(relative).suffix.lower() in suffixes:
                try:
                    texts[relative] = raw.decode("utf-8")
                except UnicodeDecodeError:
                    opaque.append(relative)
            else:
                opaque.append(relative)
        if seen != set(expected) or texts.get("SKILL.md") != snapshot.document:
            raise ValueError("Incomplete package")
        packages.append(Package(snapshot, expected, texts, tuple(opaque)))
    return packages


def commands(text: str) -> list[dict[str, Any]]:
    lines, output, index = text.splitlines(), [], 0
    while index < len(lines):
        line = lines[index]
        start = index + 1
        if not re.match(r"^\s*python(?:3)?\s+\S+\.py(?:\s|$)", line):
            index += 1
            continue
        command = line.strip()
        while command.endswith("\\") and index + 1 < len(lines):
            index += 1
            command = command[:-1] + " " + lines[index].strip()
        try:
            script = shlex.split(command)[1]
        except (ValueError, IndexError):
            script = None
        output.append({"command": command, "script": script, "start_line": start, "end_line": index + 1})
        index += 1
    return output


def resolve_target(package: Package, document: str, target: str) -> str | None:
    # Resolution uses registered names only; no filesystem reads on doc links.
    if ":" in target or "\\" in target or PurePosixPath(target).is_absolute():
        return None
    candidates = [str(PurePosixPath(document).parent / target), target]
    for candidate in candidates:
        if ".." not in PurePosixPath(candidate).parts and candidate in package.inventory:
            return candidate
    return None


def audit_package(package: Package) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    contracts = {
        path: parse_contract(text, path) for path, text in package.texts.items() if path.endswith(".py")
    }
    observations, missing = [], []
    for path, text in package.texts.items():
        if not path.endswith(".md"):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for match in re.finditer(
                r"((?:scripts|references|resources|assets)/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)", line
            ):
                target = match.group(1)
                if ".." not in PurePosixPath(target).parts and resolve_target(package, path, target) is None:
                    missing.append(
                        {
                            "file": path,
                            "line": number,
                            "target": target,
                            "status": "unresolved_mention_not_confirmed_required_resource",
                        }
                    )
        for command in commands(text):
            resolved = resolve_target(package, path, command["script"]) if command["script"] else None
            spec = contracts.get(resolved) if resolved else None
            status = (
                check_command(spec, command["command"])
                if spec
                else {
                    "status": "unknown",
                    "findings": [],
                    "reasons": ["script_or_supported_text_not_registered"],
                }
            )
            observations.append({**command, "document": path, "resolved_script": resolved, "result": status})
    summary = {
        "skill_uid": package.snapshot.skill_uid,
        "name": package.snapshot.name,
        "source_repo": package.snapshot.source_repo,
        "source_commit": package.snapshot.source_commit,
        "files_rehashed": len(package.inventory),
        "text_files_analyzed": len(package.texts),
        "opaque_files": list(package.opaque),
        "python_contracts": {
            p: {"literal_options": len(c.options), "unknown_reasons": list(c.unknown_reasons)}
            for p, c in contracts.items()
        },
        "command_observations": observations,
        "unresolved_resource_mentions": missing,
        "overall_skill_quality": "not_established",
        "safety": "not_established",
        "executed_source": False,
    }
    return summary, observations
