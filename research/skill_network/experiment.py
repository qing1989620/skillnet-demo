"""Freeze tasks, collect development-only evidence, then evaluate fixed selectors."""

from __future__ import annotations

import argparse
import copy
import json
import math
import time
from pathlib import Path

from research.skill_quality.manifest import (
    digest,
    file_sha,
    freeze_files,
    read_jsonl,
    verify_files,
    write_once,
)

from .contracts import allowed_caps, context_group
from .oracle import verify
from .planner import POLICIES, choose, eligible, metadata_path
from .registry import full_registry, public_nodes
from .runner import execute_batch
from .tasks import build_tasks, probe_input


def prepare(sources: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Preparation IDs are immutable")
    verify_files(sources, json.loads((sources / "manifest.json").read_text(encoding="utf-8")))
    output.mkdir(parents=True)
    tasks, nodes = build_tasks(sources), full_registry()
    protocol = json.loads(Path(__file__).with_name("protocol.json").read_text(encoding="utf-8"))
    assert sum(t["cohort"] == "main" and t["split"] == "held_out" for t in tasks) == 128
    assert len(nodes) == 18 and sum(t["split"] == "development" for t in tasks) == 128
    write_once(output / "protocol.json", protocol)
    write_once(output / "tasks.jsonl", tasks, jsonl=True)
    write_once(output / "registry.json", nodes)
    write_once(
        output / "source-identities.json", json.loads((sources / "sources.json").read_text(encoding="utf-8"))
    )
    paths = list(Path(__file__).parent.glob("*.py")) + [Path(__file__).with_name("protocol.json")]
    paths += [Path("skillnet/frontier.py"), Path("research/skill_study/routing_pilot.py")]
    paths = [path.resolve() for path in paths]
    write_once(output / "code-manifest.json", freeze_files(Path.cwd(), paths))
    for path in paths:
        target = output / "code-snapshot" / path.resolve().relative_to(Path.cwd())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return {"tasks": len(tasks), "development": 128, "held_out_main": 128, "nodes": 18, "api_budget_usd": 0}


def calibrate(prepared: Path, output: Path, backend: str) -> dict:
    if output.exists():
        raise FileExistsError("Use a fresh calibration ID")
    verify_files(prepared, json.loads((prepared / "manifest.json").read_text(encoding="utf-8")))
    tasks = [t for t in read_jsonl(prepared / "tasks.jsonl") if t["split"] == "development"]
    nodes = json.loads((prepared / "registry.json").read_text(encoding="utf-8"))
    requests, probes = [], []
    for task in tasks:
        for node in nodes:
            if node["implementation_key"].endswith("2") or node["capability"] not in allowed_caps(
                task["request"]["intent"]["mask"]
            ):
                continue
            identity = digest([task["task_id"], node["id"]])
            requests.append(
                {
                    "execution_id": identity,
                    "initial_state": probe_input(task, node["capability"]),
                    "intent": task["request"]["intent"],
                    "plan": [node["implementation_key"]],
                }
            )
            probes.append(
                {
                    "execution_id": identity,
                    "task_id": task["task_id"],
                    "cap": node["capability"],
                    "node_id": node["id"],
                    "source_sha256": node["source_sha256"],
                    "group": context_group(node, task["request"], True),
                    "dataset": task["dataset"],
                }
            )
    output.mkdir(parents=True)
    raw = execute_batch(requests, output / "worker", backend=backend)
    by_task = {t["task_id"]: t for t in tasks}
    records = []
    for record, outcome in zip(probes, raw, strict=True):
        result = verify(outcome, by_task[record["task_id"]]["expected"], cap=record["cap"])
        records.append({**record, **result, "artifact_sha256": digest(outcome)})
    write_once(output / "evidence.jsonl", records, jsonl=True)
    write_once(
        output / "summary.json",
        {
            "probes": len(records),
            "datasets": sorted({r["dataset"] for r in records}),
            "passed": sum(r["passed"] for r in records),
            "model_calls": 0,
            "test_tasks_used": 0,
            "prepared_manifest_sha256": file_sha(prepared / "manifest.json"),
        },
    )
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return {"probes": len(records), "test_tasks_used": 0}


def run(prepared: Path, calibration: Path, output: Path, backend: str) -> dict:
    if output.exists():
        raise FileExistsError("Use a fresh execution ID")
    for path in [prepared, calibration]:
        verify_files(path, json.loads((path / "manifest.json").read_text(encoding="utf-8")))
    verify_files(Path.cwd(), json.loads((prepared / "code-manifest.json").read_text(encoding="utf-8")))
    tasks = read_jsonl(prepared / "tasks.jsonl")
    all_nodes = json.loads((prepared / "registry.json").read_text(encoding="utf-8"))
    evidence = read_jsonl(calibration / "evidence.jsonl")
    assert {r["dataset"] for r in evidence} == {"iris", "wine"}
    by_key = {n["implementation_key"]: n for n in all_nodes}
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
    scenarios = []
    held = [t for t in tasks if t["split"] == "held_out"]
    for task in held:
        scenarios.append((task, task["cohort"], all_nodes, [1.0, 1.5, 2.0], POLICIES))
    main = [t for t in held if t["cohort"] == "main"]
    drift = copy.deepcopy(all_nodes)
    index = next(i for i, n in enumerate(drift) if n["implementation_key"] == "t0")
    drift[index] = {**by_key["t1"], "id": by_key["t0"]["id"]}
    for task in main:
        scenarios.append((task, "version_drift", drift, [1.5], POLICIES))
    shortage = [n for n in all_nodes if n["capability"] != "metrics"]
    for task in main[:16]:
        scenarios.append((task, "missing_capability", shortage, [1.0, 1.5, 2.0], POLICIES))
    sensitivity = ["metadata_shortest_path", "mmr_top5", "global_risk_path", "conditional_evidence_path"]
    for seed in [1, 2, 3]:
        perm = [{**n, "id": "p-" + digest([seed, n["id"]])[:10]} for n in all_nodes]
        for task in main:
            scenarios.append((task, f"id_permutation_{seed}", perm, [1.5], sensitivity))
    decisions, requests, execution_map = [], [], {}
    selection_start = time.monotonic()
    for task, cohort, private, multipliers, policies in scenarios:
        public = public_nodes(private)
        anchor = metadata_path(eligible(public, task["request"]), task["request"])
        if anchor["status"] == "plan_found":
            base = int(anchor["cost"])
        else:
            canonical = public_nodes(all_nodes)
            base = int(metadata_path(eligible(canonical, task["request"]), task["request"])["cost"])
        private_by_id = {n["id"]: n for n in private}
        fixed_for_view = {n["capability"]: n["id"] for n in private if n["implementation_key"].endswith("0")}
        if cohort == "version_drift":
            fixed_for_view = fixed
        for multiplier in multipliers:
            budget = math.ceil(base * multiplier)
            for policy in policies:
                result = choose(
                    public,
                    task["request"],
                    evidence,
                    budget,
                    policy,
                    fixed_ids=fixed_for_view if policy == "fixed_workflow" else None,
                )
                plan = result["plan"]
                keys = [private_by_id[n]["implementation_key"] for n in plan]
                identity = digest([task["task_id"], task["input_sha256"], keys]) if plan else None
                if identity and identity not in execution_map:
                    requests.append(
                        {
                            "execution_id": identity,
                            "raw": task["raw"],
                            "intent": task["request"]["intent"],
                            "plan": keys,
                        }
                    )
                    execution_map[identity] = task
                decisions.append(
                    {
                        "task_id": task["task_id"],
                        "dataset": task["dataset"],
                        "template": task["template"],
                        "cohort": cohort,
                        "policy": policy,
                        "multiplier": multiplier,
                        "budget": budget,
                        "plan": plan,
                        "selected_context_bytes": result["bytes"],
                        "reason": result["reason"],
                        "execution_id": identity,
                        "complete_path_selected": bool(plan),
                        "selected_versions": [
                            {k: private_by_id[n][k] for k in ["id", "source_sha256", "capability"]}
                            for n in plan
                        ],
                    }
                )
    output.mkdir(parents=True)
    write_once(output / "decisions-before-execution.jsonl", decisions, jsonl=True)
    write_once(
        output / "planning.json",
        {
            "wall_seconds": time.monotonic() - selection_start,
            "decisions": len(decisions),
            "unique_plans_to_execute": len(requests),
            "test_outcomes_available_to_selector": False,
            "evidence_sha256": file_sha(calibration / "evidence.jsonl"),
        },
    )
    raw = execute_batch(requests, output / "worker", backend=backend)
    checks = {r["execution_id"]: verify(r, execution_map[r["execution_id"]]["expected"]) for r in raw}
    outcomes = {r["execution_id"]: r for r in raw}
    for decision in decisions:
        identity = decision["execution_id"]
        decision.update(
            {
                "task_success": bool(identity and checks[identity]["passed"]),
                "operator_calls": outcomes[identity]["calls"] if identity else 0,
                "failed_checks": checks[identity]["failed_checks"] if identity else ["no_plan"],
                "process_error": bool(identity and outcomes[identity]["error"]),
            }
        )
        assert decision["selected_context_bytes"] <= decision["budget"]
    write_once(output / "decisions.jsonl", decisions, jsonl=True)
    write_once(output / "execution-verdicts.json", checks)
    summary = {
        "decisions": len(decisions),
        "unique_executions": len(raw),
        "unique_held_out_inputs": len(held),
        "main_inputs": len(main),
        "calibration_probes": len(evidence),
        "model_calls": 0,
        "api_cost_usd": 0,
        "backend": backend,
        "cache": "identical input and kernel path share one actual execution; decisions are not independent trials",
    }
    write_once(output / "summary.json", summary)
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "calibrate", "run"])
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=["trusted_process", "docker"], default="trusted_process")
    args = parser.parse_args()
    if args.action == "prepare":
        answer = prepare(args.sources, args.output)
    elif args.action == "calibrate":
        answer = calibrate(args.prepared, args.output, args.backend)
    else:
        answer = run(args.prepared, args.calibration, args.output, args.backend)
    print(json.dumps(answer, ensure_ascii=False, indent=2))
