"""Post-inference scoring with official labels, accounting for the 402 interruption."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from research.skill_quality.manifest import digest, file_sha, freeze_files, read_jsonl, write_once

from .experiment import ARMS


def metrics(rows: list[dict]) -> dict:
    passed = [r for r in rows if r["gold"]]
    failed = [r for r in rows if not r["gold"]]

    def correct(r):
        return r["schema_valid"] and (r["p"] >= 0.5) == r["gold"]

    tpr = sum(correct(r) for r in passed) / len(passed) if passed else None
    tnr = sum(correct(r) for r in failed) / len(failed) if failed else None
    chosen = [r for r in rows if r["schema_valid"] and (r["p"] >= 0.8 or r["p"] <= 0.2)]
    return {
        "n": len(rows),
        "gold_pass": len(passed),
        "gold_fail": len(failed),
        "valid": sum(r["schema_valid"] for r in rows),
        "correct": sum(correct(r) for r in rows),
        "accuracy": sum(correct(r) for r in rows) / len(rows),
        "pass_recall": tpr,
        "fail_recall": tnr,
        "balanced_accuracy": (tpr + tnr) / 2 if tpr is not None and tnr is not None else None,
        "false_acceptances": sum(r["schema_valid"] and r["p"] >= 0.5 for r in failed),
        "invalid_on_failed": sum(not r["schema_valid"] for r in failed),
        "brier_invalid_fixed_half": float(
            np.mean([(r["p"] - int(r["gold"])) ** 2 if r["schema_valid"] else 0.25 for r in rows])
        ),
        "confidence_coverage": len(chosen) / len(rows),
        "confident_accuracy": sum(correct(r) for r in chosen) / len(chosen) if chosen else None,
        "confident_false_acceptances": sum(r["gold"] is False and r["p"] >= 0.8 for r in chosen),
    }


def analyze(source: Path | None, prepared: Path, run: Path, output: Path, labels: Path | None = None) -> dict:
    if output.exists():
        raise FileExistsError("Immutable analysis IDs")
    # Predictions and provider failure are already frozen; only now score labels.
    assert (run / "manifest.json").exists()
    attempted = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "trials").glob("*.json"))]
    grouped = defaultdict(list)
    for row in attempted:
        grouped[row["case_id"]].append(row)
    common = {k: v for k, v in grouped.items() if len(v) == 3 and all(r.get("http_status") == 200 for r in v)}
    info = {r["case_id"]: r for r in read_jsonl(prepared / "groups.jsonl")}
    label_map = (
        {r["case_id"]: json.loads(r["raw_metadata_utf8"]) for r in read_jsonl(labels)} if labels else None
    )
    scored = []
    for name, triplet in sorted(common.items()):
        meta = (
            label_map[name]
            if label_map
            else json.loads(
                (source / "snapshot/data/evaluation" / name / "metadata.json").read_text(encoding="utf-8")
            )
        )
        assert meta["trajectory_label"] in {"pass", "fail"}
        gold = meta["trajectory_label"] == "pass"
        for row in triplet:
            scored.append(
                {
                    "case_id": name,
                    "task": info[name]["task"],
                    "domain": info[name]["domain"],
                    "arm": row["arm"],
                    "gold": gold,
                    "schema_valid": row["schema_valid"],
                    "p": row["judgment"]["p_success"] if row.get("judgment") else None,
                    "trial_id": row["trial_id"],
                    "locator_checks": row.get("locator_checks", []),
                }
            )
    tasks = sorted({r["task"] for r in scored})
    by_arm = {arm: metrics([r for r in scored if r["arm"] == arm]) for arm in ARMS}
    by_task = [
        {"task": task, "arm": arm, **metrics([r for r in scored if r["arm"] == arm and r["task"] == task])}
        for task in tasks
        for arm in ARMS
    ]
    for arm in ARMS:
        applicable = [
            r["balanced_accuracy"] for r in by_task if r["arm"] == arm and r["balanced_accuracy"] is not None
        ]
        by_arm[arm]["task_macro_balanced_accuracy"] = float(np.mean(applicable))
        by_arm[arm]["tasks_with_both_classes"] = len(applicable)
        refs = [c for r in scored if r["arm"] == arm for c in r["locator_checks"]]
        by_arm[arm]["valid_locator_refs"] = sum(c["supplied"] for c in refs)
        by_arm[arm]["all_locator_refs"] = len(refs)
    effects = []
    rng = np.random.default_rng(20261113)
    cases = sorted(common)
    for arm in ARMS[1:]:
        lookup = {(r["case_id"], r["arm"]): r for r in scored}
        means = []
        wins = losses = ties = 0
        for task in tasks:
            task_cases = [name for name in cases if info[name]["task"] == task]
            diffs = []
            for name in task_cases:
                a, b = lookup[(name, arm)], lookup[(name, "standard")]

                def good(r):
                    return int(r["schema_valid"] and (r["p"] >= 0.5) == r["gold"])

                d = good(a) - good(b)
                diffs.append(d)
                wins += d > 0
                losses += d < 0
                ties += d == 0
            means.append(np.mean(diffs))
        bootstrap = np.array(means)[rng.integers(0, len(tasks), size=(10000, len(tasks)))].mean(axis=1)
        effects.append(
            {
                "arm": arm,
                "base": "standard",
                "task_macro_accuracy_difference": float(np.mean(means)),
                "conditional_95_interval": np.quantile(bootstrap, [0.025, 0.975]).tolist(),
                "actual_task_clusters": len(tasks),
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "not_primary_full_evaluation_estimate": True,
            }
        )
        # Main binary endpoint: resample the actual six task clusters, preserving
        # task sizes and class counts, then recompute pooled balanced accuracy.
        counts = []
        for task in tasks:
            local = [r for r in scored if r["task"] == task]
            arows = [r for r in local if r["arm"] == arm]
            brows = [r for r in local if r["arm"] == "standard"]
            m1, m0 = metrics(arows), metrics(brows)
            counts.append(
                [
                    m1["pass_recall"] * m1["gold_pass"],
                    m1["fail_recall"] * m1["gold_fail"],
                    m0["pass_recall"] * m0["gold_pass"],
                    m0["fail_recall"] * m0["gold_fail"],
                    m1["gold_pass"],
                    m1["gold_fail"],
                ]
            )
        values = np.array(counts)[rng.integers(0, len(tasks), size=(10000, len(tasks)))].sum(axis=1)
        differences = 0.5 * (
            (values[:, 0] - values[:, 2]) / values[:, 4] + (values[:, 1] - values[:, 3]) / values[:, 5]
        )
        effects[-1]["balanced_accuracy_difference"] = (
            by_arm[arm]["balanced_accuracy"] - by_arm["standard"]["balanced_accuracy"]
        )
        effects[-1]["balanced_accuracy_conditional_95_interval"] = np.quantile(
            differences, [0.025, 0.975]
        ).tolist()
    selection = []
    for task in tasks:
        names = sorted(name for name in cases if info[name]["task"] == task)
        labels = {r["case_id"]: int(r["gold"]) for r in scored if r["task"] == task}
        for k in [1, 3, 5, 10]:
            if len(names) < k:
                continue
            subsets = [rng.choice(names, k, replace=False).tolist() for _ in range(1000)]
            random_success = np.mean([labels[s[0]] for s in subsets])
            ceiling = np.mean([max(labels[n] for n in s) for s in subsets])
            for arm in ARMS:
                prob = {
                    r["case_id"]: (r["p"] if r["schema_valid"] else -1)
                    for r in scored
                    if r["task"] == task and r["arm"] == arm
                }
                success = np.mean([labels[max(s, key=lambda n: (prob[n], digest(n)))] for s in subsets])
                selection.append(
                    {
                        "task": task,
                        "arm": arm,
                        "k": k,
                        "success": float(success),
                        "random_first": float(random_success),
                        "pool_ceiling": float(ceiling),
                        "reused_archived_trajectories": True,
                    }
                )
    ledger = json.loads((run / "ledger.json").read_text(encoding="utf-8"))
    charged = [r for r in attempted if r.get("response", {})]
    usage = {
        k: sum(r["response"].get("usage", {}).get(k, 0) for r in charged)
        for k in ["prompt_tokens", "completion_tokens"]
    }
    summary = {
        "planned_cases": 203,
        "planned_calls": 609,
        "attempts": len(attempted),
        "http200": sum(r.get("http_status") == 200 for r in attempted),
        "complete_triplets": len(common),
        "actual_source_tasks": len(tasks),
        "actual_domains": len({r["domain"] for r in scored}),
        "attempted_task_counts": dict(Counter(info[n]["task"] for n in common)),
        "interruption": "DeepSeek HTTP 402 insufficient balance on attempt 259; no retry; subsequent requests not scheduled",
        "main_sample_scope": "86 lexicographically earlier cases, not the intended full 203-case benchmark and not a random subset",
        "schema_invalid_http200": sum(
            r.get("http_status") == 200 and not r["schema_valid"] for r in attempted
        ),
        "by_arm": by_arm,
        "by_task": by_task,
        "effects": effects,
        "offline_selection": selection,
        "usage": usage,
        "ledger": ledger,
        "reserved_upper_usd": str(
            sum(__import__("decimal").Decimal(x) for x in ledger["reserved_usd"].values())
        ),
        "always_fail_accuracy": sum(not r["gold"] for r in scored) / len(scored),
        "always_fail_balanced_accuracy": 0.5,
        "future_schema_repair_not_applied": True,
        "limitations": [
            "predeclared full 14-task protocol not completed",
            "six actual task clusters only",
            "archived trajectory verification not live task-solving",
            "public benchmark contamination not excluded",
            "artifact snapshots partial",
            "invalid responses counted wrong; Brier uses fixed .5 for invalid and is labeled",
        ],
    }
    packet_path = prepared / "packets.jsonl"
    if not packet_path.exists():
        packet_path = prepared / "packet-index.jsonl"
    packet_rows = [r for r in read_jsonl(packet_path) if r["case_id"] in common]
    summary["observed_artifact_scope"] = {
        "official_summaries": sum(r["has_official_summary"] for r in packet_rows),
        "cases_with_supplied_artifact_files": sum(
            (
                json.loads(r["artifact_facts"])[0]["supplied_files"]
                if "artifact_facts" in r
                else r["artifact_snapshot_file_count"]
            )
            > 0
            for r in packet_rows
        ),
        "implication": "The interrupted matched sample has no supplied artifact files or summaries. The artifact arm does not test positive artifact-inspection utility here; it mostly adds the missing-snapshot scope warning.",
        "truncated_contexts": sum(r["context_truncated"] for r in packet_rows),
    }
    output.mkdir(parents=True)
    write_once(output / "scored.jsonl", scored, jsonl=True)
    write_once(output / "analysis.json", summary)
    write_once(output / "code-manifest.json", freeze_files(Path.cwd(), [Path(__file__)]))
    write_once(
        output / "source-manifests.json",
        {"prepared": file_sha(prepared / "manifest.json"), "run": file_sha(run / "manifest.json")},
    )
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for n in ["prepared", "run", "output"]:
        parser.add_argument("--" + n, type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--labels", type=Path)
    args = parser.parse_args()
    report = analyze(args.source, args.prepared, args.run, args.output, args.labels)
    print(
        json.dumps(
            {k: report[k] for k in ["attempts", "complete_triplets", "by_arm", "effects", "usage", "ledger"]},
            ensure_ascii=False,
            indent=2,
        )
    )
