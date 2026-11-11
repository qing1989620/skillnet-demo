"""Prespecified paired analysis; all budgets, baselines, stress cases retained."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from research.skill_quality.manifest import file_sha, freeze_files, read_jsonl, verify_files, write_once

from .planner import POLICIES

EVIDENCE_POLICIES = {
    "global_filter_path",
    "global_risk_path",
    "conditional_evidence_path",
    "conditional_top5",
    "evidence_without_version",
}


def aggregate(rows: list[dict], probes: int) -> dict:
    success = sum(r["task_success"] for r in rows)
    started = sum(r["complete_path_selected"] for r in rows)
    calls = sum(r["operator_calls"] for r in rows)
    return {
        "n": len(rows),
        "successes": success,
        "success_rate": success / len(rows),
        "plans": started,
        "abstentions": len(rows) - started,
        "operator_calls": calls,
        "mean_calls_per_task": calls / len(rows),
        "mean_context_bytes_per_started_plan": sum(r["selected_context_bytes"] for r in rows) / started
        if started
        else None,
        "calls_per_correct_artifact": calls / success if success else None,
        "including_initial_probe_calls_per_correct_artifact": (calls + probes) / success if success else None,
        "started_but_incorrect": started - success,
        "process_errors": sum(r["process_error"] for r in rows),
    }


def analyze(prepared: Path, calibration: Path, run: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Analysis IDs are immutable")
    for p in [prepared, calibration, run]:
        verify_files(p, json.loads((p / "manifest.json").read_text(encoding="utf-8")))
    rows = read_jsonl(run / "decisions.jsonl")
    probes = len(read_jsonl(calibration / "evidence.jsonl"))
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r["cohort"], r["policy"], r["multiplier"])].append(r)
    groups = [
        {"cohort": c, "policy": p, "multiplier": b, **aggregate(rs, probes if p in EVIDENCE_POLICIES else 0)}
        for (c, p, b), rs in sorted(grouped.items())
    ]
    datasets = []
    for name in ["wdbc", "banknote"]:
        for policy in POLICIES:
            rr = [r for r in rows if r["cohort"] == "main" and r["dataset"] == name and r["policy"] == policy]
            datasets.append(
                {
                    "dataset": name,
                    "policy": policy,
                    **aggregate(rr, probes if policy in EVIDENCE_POLICIES else 0),
                }
            )
    primary = []
    for policy in POLICIES:
        rr = [r for r in rows if r["cohort"] == "main" and r["policy"] == policy]
        assert len(rr) == 384
        primary.append(
            {
                "policy": policy,
                "unique_inputs": 128,
                **aggregate(rr, probes if policy in EVIDENCE_POLICIES else 0),
            }
        )
    effects = []
    rng = np.random.default_rng(20261111)
    for comparator in [p for p in POLICIES if p != "conditional_evidence_path"]:
        left = [r for r in rows if r["cohort"] == "main" and r["policy"] == "conditional_evidence_path"]
        right = {
            (r["task_id"], r["multiplier"]): r
            for r in rows
            if r["cohort"] == "main" and r["policy"] == comparator
        }
        blocks = defaultdict(list)
        wins = losses = ties = 0
        for a in left:
            b = right[(a["task_id"], a["multiplier"])]
            diff = int(a["task_success"]) - int(b["task_success"])
            blocks[a["template"]].append(diff)
            wins += diff > 0
            losses += diff < 0
            ties += diff == 0
        assert len(blocks) == 32 and all(len(v) == 12 for v in blocks.values())
        means = np.array([np.mean(blocks[k]) for k in sorted(blocks)])
        sampled = means[rng.integers(0, 32, size=(10000, 32))].mean(axis=1)
        effects.append(
            {
                "selected": "conditional_evidence_path",
                "base": comparator,
                "condition_blocks": 32,
                "unique_tasks": 128,
                "paired_resource_cases": 384,
                "mean_difference": float(means.mean()),
                "conditional_interval_95": [float(x) for x in np.quantile(sampled, [0.025, 0.975])],
                "wins": int(wins),
                "losses": int(losses),
                "ties": int(ties),
                "not_population_confidence_or_multiple_testing_significance": True,
            }
        )
    summary = {
        "date": "2026-11-11",
        "primary": "mean success over three fixed resource levels per task",
        "primary_scope": "128 held-out derived tasks, 32 constructed condition blocks, two datasets",
        "source_summary": json.loads((run / "summary.json").read_text(encoding="utf-8")),
        "development_probes": probes,
        "policies": POLICIES,
        "groups": groups,
        "primary_averages": primary,
        "by_held_out_dataset": datasets,
        "paired_effects": effects,
        "call_accounting": "per-policy logical invocations; physical identical plans cached; development evidence not free",
        "source_files": {
            "prepared_manifest": file_sha(prepared / "manifest.json"),
            "calibration_manifest": file_sha(calibration / "manifest.json"),
            "run_manifest": file_sha(run / "manifest.json"),
        },
        "limitations": [
            "18 owned operators, not 1881 natural community Skills",
            "task semantics and operator library shared across dataset split",
            "risk product is a heuristic, not calibrated joint success probability",
            "known manual workflow matches at generous budgets",
            "public inputs are modified by explicit controlled audit faults",
            "all policies use the same final verifier; its release filtering is not new learned risk control",
        ],
    }
    output.mkdir(parents=True)
    write_once(output / "analysis.json", summary)
    write_once(output / "code-manifest.json", freeze_files(Path.cwd(), [Path(__file__)]))
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["prepared", "calibration", "run", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.prepared, args.calibration, args.run, args.output)
    print(
        json.dumps(
            {"primary": report["primary_averages"], "effects": report["paired_effects"]},
            ensure_ascii=False,
            indent=2,
        )
    )
