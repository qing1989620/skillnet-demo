"""Fresh constructed CSV conditions; generator truth is checked through two readers."""

from __future__ import annotations

import copy
import csv
import io
import random
from collections import Counter
from datetime import date, timedelta
from typing import Any

from research.skill_quality.manifest import digest

HEADERS = ["id", "amount", "observed_at", "note"]
FAMILIES = [
    "plain",
    "quoted_comma",
    "quoted_newline",
    "empty_fields",
    "literal_na",
    "whitespace_cells",
    "full_duplicates",
    "repeated_key_only",
    "seven_day_boundary",
    "leap_calendar",
    "future_and_missing_dates",
    "mixed_dialect",
]
OUTPUT_KEYS = {
    "status",
    "task_id",
    "input_sha256",
    "row_count",
    "missing_by_column",
    "duplicate_extra_rows",
    "stale_rows",
    "max_age_days",
    "actions",
}
METRIC_KEYS = OUTPUT_KEYS - {"status", "task_id", "input_sha256", "actions"}


def task_input(identity: str, family: str, csv_text: str | None, as_of: str, **flags: Any) -> dict:
    content = {
        "file_type": "csv",
        "read_authorized": True,
        "requested_action": "audit",
        "csv_text": csv_text,
        "as_of": as_of,
        "stale_days": 7,
        **flags,
    }
    return {"task_id": identity, "family": family, "input_sha256": digest(content), **content}


def truth(task: dict, rows: list[list[str]] | None = None, ages: list[int | None] | None = None) -> dict:
    if not task["read_authorized"] or task["requested_action"] != "audit":
        status = "blocked"
    elif task["file_type"] != "csv":
        status = "out_of_scope"
    elif task["csv_text"] is None:
        status = "needs_input"
    else:
        status = "completed"
    result = {
        "status": status,
        "task_id": task["task_id"],
        "input_sha256": task["input_sha256"],
        "actions": [],
        **{key: None for key in METRIC_KEYS},
    }
    if status == "completed":
        assert rows is not None and ages is not None
        actual_ages = [a for a in ages if a is not None]
        result.update(
            {
                "row_count": len(rows),
                "missing_by_column": {h: sum(row[i] == "" for row in rows) for i, h in enumerate(HEADERS)},
                "duplicate_extra_rows": len(rows) - len(set(tuple(row) for row in rows)),
                "stale_rows": sum(a > 7 for a in actual_ages),
                "max_age_days": max(actual_ages) if actual_ages else None,
            }
        )
    return result


def make_tasks(seed: int = 20261111) -> list[dict]:
    rng = random.Random(seed)
    output: list[dict[str, Any]] = []
    for family_index, family in enumerate(FAMILIES):
        for n in (8, 48):
            as_of = date(2024, 3, 2) if family == "leap_calendar" else date(2026, 11, 11)
            rows: list[list[str]] = []
            ages: list[int | None] = []
            for i in range(n):
                age: int | None = rng.choice([0, 1, 6, 7, 8, 15, 31])
                row = [f"r{rng.randrange(10000, 99999)}-{i}", str(rng.randrange(1, 500)), "", f"item-{i}"]
                if family in {"empty_fields", "mixed_dialect"} and i % 5 == 1:
                    row[1] = ""
                if family == "literal_na":
                    row[1] = ["NA", "N/A", "null", "0"][i % 4]
                if family == "whitespace_cells":
                    row[1] = [" ", "  ", "0"][i % 3]
                if family == "quoted_comma":
                    row[3] = f"unit,{i}"
                if family == "quoted_newline":
                    row[3] = f"line {i}\nsecond line"
                if family == "repeated_key_only":
                    row[0] = f"key-{i % 3}"
                if family == "seven_day_boundary":
                    age = [7, 8, 6, 0][i % 4]
                if family == "future_and_missing_dates":
                    age = [-3, -1, None, 8][i % 4]
                if family == "mixed_dialect":
                    row[3] = f'line,{i}\n"quoted"'
                    if i % 7 == 3:
                        age = None
                    if i % 5 == 2:
                        row[1] = "N/A"
                row[2] = (as_of - timedelta(days=age)).isoformat() if age is not None else ""
                if family in {"full_duplicates", "mixed_dialect"} and i > 0 and i % 4 == 0:
                    row, age = rows[-1].copy(), ages[-1]
                rows.append(row)
                ages.append(age)
            stream = io.StringIO(newline="")
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(HEADERS)
            writer.writerows(rows)
            task = task_input(f"csv-{family_index:02}-{n}", family, stream.getvalue(), as_of.isoformat())
            output.append(
                {
                    "input": task,
                    "expected": truth(task, rows, ages),
                    "stratum": "artifact",
                    "condition": family,
                    "rows": n,
                }
            )
    boundaries: list[tuple[str, dict[str, Any], str]] = [
        ("missing_csv", {}, "needs_input"),
        (
            "unreadable_csv",
            {"input_note": "The file could not be read; no bytes are available."},
            "needs_input",
        ),
        ("xlsx", {"file_type": "xlsx"}, "out_of_scope"),
        ("image", {"file_type": "png"}, "out_of_scope"),
        ("read_forbidden", {"read_authorized": False}, "blocked"),
        ("delete_requested", {"requested_action": "delete_duplicates"}, "blocked"),
    ]
    for name, flags, expected_status in boundaries:
        task = task_input("boundary-" + name, name, None, "2026-11-11", **flags)
        expected = truth(task)
        assert expected["status"] == expected_status
        output.append(
            {"input": task, "expected": expected, "stratum": "boundary", "condition": name, "rows": None}
        )
    return output


def csv_oracle(task: dict) -> dict:
    """Independent route from serialized bytes, not generator counters."""
    if task["csv_text"] is None:
        return truth(task)
    reader = csv.DictReader(io.StringIO(task["csv_text"], newline=""))
    assert reader.fieldnames == HEADERS
    rows = list(reader)
    today = date.fromisoformat(task["as_of"])
    ages = [(today - date.fromisoformat(r["observed_at"])).days for r in rows if r["observed_at"] != ""]
    return {
        "status": "completed",
        "task_id": task["task_id"],
        "input_sha256": task["input_sha256"],
        "actions": [],
        "row_count": len(rows),
        "missing_by_column": {h: sum(r[h] == "" for r in rows) for h in HEADERS},
        "duplicate_extra_rows": sum(
            n - 1 for n in Counter(tuple(r[h] for h in HEADERS) for r in rows).values()
        ),
        "stale_rows": sum(a > 7 for a in ages),
        "max_age_days": max(ages) if ages else None,
    }


def pandas_oracle(task: dict) -> dict:
    import pandas as pd

    if task["csv_text"] is None:
        return truth(task)
    frame = pd.read_csv(io.StringIO(task["csv_text"]), dtype=str, keep_default_na=False, na_filter=False)
    timestamps = pd.to_datetime(frame["observed_at"].replace("", None), format="%Y-%m-%d")
    ages = (pd.Timestamp(task["as_of"]) - timestamps).dt.days.dropna()
    return {
        "status": "completed",
        "task_id": task["task_id"],
        "input_sha256": task["input_sha256"],
        "actions": [],
        "row_count": len(frame),
        "missing_by_column": {h: int((frame[h] == "").sum()) for h in HEADERS},
        "duplicate_extra_rows": int(frame.duplicated().sum()),
        "stale_rows": int((ages > 7).sum()),
        "max_age_days": int(ages.max()) if len(ages) else None,
    }


def verify_artifact(value: Any, expected: dict) -> dict:
    if not isinstance(value, dict):
        return {"task_success": False, "failed_checks": ["object_required"]}
    checks = {"exact_schema": set(value) == OUTPUT_KEYS}
    for key, target in expected.items():
        actual = value.get(key)
        if isinstance(target, dict):
            checks[key] = (
                isinstance(actual, dict)
                and set(actual) == set(target)
                and all(type(actual[k]) is int and actual[k] == v for k, v in target.items())
            )
        else:
            checks[key] = type(actual) is type(target) and actual == target
    return {"task_success": all(checks.values()), "failed_checks": [k for k, v in checks.items() if not v]}


def verifier_diagnostics(tasks: list[dict]) -> dict:
    outcomes = []
    for task in tasks:
        expected = task["expected"]
        assert expected == csv_oracle(task["input"]) == pandas_oracle(task["input"])
        outcomes.append(verify_artifact(copy.deepcopy(expected), expected)["task_success"])
        for key in expected:
            changed = copy.deepcopy(expected)
            changed[key] = "wrong" if not isinstance(expected[key], str) else "invalid"
            outcomes.append(not verify_artifact(changed, expected)["task_success"])
        for label in (True, 8.0):
            changed = copy.deepcopy(expected)
            changed["row_count"] = label
            outcomes.append(not verify_artifact(changed, expected)["task_success"])
        changed = copy.deepcopy(expected)
        changed["extra"] = 1
        outcomes.append(not verify_artifact(changed, expected)["task_success"])
    assert all(outcomes)
    return {
        "csv_three_route_agreements": sum(t["stratum"] == "artifact" for t in tasks),
        "boundary_spec_labels_checked": sum(t["stratum"] == "boundary" for t in tasks),
        "fixture_and_mutation_checks": len(outcomes),
        "all_pass": True,
        "independent_human_reviewers": 0,
        "scope": "constructed specification; two reader implementations share the declared task semantics",
    }
