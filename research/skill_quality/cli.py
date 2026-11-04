"""Phase A commands. No paid model call or arbitrary Skill execution is enabled."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from .audit_static import audit
from .baseline_audit import inspect_repository
from .datasets import deduplicate, prepare_splits
from .label_export import export_labels
from .manifest import canonical, digest, freeze_files, read_jsonl, verify_files, write_once
from .report import inventory_metrics, render_report
from .schemas import SkillSnapshot
from .snapshot import git_commit, snapshot_library

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).parent / "configs/study-v1.yaml"


def snapshots_at(run: Path) -> list[SkillSnapshot]:
    return [SkillSnapshot.model_validate(row) for row in read_jsonl(run / "snapshots/skills.jsonl")]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def recompute(run: Path) -> dict[str, Any]:
    return inventory_metrics(
        snapshots_at(run),
        read_jsonl(run / "baseline.jsonl"),
        read_jsonl(run / "static_audits.jsonl"),
        load_json(run / "dataset_manifest.json"),
        load_json(run / "duplicate_groups.json"),
    )


def do_snapshot(run: Path) -> None:
    os.environ["DEEPSEEK_API_KEY"] = ""
    from skillnet import config
    from skillnet.catalog import SkillLibrary

    config.API_KEY = ""
    if config.LIBRARY_FILE.resolve() != (ROOT / "data/library.json").resolve():
        raise ValueError("Snapshot must read the baseline checkout, not a private runtime path")
    library = SkillLibrary.load()
    items, baseline = snapshot_library(
        ROOT, library, base_commit=load_json(run / "protocol.json")["protocol"]["repo_commit"]
    )
    write_once(run / "snapshots/skills.jsonl", [s.model_dump(mode="json") for s in items], jsonl=True)
    write_once(run / "baseline.jsonl", baseline, jsonl=True)
    print(
        json.dumps(
            {"snapshot_skills": len(items), "registered_resources": sum(len(s.resources) for s in items)}
        ),
        flush=True,
    )


def do_labels(run: Path, split_name: str) -> None:
    snapshots = snapshots_at(run)
    ids = load_json(run / "dataset_manifest.json")["sample_ids"][split_name]
    for rater in ("A", "B"):
        write_once(
            run / f"labels/{split_name}_{rater}_unlabelled.jsonl",
            export_labels(snapshots, ids, labeler_id=rater + "-blinded"),
            jsonl=True,
        )
    # Provenance is separated because this dimension necessarily reveals source.
    by_uid = {s.skill_uid: s for s in snapshots}
    write_once(
        run / f"labels/{split_name}_provenance_review.jsonl",
        [
            {
                "skill_uid": uid,
                "source_repo": by_uid[uid].source_repo,
                "source_commit": by_uid[uid].source_commit,
                "source_path": by_uid[uid].source_path,
                "declared_license": by_uid[uid].declared_license,
                "review_status": "not_reviewed",
                "license_evidence_files": [
                    r.model_dump() for r in by_uid[uid].resources if "license" in r.path.lower()
                ],
            }
            for uid in ids
        ],
        jsonl=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "inspect",
            "snapshot",
            "scan",
            "dedup",
            "split",
            "export-labels",
            "prepare",
            "analyze",
            "verify",
            "judge",
            "execute",
        ],
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--run-id", default="20261104-phase-a-v1")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--split", choices=["D1", "D2"], default="D1")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", args.run_id):
        parser.error("Invalid run ID")
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if args.limit < 1:
        parser.error("Limit must be positive")
    run = ROOT / "out/research/skill-quality" / args.run_id
    if args.command in ("judge", "execute"):
        if args.dry_run:
            print(
                json.dumps(
                    {
                        "command": args.command,
                        "status": "plan_only_no_external_calls",
                        "approved_budget_usd": 0,
                        "requires": [
                            "rotated_key",
                            "budget_approval",
                            "human_gold",
                            "frozen_models_and_providers",
                        ]
                        if args.command == "judge"
                        else ["docker", "reviewed_tasks", "frozen_verifiers", "execution_approval"],
                    }
                )
            )
            return 0
        print(
            json.dumps({"error_code": 4, "reason": "Phase_A_does_not_enable_paid_calls_or_skill_execution"})
        )
        return 4
    if args.dry_run:
        print(json.dumps({"command": args.command, "run": str(run), "writes": False, "live_calls": False}))
        return 0
    if args.command == "inspect":
        print(json.dumps(inspect_repository(ROOT), ensure_ascii=False))
        return 0
    if args.command == "verify":
        verify_files(run, load_json(run / "verification/manifest.json"))
        verify_files(Path(__file__).parent, load_json(run / "research_code_manifest.json"))
        calculated = recompute(run)
        if canonical(calculated) != canonical(load_json(run / "analysis/metrics.json")):
            raise ValueError("Recomputed metrics differ")
        if (run / "report/FINAL_REPORT.md").read_text(encoding="utf-8") != render_report(calculated):
            raise ValueError("Report differs from raw-derived metrics")
        print(json.dumps({"ok": True, "recomputed_skills": calculated["skills"], "live_calls": 0}))
        return 0
    if args.command in ("snapshot", "prepare"):
        base = config["protocol"]["repo_commit"]
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", base, git_commit(ROOT)], cwd=ROOT, check=False
        )
        if result.returncode:
            raise ValueError("Frozen baseline is not an ancestor of the research checkout")
        from tools.verify_delivery import verify

        if not verify(ROOT, strict_runtime=True)["ok"]:
            raise ValueError("Original delivery bytes differ from the frozen baseline")
        run.mkdir(parents=True, exist_ok=False)
        write_once(run / "protocol.json", config)
        (run / "protocol.sha256").write_text(digest(config) + "\n", encoding="ascii", newline="\n")
        write_once(run / "repository_audit.json", inspect_repository(ROOT))
        code_root = Path(__file__).parent
        code_paths = [
            p
            for p in code_root.rglob("*")
            if p.is_file() and p.suffix in (".py", ".yaml", ".txt", ".toml", ".ini")
        ]
        write_once(run / "research_code_manifest.json", freeze_files(code_root, code_paths))
        do_snapshot(run)
    if args.command in ("scan", "prepare"):
        write_once(run / "static_audits.jsonl", [audit(s) for s in snapshots_at(run)], jsonl=True)
        print("static audit complete", flush=True)
    if args.command in ("dedup", "prepare"):
        write_once(
            run / "duplicate_groups.json",
            deduplicate(snapshots_at(run), config["data"]["near_duplicate_jaccard"]),
        )
        print("exact/near text grouping complete", flush=True)
    if args.command in ("split", "prepare"):
        split = prepare_splits(
            snapshots_at(run),
            load_json(run / "duplicate_groups.json"),
            seed=config["protocol"]["split_seed"],
            target=config["data"]["labels_per_split"],
        )
        write_once(run / "dataset_manifest.json", split)
        print(
            json.dumps({"split_status": split["status"], "component_sizes": split["component_sizes"]}),
            flush=True,
        )
    if args.command == "export-labels":
        do_labels(run, args.split)
    if args.command == "prepare":
        for split_name in ("D1", "D2"):
            do_labels(run, split_name)
    if args.command in ("prepare", "analyze"):
        metrics = recompute(run)
        write_once(run / "analysis/metrics.json", metrics)
        (run / "report").mkdir(parents=True, exist_ok=True)
        with (run / "report/FINAL_REPORT.md").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(render_report(metrics))
        manifest = freeze_files(run, run.rglob("*"))
        write_once(run / "verification/manifest.json", manifest)
        print(
            json.dumps({"ok": True, "run": str(run), "metrics_sha256": digest(metrics)}, ensure_ascii=False)
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FileExistsError:
        print(json.dumps({"error_code": 2, "reason": "immutable_output_already_exists_use_new_run_id"}))
        sys.exit(2)
    except (ValueError, KeyError, OSError) as exc:
        # Type only: source errors must never echo document text or credentials.
        print(json.dumps({"error_code": 3, "reason": type(exc).__name__}))
        sys.exit(3)
