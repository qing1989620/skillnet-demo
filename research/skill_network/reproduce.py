"""Verify frozen evidence, recompute every selector, optionally reexecute owned code."""

from __future__ import annotations

import argparse
import copy
import json
import math
import tempfile
from pathlib import Path

from research.skill_quality.manifest import digest, read_jsonl, verify_files

from .analysis import analyze
from .oracle import verify
from .planner import choose, eligible, metadata_path
from .registry import full_registry, public_nodes
from .runner import execute_batch
from .tasks import build_tasks

RESULTS = Path(__file__).with_name("results")
ROOT = Path(__file__).resolve().parents[2]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def reproduce(root: Path = RESULTS, *, execute: bool = False, backend: str = "trusted_process") -> dict:
    prepared, calibration, run = [root / n for n in ["prepared-v3", "calibration-v2", "execution-v2"]]
    joint = root / "joint-posthoc-v1"
    for name in ["sources-v2", "prepared-v3", "calibration-v2", "execution-v2", "analysis-v1"]:
        path = root / name
        verify_files(path, load(path / "manifest.json"))
    verify_files(ROOT, load(prepared / "code-manifest.json"))
    tasks = read_jsonl(prepared / "tasks.jsonl")
    assert digest(tasks) == digest(build_tasks(root / "sources-v2"))
    nodes = load(prepared / "registry.json")
    assert digest(nodes) == digest(full_registry())
    by_task = {t["task_id"]: t for t in tasks}
    evidence = read_jsonl(calibration / "evidence.jsonl")
    raw_probes = read_jsonl(calibration / "worker/outcomes.jsonl")
    assert len(evidence) == len(raw_probes) == 928
    assert {r["dataset"] for r in evidence} == {"iris", "wine"}
    for row, artifact in zip(evidence, raw_probes, strict=True):
        task = by_task[row["task_id"]]
        assert task["split"] == "development"
        assert row["artifact_sha256"] == digest(artifact)
        verdict = verify(artifact, task["expected"], cap=row["cap"])
        assert all(row[k] == v for k, v in verdict.items())
    drift = copy.deepcopy(nodes)
    by_key = {n["implementation_key"]: n for n in nodes}
    index = next(i for i, n in enumerate(drift) if n["implementation_key"] == "t0")
    drift[index] = {**by_key["t1"], "id": by_key["t0"]["id"]}
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
    records = read_jsonl(run / "decisions.jsonl")
    before = read_jsonl(run / "decisions-before-execution.jsonl")
    assert len(records) == len(before) == 7856
    artifact_by_id = {r["execution_id"]: r for r in read_jsonl(run / "worker/outcomes.jsonl")}
    request_by_id = {r["execution_id"]: r for r in read_jsonl(run / "worker/requests.jsonl")}
    assert len(artifact_by_id) == len(request_by_id) == 1204
    for row, prior in zip(records, before, strict=True):
        assert all(row[k] == v for k, v in prior.items())
        task = by_task[row["task_id"]]
        assert task["split"] == "held_out"
        cohort = row["cohort"]
        private = nodes
        if cohort == "version_drift":
            private = drift
        elif cohort == "missing_capability":
            private = [n for n in nodes if n["capability"] != "metrics"]
        elif cohort.startswith("id_permutation_"):
            seed = int(cohort.rsplit("_", 1)[1])
            private = [{**n, "id": "p-" + digest([seed, n["id"]])[:10]} for n in nodes]
        public = public_nodes(private)
        answer = choose(
            public,
            task["request"],
            evidence,
            row["budget"],
            row["policy"],
            fixed if row["policy"] == "fixed_workflow" else None,
        )
        assert answer["plan"] == row["plan"]
        assert answer["bytes"] == row["selected_context_bytes"] <= row["budget"]
        identity = row["execution_id"]
        if identity:
            artifact = artifact_by_id[identity]
            verdict = verify(artifact, task["expected"])
            assert verdict["passed"] == row["task_success"]
            assert verdict["failed_checks"] == row["failed_checks"]
            assert artifact["calls"] == row["operator_calls"]
            assert (
                digest([task["task_id"], task["input_sha256"], request_by_id[identity]["plan"]]) == identity
            )
        else:
            assert not row["task_success"] and row["operator_calls"] == 0
    joint_rows = read_jsonl(joint / "decisions.jsonl")
    joint_artifacts = {r["execution_id"]: r for r in read_jsonl(joint / "worker/outcomes.jsonl")}
    assert len(joint_rows) == 240 and len(joint_artifacts) == 132
    for row in joint_rows:
        task = by_task[row["task_id"]]
        public = public_nodes(drift)
        budget = math.ceil(
            float(metadata_path(eligible(public, task["request"]), task["request"])["cost"]) * 1.5
        )
        answer = choose(
            public,
            task["request"],
            evidence,
            budget,
            row["policy"],
            fixed if row["policy"] == "fixed_workflow" else None,
        )
        assert answer["plan"] == row["plan"]
        identity = row["execution_id"]
        assert (
            bool(identity and verify(joint_artifacts[identity], task["expected"])["passed"])
            == row["task_success"]
        )
    for policy, count in load(joint / "summary.json")["methods"].items():
        assert count == sum(r["task_success"] for r in joint_rows if r["policy"] == policy)
    with tempfile.TemporaryDirectory(prefix="skill-network-reproduction-") as directory:
        temp = Path(directory)
        replay = analyze(prepared, calibration, run, temp / "analysis")
        assert digest(replay) == digest(load(root / "analysis-v1/analysis.json"))
        reexecuted = 0
        if execute:
            requests, wanted = [], []
            for path in [calibration, run, joint]:
                requests.extend(read_jsonl(path / "worker/requests.jsonl"))
                wanted.extend(read_jsonl(path / "worker/outcomes.jsonl"))
            observed = execute_batch(requests, temp / "worker", backend=backend)
            assert digest(observed) == digest(wanted)
            reexecuted = len(observed)
    return {
        "status": "PASS",
        "api_calls": 0,
        "api_cost_usd": 0,
        "development_probes_reverified": 928,
        "decisions_recomputed": 7856,
        "primary_unique_executions_reverified": 1204,
        "held_out_inputs": 152,
        "posthoc_decisions_recomputed": 240,
        "posthoc_executions_reverified": 132,
        "owned_executions_repeated": reexecuted,
        "backend": backend if execute else "offline",
        "scope": "Same frozen inputs; reproduction is not additional independent evaluation",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backend", choices=["trusted_process", "docker"], default="trusted_process")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = reproduce(execute=args.execute, backend=args.backend)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
