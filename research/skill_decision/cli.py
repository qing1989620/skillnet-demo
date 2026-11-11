"""Offline runnable Skill discriminator and frozen-D1 diagnosis."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from research.skill_quality.manifest import file_sha, freeze_files, safe_read, write_once
from research.skill_study.package_audit import audit_package, load_d1

from .gate import Bundle, evaluate, from_texts

LABELS = {
    "repair_required": "发现需修复的问题",
    "tested_pass_within_scope": "在已测任务范围内通过",
    "insufficient_evidence": "证据不足，需进一步验证",
    "outside_tested_scope": "当前任务超出已有测试范围",
}


def scan_directory(directory: Path, manifest: Path | None = None) -> dict:
    directory = directory.resolve()
    files = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".py", ".json", ".txt", ".yaml", ".yml"}:
            relative = path.relative_to(directory).as_posix()
            files[relative] = safe_read(directory, relative).decode("utf-8", errors="strict")
    if "SKILL.md" not in files:
        raise ValueError("SKILL.md is required")
    bundle = from_texts(directory.name, files)
    if manifest:
        expected = json.loads(manifest.read_text(encoding="utf-8"))
        bundle = Bundle(bundle.identity, files, expected, bundle.examples)
    result = evaluate(bundle)
    result["decision_zh"] = LABELS[result["decision"]]
    result["integrity_origin"] = (
        "caller_supplied_manifest_not_independently_authenticated"
        if manifest
        else "self_snapshotted_not_a_pinned_upstream_version"
    )
    result["opaque_resources_not_analyzed"] = True
    return result


def natural(output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Use a fresh diagnosis ID")
    root = Path.cwd()
    packages = load_d1(root, root / "out/research/skill-quality/20261104-phase-a-v3")
    reports = []
    for package in packages:
        prior, examples = audit_package(package)
        bundle = from_texts(package.snapshot.name, package.texts)
        bundle = Bundle(
            bundle.identity,
            bundle.files,
            bundle.expected_hashes,
            tuple({**e, "script": e["resolved_script"]} for e in examples),
        )
        result = evaluate(bundle)
        result.update(
            {
                "decision_zh": LABELS[result["decision"]],
                "skill_uid": package.snapshot.skill_uid,
                "source_repository": package.snapshot.source_repo,
                "source_commit": package.snapshot.source_commit,
                "registered_resource_count": len(package.inventory),
                "opaque_resource_count": len(package.opaque),
                "full_inventory_rehashed_before_text_projection": True,
                "unresolved_mentions_are_review_leads": prior["unresolved_resource_mentions"],
            }
        )
        reports.append(result)
    summary = {
        "date": "2026-11-11",
        "packages": len(reports),
        "decisions": dict(Counter(r["decision"] for r in reports)),
        "defect_kinds": dict(Counter(f["kind"] for r in reports for f in r["findings"])),
        "command_states": dict(
            Counter(c["result"]["status"] for r in reports for c in r["command_observations"])
        ),
        "api_calls": 0,
        "api_cost_usd": 0,
        "community_script_executions": 0,
        "human_semantic_gold": 0,
        "accuracy_on_natural_skills": None,
        "meaning": "Read-only mechanical diagnosis; untested semantic quality remains unknown",
    }
    output.mkdir(parents=True)
    write_once(output / "reports.jsonl", reports, jsonl=True)
    write_once(output / "summary.json", summary)
    write_once(output / "code-manifest.json", freeze_files(root, Path(__file__).parent.glob("*.py")))
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan")
    scan.add_argument("directory", type=Path)
    scan.add_argument("--manifest", type=Path)
    scan.add_argument("--output", type=Path)
    audit = sub.add_parser("natural")
    audit.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "natural":
        result = natural(args.output)
    else:
        result = scan_directory(args.directory, args.manifest)
        if args.output:
            write_once(args.output, result)
            result = {
                "output": str(args.output.resolve()),
                "sha256": file_sha(args.output),
                "decision": result["decision_zh"],
            }
    print(json.dumps(result, ensure_ascii=False, indent=2))
