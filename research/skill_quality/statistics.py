"""Statistics on a complete planned cohort, preserving task-family independence."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np


def paired_family_bootstrap(
    records: list[dict[str, Any]],
    planned_trials: list[dict[str, Any]],
    *,
    arm_a: str = "A2",
    arm_b: str = "A9",
    n_boot: int = 10_000,
    seed: int = 20261104,
    unverified_policy: str = "error",
) -> dict[str, Any]:
    if n_boot < 100 or unverified_policy not in ("error", "itt_failure"):
        raise ValueError("Invalid predeclared analysis configuration")
    planned = {r["run_id"]: r for r in planned_trials}
    observed = {r["run_id"]: r for r in records}
    if len(planned) != len(planned_trials) or len(observed) != len(records) or set(planned) != set(observed):
        raise ValueError("Duplicate, missing or unplanned trials")
    groups: dict[str, dict[str, dict[tuple[str, int], int]]] = defaultdict(lambda: defaultdict(dict))
    failure_counts: dict[str, int] = defaultdict(int)
    for uid, record in observed.items():
        plan = planned[uid]
        for field in ("task_family_id", "task_uid", "arm_id", "seed"):
            if record[field] != plan[field]:
                raise ValueError("Outcome does not match planned trial")
        if record["arm_id"] not in (arm_a, arm_b):
            continue
        status = record["verification_status"]
        if status == "verified":
            if type(record["success"]) not in (int, bool) or record["success"] not in (0, 1):
                raise ValueError("Verified outcome must be binary")
            value = int(record["success"])
        elif unverified_policy == "itt_failure" and status in (
            "not_run",
            "infra_failure",
            "unsafe_block",
            "invalid",
        ):
            if record["success"] is not None:
                raise ValueError("Unverified outcome cannot masquerade as verified failure")
            value = 0
            failure_counts[status] += 1
        else:
            raise ValueError("Unverified outcome; choose the frozen missingness policy explicitly")
        key = (record["task_uid"], record["seed"])
        per_arm = groups[str(record["task_family_id"])][record["arm_id"]]
        if key in per_arm:
            raise ValueError("Duplicate family/task/arm/seed")
        per_arm[key] = value
    differences = []
    for family, arms in groups.items():
        if set(arms) != {arm_a, arm_b} or set(arms[arm_a]) != set(arms[arm_b]):
            raise ValueError("Unpaired family: " + family)
        differences.append(float(np.mean(list(arms[arm_b].values())) - np.mean(list(arms[arm_a].values()))))
    if len(differences) < 2:
        raise ValueError("Need at least two independent task families")
    d = np.asarray(differences, dtype=np.float64)
    rng = np.random.default_rng(seed)
    means = np.array([d[rng.integers(0, len(d), size=len(d))].mean() for _ in range(n_boot)])
    low, high = np.quantile(means, [0.025, 0.975])
    return {
        "families": len(d),
        "delta_pp": 100 * float(d.mean()),
        "ci95_low_pp": 100 * float(low),
        "ci95_high_pp": 100 * float(high),
        "bootstrap_seed": seed,
        "n_boot": n_boot,
        "unverified_policy": unverified_policy,
        "unverified_counts": dict(failure_counts),
        "dependence_limit": "shared_skills_sources_require_additional_cluster_sensitivity",
    }


def holm(p_values: list[float]) -> list[float]:
    if any(isinstance(p, bool) or not np.isfinite(p) or not 0 <= p <= 1 for p in p_values):
        raise ValueError("Invalid p value")
    adjusted = [0.0] * len(p_values)
    previous = 0.0
    for i, index in enumerate(sorted(range(len(p_values)), key=lambda j: p_values[j])):
        previous = max(previous, min(1.0, (len(p_values) - i) * p_values[index]))
        adjusted[index] = previous
    return adjusted
