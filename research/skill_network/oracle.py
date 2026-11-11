"""Index-based reference with rational arithmetic; no worker/planner imports."""

from __future__ import annotations

import csv
import io
from fractions import Fraction

HEADER = ["sample_id", "subject_id", "split", "label", "score"]


def reference(raw: str, intent: dict) -> dict:
    table = list(csv.reader(io.StringIO(raw, newline=""), strict=True))
    if not table or table[0] != HEADER or any(len(row) != 5 for row in table[1:]):
        raise ValueError("reference schema")
    rows = [r.copy() for r in table[1:]]
    stages = {"parse": [r.copy() for r in rows]}
    if intent["mask"] & 1:
        kept = []
        identifiers = []
        for row in rows:
            if row[0] not in identifiers:
                identifiers.append(row[0])
                kept.append(row)
        rows = kept
        stages["dedup"] = [r.copy() for r in rows]
    if intent["mask"] & 2:
        bad = []
        for row in rows:
            if any(other[1] == row[1] and other[2] != row[2] for other in rows):
                bad.append(row[1])
        rows = [r for r in rows if r[1] not in bad]
        stages["exclude"] = [r.copy() for r in rows]
    if intent["mask"] & 4:
        rows = [r for r in rows if len(r[4]) > 0]
        stages["drop"] = [r.copy() for r in rows]
    stages["bundle"] = [r.copy() for r in rows]
    tn = fp = fn = tp = 0
    for row in rows:
        if len(row[4]) == 0:
            continue
        prediction = Fraction(row[4]) >= Fraction(intent["threshold"])
        label = row[3]
        if label not in {"0", "1"}:
            raise ValueError("reference binary label")
        if prediction:
            if label == "1":
                tp += 1
            else:
                fp += 1
        elif label == "1":
            fn += 1
        else:
            tn += 1
    n = tn + fp + fn + tp

    def fraction(a, b):
        return str(Fraction(a, b)) if b else "0"

    metrics = {
        "n": str(n),
        "tp": str(tp),
        "tn": str(tn),
        "fp": str(fp),
        "fn": str(fn),
        "accuracy": fraction(tp + tn, n),
        "precision": fraction(tp, tp + fp),
        "recall": fraction(tp, tp + fn),
        "f1": fraction(2 * tp, 2 * tp + fp + fn),
    }
    return {"rows": rows, "metrics": metrics, "stages": stages}


def artifact_rows(value: object) -> list | None:
    if not isinstance(value, list) or any(not isinstance(r, dict) or set(r) != set(HEADER) for r in value):
        return None
    return [[r[k] for k in HEADER] for r in value]


def verify(output: dict, expected: dict, *, cap: str = "metrics") -> dict:
    rows = artifact_rows(output.get("rows"))
    target = expected["stages"][cap] if cap != "metrics" else expected["rows"]
    checks = {"process": output.get("error") is None, "exact_rows": rows == target}
    if cap == "metrics":
        metrics = output.get("metrics")
        checks["metric_schema"] = isinstance(metrics, dict) and set(metrics) == set(expected["metrics"])
        for key, wanted in expected["metrics"].items():
            try:
                actual = metrics[key] if isinstance(metrics, dict) else None
                checks[key] = (
                    type(actual) is str
                    and len(actual) < 128
                    and abs(Fraction(actual) - Fraction(wanted)) <= Fraction(1, 10**12)
                )
            except (ValueError, ZeroDivisionError):
                checks[key] = False
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [k for k, v in checks.items() if not v],
    }
