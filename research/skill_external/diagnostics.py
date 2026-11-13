"""Post-hoc parser sensitivity; never overwrite strict model assessments."""

from __future__ import annotations

import json
from pathlib import Path

from .analysis import metrics


def parser_sensitivity(root: Path) -> dict:
    scored = [
        json.loads(s) for s in (root / "analysis-v3/scored.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    output = []
    for row in scored:
        trial = json.loads(
            (root / "deepseek-v1/trials" / (row["trial_id"] + ".json")).read_text(encoding="utf-8")
        )
        value = json.loads(trial["response"]["choices"][0]["message"]["content"])
        p = value.get("p_success")
        valid = (
            type(p) in (int, float)
            and 0 <= p <= 1
            and value.get("decision") == ("PASS" if p >= 0.5 else "FAIL")
        )
        output.append({**row, "schema_valid": valid, "p": p if valid else None})
    return {
        "posthoc": True,
        "changes_to_primary": False,
        "rule": "Read only mutually consistent probability and binary decision; disregard extra fields/citation count for this sensitivity diagnostic only",
        "by_arm": {
            arm: metrics([r for r in output if r["arm"] == arm])
            for arm in ["standard", "evidence_rules", "artifact_packet"]
        },
    }
