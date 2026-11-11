"""Explicit post-hoc falsification: combine version drift with unseen precision."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path

from research.skill_quality.manifest import digest, file_sha, read_jsonl, write_once

from .oracle import verify
from .planner import POLICIES, choose, eligible, metadata_path
from .registry import public_nodes
from .runner import execute_batch


def run(prepared: Path, calibration: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Choose a new falsification ID")
    output.mkdir(parents=True)
    write_once(
        output / "plan.json",
        {
            "date": "2026-11-11",
            "posthoc": True,
            "rationale": "Separate precision and version-drift success does not establish their conjunction",
            "changes_to_primary_method": False,
            "primary_results_already_observed": True,
            "tests": "same 24 precision inputs, version t0 replaced by t1, 1.5x metadata budget, all ten fixed policies",
            "code_sha256": file_sha(Path(__file__)),
        },
    )
    tasks = [t for t in read_jsonl(prepared / "tasks.jsonl") if t["cohort"] == "precision"]
    nodes = json.loads((prepared / "registry.json").read_text(encoding="utf-8"))
    by_key = {n["implementation_key"]: n for n in nodes}
    private = copy.deepcopy(nodes)
    index = next(i for i, n in enumerate(private) if n["implementation_key"] == "t0")
    private[index] = {**by_key["t1"], "id": by_key["t0"]["id"]}
    public = public_nodes(private)
    lookup = {n["id"]: n for n in private}
    fixed = {
        cap: by_key[key]["id"]
        for cap, key in [
            ("parse", "p0"),
            ("dedup", "d0"),
            ("exclude", "x0"),
            ("drop", "m0"),
            ("metrics", "t0"),
        ]
    }
    evidence = read_jsonl(calibration / "evidence.jsonl")
    decisions = []
    requests = {}
    truth = {}
    for task in tasks:
        budget = math.ceil(
            float(metadata_path(eligible(public, task["request"]), task["request"])["cost"]) * 1.5
        )
        for policy in POLICIES:
            answer = choose(
                public,
                task["request"],
                evidence,
                budget,
                policy,
                fixed if policy == "fixed_workflow" else None,
            )
            keys = [lookup[n]["implementation_key"] for n in answer["plan"]]
            identity = digest([task["task_id"], keys]) if keys else None
            if identity:
                requests[identity] = {
                    "execution_id": identity,
                    "raw": task["raw"],
                    "intent": task["request"]["intent"],
                    "plan": keys,
                }
                truth[identity] = task["expected"]
            decisions.append(
                {
                    "task_id": task["task_id"],
                    "policy": policy,
                    "execution_id": identity,
                    "plan": answer["plan"],
                }
            )
    write_once(output / "decisions-before-execution.jsonl", decisions, jsonl=True)
    observed = execute_batch(list(requests.values()), output / "worker")
    verdict = {r["execution_id"]: verify(r, truth[r["execution_id"]]) for r in observed}
    for row in decisions:
        row["task_success"] = bool(row["execution_id"] and verdict[row["execution_id"]]["passed"])
    summary = {
        "posthoc": True,
        "inputs": len(tasks),
        "reused_inputs_not_additional_independent_main_tasks": True,
        "unique_executions": len(observed),
        "methods": {p: sum(r["task_success"] for r in decisions if r["policy"] == p) for p in POLICIES},
        "new_model_calls": 0,
        "method_modified_after_outcomes": False,
    }
    write_once(output / "decisions.jsonl", decisions, jsonl=True)
    write_once(output / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["prepared", "calibration", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.prepared, args.calibration, args.output), ensure_ascii=False, indent=2))
