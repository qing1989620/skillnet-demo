"""Owned, fixed worker. Reads requests, never labels; accepts no arbitrary code."""

from __future__ import annotations

import csv
import io
import json
import sys
from collections.abc import Callable
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

HEADER = ["sample_id", "subject_id", "split", "label", "score"]


def p0(state, intent):
    reader = csv.DictReader(io.StringIO(state["raw"], newline=""), strict=True)
    if reader.fieldnames != HEADER:
        raise ValueError("schema")
    state["rows"] = list(reader)
    if any(set(row) != set(HEADER) or any(v is None for v in row.values()) for row in state["rows"]):
        raise ValueError("row width")


def p1(state, intent):
    lines = state["raw"].strip().splitlines()
    state["rows"] = [dict(zip(lines[0].split(","), line.split(","), strict=True)) for line in lines[1:]]


def p2(state, intent):
    reader = csv.DictReader(io.StringIO(state["raw"], newline=""), strict=True)
    state["rows"] = [{k: v.strip() for k, v in row.items()} for row in reader]


def d0(state, intent):
    retained = {}
    for row in state["rows"]:
        retained.setdefault(row["sample_id"], row)
    state["rows"] = list(retained.values())


def d1(state, intent):
    retained = {}
    for row in state["rows"]:
        retained[row["sample_id"]] = row
    state["rows"] = list(retained.values())


def d2(state, intent):
    seen = set()
    output = []
    for row in state["rows"]:
        key = tuple(row[k] for k in HEADER)
        if key not in seen:
            output.append(row)
            seen.add(key)
    state["rows"] = output


def x0(state, intent):
    subjects = {}
    for row in state["rows"]:
        subjects.setdefault(row["subject_id"], set()).add(row["split"])
    bad = {s for s, splits in subjects.items() if len(splits) > 1}
    state["rows"] = [r for r in state["rows"] if r["subject_id"] not in bad]


def x1(state, intent):
    first = {}
    for row in state["rows"]:
        first.setdefault(row["subject_id"], row["split"])
    state["rows"] = [r for r in state["rows"] if r["split"] == first[r["subject_id"]]]


def x2(state, intent):
    counts = {}
    for row in state["rows"]:
        counts[row["subject_id"]] = counts.get(row["subject_id"], 0) + 1
    state["rows"] = [r for r in state["rows"] if counts[r["subject_id"]] == 1]


def m0(state, intent):
    state["rows"] = [r for r in state["rows"] if r["score"] != ""]


def m1(state, intent):
    state["rows"] = [r for r in state["rows"] if r["score"].strip().lower() not in {"", "na", "n/a", "null"}]


def m2(state, intent):
    state["rows"] = [r for r in state["rows"][:-1] if r["score"] != ""]


def metric_values(rows, threshold, mode):
    counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    for row in rows:
        if row["score"] == "":
            continue
        score = float(row["score"]) if mode == "float" else Decimal(row["score"])
        bound = float(threshold) if mode == "float" else Decimal(threshold)
        positive = score > bound if mode == "strict" else score >= bound
        label = int(row["label"])
        if label not in {0, 1}:
            raise ValueError("binary label")
        counts["tp" if positive and label else "fp" if positive else "fn" if label else "tn"] += 1
    tp, tn, fp, fn = (counts[k] for k in ["tp", "tn", "fp", "fn"])
    n = tp + tn + fp + fn
    with localcontext() as context:
        context.prec = 40

        def ratio(a, b):
            return str(Decimal(a) / Decimal(b)) if b else "0"

        return {
            **{k: str(v) for k, v in counts.items()},
            "n": str(n),
            "accuracy": ratio(tp + tn, n),
            "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, tp + fn),
            "f1": ratio(2 * tp, 2 * tp + fp + fn),
        }


def t0(state, intent):
    state["metrics"] = metric_values(state["rows"], intent["threshold"], "decimal")


def t1(state, intent):
    state["metrics"] = metric_values(state["rows"], intent["threshold"], "strict")


def t2(state, intent):
    state["metrics"] = metric_values(state["rows"], intent["threshold"], "float")


def b0(state, intent):
    d0(state, intent)
    x0(state, intent)
    m0(state, intent)


def b1(state, intent):
    m0(state, intent)
    x0(state, intent)
    d0(state, intent)


def b2(state, intent):
    d1(state, intent)
    x0(state, intent)
    m0(state, intent)


OPS: dict[str, Callable[..., Any]] = {
    f.__name__: f for f in [p0, p1, p2, d0, d1, d2, x0, x1, x2, m0, m1, m2, t0, t1, t2, b0, b1, b2]
}


def execute(request):
    state = request.get("initial_state", {"raw": request.get("raw", "")}).copy()
    trace, error = [], None
    for key in request["plan"]:
        if key not in OPS or len(trace) >= 5:
            error = "unsupported_plan_or_call_limit"
            break
        trace.append(key)
        try:
            OPS[key](state, request["intent"])
        except (ValueError, TypeError, KeyError, csv.Error, ArithmeticError) as exc:
            error = type(exc).__name__ + ":" + str(exc)[:200]
            break
    return {
        "execution_id": request["execution_id"],
        "rows": state.get("rows"),
        "metrics": state.get("metrics"),
        "trace": trace,
        "calls": len(trace),
        "error": error,
    }


if __name__ == "__main__":
    with Path(sys.argv[1]).open(encoding="utf-8") as stream:
        for line in stream:
            result = execute(json.loads(line))
            print(json.dumps(result, ensure_ascii=False), flush=True)
