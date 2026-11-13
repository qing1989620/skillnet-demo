"""Recheck the released constructed-task results offline; never call an API."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "code"))

from research.skill_execution.tasks import (  # noqa: E402
    make_tasks,
    verifier_diagnostics,
    verify_artifact,
)


def load(name: str) -> dict:
    return json.loads((HERE / "results" / name).read_text(encoding="utf-8"))


def lines(name: str) -> list[dict]:
    return [json.loads(s) for s in (HERE / "results" / name).read_text(encoding="utf-8").splitlines()]


def reproduce() -> dict:
    cases = lines("constructed-tasks.jsonl")
    assert cases == make_tasks(), "Released inputs differ from the frozen generator"
    checks = verifier_diagnostics(cases)
    expected = {c["input"]["task_id"]: c["expected"] for c in cases}
    observations = lines("trial-outcomes.jsonl")
    analysis = load("analysis.json")
    plan = load("run-plan.json")
    posthoc = load("posthoc-diagnostics.json")
    assert len(observations) == 300 and len({r["trial_id"] for r in observations}) == 300
    normal = [r for r in observations if r["stratum"] == "artifact"]
    boundary = [r for r in observations if r["stratum"] == "boundary"]
    assert len(normal) == 240 and len(boundary) == 60
    for row in observations:
        result = verify_artifact(row["artifact"], expected[row["task_id"]])
        assert result["task_success"] == row["task_success"]
        assert set(result["failed_checks"]) == set(row["failed_checks"])
        assert row["finish_reason"] == "stop"
    for aggregate in analysis["aggregates"]:
        subset = [
            r for r in observations if (r["arm"], r["stratum"]) == (aggregate["arm"], aggregate["stratum"])
        ]
        assert len(subset) == aggregate["n"]
        assert sum(r["task_success"] for r in subset) == aggregate["passed"]
        assert dict(Counter(k for r in subset for k in r["failed_checks"])) == aggregate["failed_checks"]
        for usage_key in ["prompt_tokens", "completion_tokens"]:
            assert sum(r["usage"][usage_key] for r in subset) == aggregate[usage_key]
    rng = np.random.default_rng(plan["seed"])
    for effect, comparison in zip(
        analysis["paired_effects"], plan["analysis_comparisons_declared_before_calls"], strict=True
    ):
        selected, base = comparison
        assert (selected, base) == (effect["selected"], effect["base"])
        cluster_diffs, counts = [], Counter()
        for condition in sorted({r["condition"] for r in normal}):
            outcomes = {
                arm: {
                    (r["task_id"], r["repeat"]): int(r["task_success"])
                    for r in normal
                    if r["arm"] == arm and r["condition"] == condition
                }
                for arm in [selected, base]
            }
            a, b = outcomes[selected], outcomes[base]
            assert set(a) == set(b) and len(a) == 4
            differences = [a[k] - b[k] for k in sorted(a)]
            counts.update(differences)
            cluster_diffs.append(float(np.mean(differences)))
        sampled = np.array(cluster_diffs)[rng.integers(0, 12, size=(10000, 12))].mean(axis=1)
        assert np.isclose(float(np.mean(cluster_diffs)), effect["mean_paired_difference"])
        assert np.allclose(np.quantile(sampled, [0.025, 0.975]), effect["conditional_percentile_interval_95"])
        assert [counts[1], counts[-1], counts[0]] == [
            effect["paired_wins"],
            effect["paired_losses"],
            effect["paired_ties"],
        ]
    failures = sum(len(r["failed_checks"]) for r in normal)
    successes = sum(r["task_success"] for r in normal)
    assert failures == posthoc["failed_required_checks"] == 259
    assert successes == posthoc["complete_successes"] == 23
    assert np.isclose(1 - failures / 2400, posthoc["mean_required_check_pass_fraction"])
    pairs = defaultdict(list)
    for row in normal:
        pairs[(row["task_id"], row["arm"])].append(row)
    assert len(pairs) == 120 and all(len(v) == 2 for v in pairs.values())
    assert (
        sum(v[0]["task_success"] != v[1]["task_success"] for v in pairs.values())
        == posthoc["repeat_pass_disagreements"]
        == 7
    )
    assert (
        sum(v[0]["artifact"] != v[1]["artifact"] for v in pairs.values())
        == posthoc["repeat_artifact_disagreements"]
        == 24
    )
    for key in ["prompt_tokens", "completion_tokens"]:
        assert sum(r["usage"][key] for r in observations) == analysis["summary"][key]
    for currency, miss, output in [("USD", ".3", "1.2"), ("CNY", "2", "8")]:
        recomputed = Decimal(0)
        for row in observations:
            usage = row["usage"]
            bound = (
                Decimal(usage["prompt_tokens"]) * Decimal(miss)
                + Decimal(usage["completion_tokens"]) * Decimal(output)
            ) / 1000000
            assert bound == Decimal(row["tariff_upper"][currency])
            recomputed += bound
        assert recomputed == Decimal(analysis["summary"]["tariff_upper"][currency])
    return {
        "offline_reproduction": "passed",
        "api_calls": 0,
        "verified_observations": len(observations),
        "artifact_success": f"{successes}/240",
        "boundary_success": f"{sum(r['task_success'] for r in boundary)}/60",
        "verifier_diagnostics": checks,
        "paired_comparisons_reproduced": len(analysis["paired_effects"]),
        "observations_sha256": hashlib.sha256(
            (HERE / "results/trial-outcomes.jsonl").read_bytes()
        ).hexdigest(),
    }


if __name__ == "__main__":
    print(json.dumps(reproduce(), ensure_ascii=False, indent=2))
