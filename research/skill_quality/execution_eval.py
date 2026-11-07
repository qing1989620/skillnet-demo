"""No external Skill runner in Phase A. Only a pure fixture verifier for mutation tests."""

from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation


def verify_sum_fixture(raw: bytes, *, expected_count: int, expected_sum: str) -> bool:
    """Deterministic fixture, not a D4/D5 task or evidence of Skill utility."""
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
        if reader.fieldnames != ["value"]:
            return False
        values = [Decimal(row["value"]) for row in reader]
        return (
            len(values) == expected_count
            and all(v.is_finite() for v in values)
            and sum(values, Decimal(0)) == Decimal(expected_sum)
        )
    except (ValueError, UnicodeError, KeyError, TypeError, InvalidOperation):
        return False


def require_execution_approval(*, docker_available: bool, approved: bool, manifest_frozen: bool) -> None:
    if not docker_available or not approved or not manifest_frozen:
        raise PermissionError(
            "Controlled execution needs Docker, reviewed approval and a frozen task/verifier manifest"
        )
    raise NotImplementedError("Actual Skill execution is outside the Phase A implementation")
