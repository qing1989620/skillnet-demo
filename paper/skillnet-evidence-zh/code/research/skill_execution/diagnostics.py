"""Post-hoc measurement diagnostics, never added to prespecified treatment effects."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from research.skill_quality.manifest import read_jsonl, write_once


def diagnose(run: Path, output: Path) -> dict:
    rows = [r for r in read_jsonl(run / "observations.private.jsonl") if r.get("stratum") == "artifact"]
    assert len(rows) == 240
    failures = sum(len(r["failed_checks"]) for r in rows)
    pairs = defaultdict(list)
    for row in rows:
        pairs[(row["task_id"], row["arm"])].append(row)
    assert all(len(v) == 2 for v in pairs.values())
    correct = sum(r["task_success"] for r in rows)
    result = {
        "kind": "posthoc_descriptive_measurement_diagnostic",
        "normal_artifact_trials": len(rows),
        "complete_successes": correct,
        "all_required_checks_per_trial": 10,
        "failed_required_checks": failures,
        "mean_required_check_pass_fraction": 1 - failures / (10 * len(rows)),
        "five_data_measure_check_pass_fraction": 1 - failures / (5 * len(rows)),
        "whole_artifact_success_fraction": correct / len(rows),
        "repeat_pairs": len(pairs),
        "repeat_pass_disagreements": sum(
            v[0]["task_success"] != v[1]["task_success"] for v in pairs.values()
        ),
        "repeat_artifact_disagreements": sum(v[0]["artifact"] != v[1]["artifact"] for v in pairs.values()),
        "release_gate_replay": {
            "accept_all": {"released": len(rows), "incorrect_releases": len(rows) - correct},
            "reject_all": {"released": 0, "incorrect_releases": 0},
            "full_verifier_gate": {"released": correct, "incorrect_releases": 0},
        },
        "gate_limit": "oracle-defined replay; no increase in solving success and no general risk guarantee",
        "not_the_legacy_skill_quality_score": True,
    }
    write_once(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(diagnose(args.run, args.output))
