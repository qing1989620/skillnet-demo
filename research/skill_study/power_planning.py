"""Exact hypothetical paired-binary power, not observed Skill performance."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import binom


def power(n: int, delta: float, discordance: float = 0.2, alpha: float = 0.05) -> float:
    if n < 1 or not 0 < delta < discordance < 1 or not 0 < alpha < 1:
        raise ValueError("Invalid planning assumptions")
    disagreements = np.arange(n + 1)
    conditional_win = (discordance + delta) / (2 * discordance)
    upper_cut = binom.ppf(1 - alpha / 2, disagreements, 0.5)
    conditional_power = binom.sf(upper_cut, disagreements, conditional_win) + binom.cdf(
        disagreements - upper_cut - 1, disagreements, conditional_win
    )
    return float(np.sum(binom.pmf(disagreements, n, discordance) * conditional_power))


if __name__ == "__main__":
    rows = [
        {"independent_binary_units": n, "hypothetical_absolute_lift": delta, "power": power(n, delta)}
        for n in (40, 100, 150, 300, 600, 1000, 1500, 2000)
        for delta in (0.03, 0.05, 0.1)
    ]
    result = {
        "kind": "hypothetical_design_calculation_not_experimental_result",
        "assumptions": {
            "paired_discordance_probability": 0.2,
            "two_sided_alpha": 0.05,
            "independent_units": "one binary outcome per independent task family",
            "repeated_runs_are_not_extra_independent_units": True,
        },
        "method": "sum over binomial discordance counts of exact two-sided binomial rejection probability",
        "limitations": [
            "actual discordance and within-family dependence unknown until pilot",
            "not direct power for continuous task-macro or human ordinal scores",
            "not a risk certificate or measured improvement",
        ],
        "rows": rows,
    }
    destination = Path(__file__).with_name("results") / "power-planning.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([r for r in rows if r["independent_binary_units"] in (100, 600)]))
