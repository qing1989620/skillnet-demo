from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from research.skill_execution.experiment import Ledger, messages
from research.skill_execution.tasks import make_tasks, verifier_diagnostics, verify_artifact


def test_constructed_labels_match_serialized_csv_and_pandas_readers() -> None:
    cases = make_tasks()
    assert len(cases) == 30
    result = verifier_diagnostics(cases)
    assert result["csv_three_route_agreements"] == 24
    assert result["boundary_spec_labels_checked"] == 6
    assert result["fixture_and_mutation_checks"] == 390 and result["all_pass"]


def test_literal_na_whitespace_and_quoted_newlines_keep_declared_semantics() -> None:
    cases = make_tasks()
    for condition in ["literal_na", "whitespace_cells", "quoted_newline"]:
        case = next(c for c in cases if c["condition"] == condition)
        assert case["expected"]["row_count"] == 8
        assert case["expected"]["missing_by_column"]["amount"] == 0
    assert (
        next(c for c in cases if c["condition"] == "repeated_key_only")["expected"]["duplicate_extra_rows"]
        == 0
    )


@pytest.mark.parametrize("value", [True, 8.0, "8"])
def test_valid_value_with_wrong_type_is_rejected(value: object) -> None:
    expected = make_tasks()[0]["expected"]
    output = copy.deepcopy(expected)
    output["row_count"] = value
    assert not verify_artifact(output, expected)["task_success"]


def test_refusal_cannot_win_an_in_scope_task() -> None:
    case = make_tasks()[0]
    output = {**case["expected"], "status": "blocked", "row_count": None}
    assert not verify_artifact(output, case["expected"])["task_success"]


def test_task_answers_are_not_part_of_api_payload() -> None:
    case = make_tasks()[0]
    payload = json.loads(messages(case["input"], "guidance")[1]["content"])
    assert "expected" not in payload and "expected" not in payload["task"]
    assert "family" not in payload["task"]
    with pytest.raises(ValueError, match="leakage"):
        messages(case, "guidance")


def test_two_inflight_reservations_are_bounded(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    try:
        ledger.reserve("a")
        ledger.reserve("b")
        with pytest.raises(RuntimeError, match="Concurrency"):
            ledger.reserve("c")
        ledger.settle("a", {"USD": "0.01", "CNY": "0.1"})
        ledger.reserve("c")
    finally:
        ledger.close()


def test_unknown_call_blocks_future_scheduling_after_restart(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger(path)
    ledger.reserve("a")
    ledger.fail("a", "Timeout")
    ledger.close()
    restarted = Ledger(path)
    try:
        with pytest.raises(RuntimeError, match="Unknown"):
            restarted.reserve("b")
    finally:
        restarted.close()
