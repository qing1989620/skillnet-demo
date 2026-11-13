"""Explicitly post-hoc joint-contract replay from observed community CLI outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.skill_quality.manifest import digest, freeze_files, write_once
from skillnet.frontier import plan


def analyze(observed: Path, bundle: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Immutable post-hoc IDs")
    fixtures = json.loads((observed / "fixtures.json").read_text(encoding="utf-8"))
    verdicts = json.loads((observed / "verdicts.json").read_text(encoding="utf-8"))
    entries = json.loads((observed / "entries.json").read_text(encoding="utf-8"))
    for entry in entries:
        from research.skill_quality.manifest import file_sha

        assert file_sha(bundle / "scripts" / entry["file"]) == entry["source_sha256"]
    allowed = [
        "data_profiler.py",
        "data_profiler_repaired.py",
        "missing_value_analyzer.py",
        "outlier_detector.py",
        "outlier_detector_repaired.py",
    ]
    ids = {name: "n-" + digest(name)[:10] for name in allowed}
    by_id = {v: k for k, v in ids.items()}
    dev = {f["id"] for f in fixtures if f["dataset"] in {"iris", "wine"}}
    lookup = {
        (r["case_id"], r["script"], r["threshold"] or 0): r["passed"] for r in verdicts if r.get("case_id")
    }
    methods = [
        "fixed_original",
        "original_metadata",
        "original_evidence",
        "expanded_metadata",
        "expanded_evidence",
    ]
    rows = []
    for fixture in fixtures:
        if fixture["id"] in dev:
            continue
        for threshold in [1.5, 3.0]:
            for method in methods:
                selected = ["data_profiler.py", "outlier_detector.py"]
                if method != "fixed_original":
                    pool = [n for n in allowed if "expanded" in method or "_repaired" not in n]
                    actions = []
                    for name in pool:
                        outlier = name.startswith("outlier")
                        parameter = threshold if outlier else 0
                        if "evidence" in method and not all(lookup[(task, name, parameter)] for task in dev):
                            continue
                        actions.append(
                            {
                                "id": ids[name],
                                "requires": ["raw"],
                                "adds": ["outlier" if outlier else "summary"],
                                "deletes": [],
                                "cost": (bundle / "scripts" / name).stat().st_size,
                            }
                        )
                    answer = plan(["raw"], ["summary", "outlier"], actions, max_depth=2, max_states=64)
                    selected = [by_id[n] for n in answer["plan"]] if answer["status"] == "plan_found" else []
                passed = bool(selected) and all(
                    lookup[(fixture["id"], n, threshold if n.startswith("outlier") else 0)] for n in selected
                )
                rows.append(
                    {
                        "case_id": fixture["id"],
                        "dataset": fixture["dataset"],
                        "threshold": threshold,
                        "method": method,
                        "plan": selected,
                        "passed": passed,
                        "abstain": not selected,
                    }
                )
    groups = []
    for cohort in ["held_source", "explicit_regression"]:
        for method in methods:
            rr = [
                r
                for r in rows
                if r["method"] == method
                and ((r["dataset"] == "explicit_regression") == (cohort == "explicit_regression"))
            ]
            groups.append(
                {
                    "cohort": cohort,
                    "method": method,
                    "n": len(rr),
                    "successes": sum(r["passed"] for r in rr),
                    "abstentions": sum(r["abstain"] for r in rr),
                }
            )
    summary = {
        "posthoc": True,
        "observations_already_seen": True,
        "scope": "joint row count, documented null counts and requested IQR count; independent stages read the same unchanged input",
        "new_executions": 0,
        "replay_of_actual_original_cli_outputs": True,
        "development_inputs": len(dev),
        "held_inputs": 24,
        "regression_inputs_separate": 1,
        "groups": groups,
        "candidate_intervention": "expanded pool adds the two minimal repaired implementations; routing effect must be separated from added candidate availability",
        "evidence_rule": "only Iris/Wine probe verdicts; version tied by raw code hash; veto observed failures; same native planner",
    }
    output.mkdir(parents=True)
    write_once(output / "decisions.jsonl", rows, jsonl=True)
    write_once(output / "summary.json", summary)
    write_once(output / "code-manifest.json", freeze_files(Path.cwd(), [Path(__file__)]))
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["observed", "bundle", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(args.observed, args.bundle, args.output), ensure_ascii=False, indent=2))
