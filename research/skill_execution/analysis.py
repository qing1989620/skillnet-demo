"""Prespecified descriptive analysis of constructed-condition paired outcomes."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

import numpy as np

from research.skill_quality.manifest import file_sha, read_jsonl, verify_files, write_once

from .experiment import ARMS
from .tasks import METRIC_KEYS, verify_artifact

COMPARISONS = [
    ("original", "no_skill"),
    ("evidence_contract", "original"),
    ("contract_only", "no_skill"),
    ("evidence_contract", "contract_only"),
    ("unrelated", "no_skill"),
]


def analyze(prepared: Path, run: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Use a new analysis ID")
    verify_files(run, json.loads((run / "manifest.json").read_text(encoding="utf-8")))
    rows = read_jsonl(run / "observations.private.jsonl")
    cases = {r["input"]["task_id"]: r for r in read_jsonl(prepared / "cases.private.jsonl")}
    completed = [r for r in rows if "usage" in r]
    assert len(completed) == 300, "Do not present an incomplete experiment as a complete paired comparison"
    for row in completed:
        check = verify_artifact(row["artifact"], cases[row["task_id"]]["expected"])
        assert check["task_success"] == row["task_success"] and check["failed_checks"] == row["failed_checks"]
        row["data_measures_success"] = (
            row["stratum"] == "artifact"
            and isinstance(row["artifact"], dict)
            and row["artifact"].get("status") == "completed"
            and row["artifact"].get("actions") == []
            and all(k not in row["failed_checks"] for k in METRIC_KEYS)
        )
    aggregates = []
    for stratum in ["artifact", "boundary"]:
        for arm in ARMS:
            subset = [r for r in completed if r["stratum"] == stratum and r["arm"] == arm]
            passed = sum(r["task_success"] for r in subset)
            aggregates.append(
                {
                    "stratum": stratum,
                    "arm": arm,
                    "n": len(subset),
                    "passed": passed,
                    "success_rate": passed / len(subset),
                    "data_measures_passed": sum(r["data_measures_success"] for r in subset),
                    "prompt_tokens": sum(r["usage"]["prompt_tokens"] for r in subset),
                    "completion_tokens": sum(r["usage"]["completion_tokens"] for r in subset),
                    "peak_tariff_upper_cny": str(
                        sum((Decimal(r["tariff_upper"]["CNY"]) for r in subset), Decimal(0))
                    ),
                    "failed_checks": dict(Counter(k for r in subset for k in r["failed_checks"])),
                }
            )
    strata = []
    for condition in sorted({r["condition"] for r in completed}):
        for arm in ARMS:
            subset = [r for r in completed if r["condition"] == condition and r["arm"] == arm]
            strata.append(
                {
                    "condition": condition,
                    "arm": arm,
                    "n": len(subset),
                    "passed": sum(r["task_success"] for r in subset),
                }
            )
    effects = []
    rng = np.random.default_rng(20261111)
    for selected, base in COMPARISONS:
        units = []
        conditions = sorted({r["condition"] for r in completed if r["stratum"] == "artifact"})
        wins = losses = ties = 0
        for condition in conditions:
            a = {
                (r["task_id"], r["repeat"]): int(r["task_success"])
                for r in completed
                if r["condition"] == condition and r["arm"] == selected
            }
            b = {
                (r["task_id"], r["repeat"]): int(r["task_success"])
                for r in completed
                if r["condition"] == condition and r["arm"] == base
            }
            assert set(a) == set(b) and len(a) == 4
            diffs = [a[k] - b[k] for k in sorted(a)]
            wins += sum(d > 0 for d in diffs)
            losses += sum(d < 0 for d in diffs)
            ties += sum(d == 0 for d in diffs)
            units.append(float(np.mean(diffs)))
        sampled = np.array(units)[rng.integers(0, len(units), size=(10000, len(units)))].mean(axis=1)
        effects.append(
            {
                "selected": selected,
                "base": base,
                "condition_clusters": len(units),
                "mean_paired_difference": float(np.mean(units)),
                "conditional_percentile_interval_95": [
                    float(x) for x in np.quantile(sampled, [0.025, 0.975])
                ],
                "paired_wins": wins,
                "paired_losses": losses,
                "paired_ties": ties,
                "not_a_population_generalization_or_equivalence_certificate": True,
            }
        )
    by_size = []
    for size in [8, 48]:
        for arm in ARMS:
            subset = [
                r for r in completed if r["stratum"] == "artifact" and r["rows"] == size and r["arm"] == arm
            ]
            by_size.append(
                {"rows": size, "arm": arm, "n": len(subset), "passed": sum(r["task_success"] for r in subset)}
            )
    report = {
        "date": "2026-11-11",
        "experiment": "restricted_csv_five_arm_artifact_experiment",
        "run_id": run.name,
        "responses": 300,
        "unique_task_inputs": 30,
        "normal_task_inputs": 24,
        "normal_condition_clusters": 12,
        "boundary_task_inputs": 6,
        "repeats": 2,
        "arms": ARMS,
        "aggregates": aggregates,
        "by_condition": strata,
        "by_row_count": by_size,
        "paired_effects": effects,
        "source_summary_sha256": file_sha(run / "summary.json"),
        "summary": json.loads((run / "summary.json").read_text(encoding="utf-8")),
        "independent_human_quality_labels": 0,
        "community_script_executions": 0,
        "limitations": [
            "one target Skill, constructed conditions, one mutable model alias, two repeats",
            "text-only executor; does not test actual community-script execution or unrestricted agent actions",
            "condition bootstrap describes this development design, not a random sample of real-world families",
            "boundary cases are explicit metadata rules, not file-format decoding or operating-system security tests",
            "task specification itself supplies rules to every arm; any gain must exceed this strong no-Skill control",
            "contract-only arm separates added operational guidance from the original Skill content",
            "unrelated control is close in byte length, not equal in observed tokens",
        ],
    }
    output.mkdir(parents=True)
    write_once(output / "analysis.json", report)
    write_once(output / "trial-outcomes.jsonl", completed, jsonl=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.prepared, args.run, args.output)
    print(
        json.dumps(
            {"aggregates": report["aggregates"], "paired_effects": report["paired_effects"]},
            ensure_ascii=False,
            indent=2,
        )
    )
