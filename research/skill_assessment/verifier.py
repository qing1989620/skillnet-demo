"""Owned illustrative CSV task and a deterministic artifact verifier.

The reference output is a constructed fixture, NOT an Agent/Skill result. This
public development task must never be reused as a hidden scientific test set.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any

CSV_INPUT = (
    "id,amount,observed_at\n"
    "1,10,2026-11-01\n"
    "2,,2026-10-01\n"
    "2,,2026-10-01\n"
    "3,999,2026-11-04\n"
    "4,15,2026-11-04\n"
    "5,20,2026-11-05\n"
)


def task_spec() -> dict[str, Any]:
    return {
        "id": "development-csv-audit-001",
        "status": "public_verifier_development_fixture_not_held_out",
        "input_sha256": hashlib.sha256(CSV_INPUT.encode("utf-8")).hexdigest(),
        "as_of": "2026-11-05",
        "stale_rule": "age_in_calendar_days > 7",
        "missing_rule": "empty CSV field only; header excluded",
        "duplicate_rule": "full-row duplicates beyond first occurrence; no automatic deletion",
        "request": "Report row count, missing fields per column, duplicate extra rows, stale rows and maximum age. Read only.",
        "expected_output_keys": [
            "input_sha256",
            "row_count",
            "missing_by_column",
            "duplicate_extra_rows",
            "stale_rows",
            "max_age_days",
            "actions",
        ],
        "skill_execution_trials": 0,
    }


def reference_fixture() -> dict[str, Any]:
    # Known by construction, rather than borrowed from a Skill's DQS formula.
    return {
        "input_sha256": task_spec()["input_sha256"],
        "row_count": 6,
        "missing_by_column": {"id": 0, "amount": 2, "observed_at": 0},
        "duplicate_extra_rows": 1,
        "stale_rows": 2,
        "max_age_days": 35,
        "actions": [],
    }


def verify_artifact(artifact: Any) -> dict[str, Any]:
    expected = reference_fixture()
    if not isinstance(artifact, dict):
        return {"task_success": False, "checks": {"object_schema": False}}
    checks = {"exact_schema": set(artifact) == set(expected)}
    for key, value in expected.items():
        candidate = artifact.get(key)
        # Avoid Python equality accepting True as 1, or 6.0 as integer 6.
        if isinstance(value, dict):
            checks[key] = (
                isinstance(candidate, dict)
                and set(candidate) == set(value)
                and all(type(candidate[k]) is int and candidate[k] == v for k, v in value.items())
            )
        else:
            checks[key] = type(candidate) is type(value) and candidate == value
    return {
        "task_success": all(checks.values()),
        "checks": checks,
        "meaning": "artifact_matches_this_constructed_task_not_general_skill_quality",
    }


def mutation_diagnostics() -> list[dict[str, Any]]:
    variants: list[tuple[str, Any, bool]] = [("constructed_reference", reference_fixture(), True)]
    replacements = {
        "row_count": 7,
        "missing_by_column": {"id": 0, "amount": 0, "observed_at": 0},
        "duplicate_extra_rows": 0,
        "stale_rows": 0,
        "max_age_days": 0,
        "input_sha256": "0" * 64,
        "actions": ["delete_duplicates"],
    }
    for key, replacement in replacements.items():
        changed = copy.deepcopy(reference_fixture())
        changed[key] = replacement
        variants.append(("mutated_" + key, changed, False))
    boolean_number = reference_fixture()
    boolean_number["duplicate_extra_rows"] = True
    variants.append(("boolean_is_not_integer", boolean_number, False))
    missing_field = reference_fixture()
    missing_field.pop("stale_rows")
    variants.append(("missing_required_field", missing_field, False))
    variants.append(("non_object", "I completed the audit correctly", False))
    return [
        {
            "id": name,
            "expected_accept": expected_accept,
            "observed_accept": verify_artifact(artifact)["task_success"],
            "diagnostic_pass": verify_artifact(artifact)["task_success"] == expected_accept,
            "artifact_origin": "constructed_fixture_or_deliberate_mutation_not_agent_execution",
        }
        for name, artifact, expected_accept in variants
    ]
