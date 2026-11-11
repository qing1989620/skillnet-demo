"""Recompute released decisions and artifact verdicts without execution or API calls."""

from __future__ import annotations

import json
from pathlib import Path

from research.skill_quality.manifest import digest, read_jsonl, verify_files

from .benchmark import METHODS, make_static_cases, predict, summarize
from .gate import Bundle
from .owned import PROGRAMS, make_inputs, program_bundle, verify_output

RESULTS = Path(__file__).with_name("results")


def reproduce(root: Path = RESULTS) -> dict:
    run = root / "diagnostic-v3"
    verify_files(run, json.loads((run / "manifest.json").read_text(encoding="utf-8")))
    cases = read_jsonl(run / "static-fixtures.jsonl")
    fixtures = read_jsonl(run / "behavior-inputs.jsonl")
    assert digest(cases) == digest(make_static_cases())
    assert digest(fixtures) == digest(make_inputs())
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    predictions = read_jsonl(run / "predictions.jsonl")
    by_case = {c["id"]: c for c in cases}
    receipts = read_jsonl(run / "receipts.jsonl")
    trials = read_jsonl(run / "owned-trials.jsonl")
    by_program = {}
    fixture_by_id = {f["id"]: f for f in fixtures}
    for program in PROGRAMS:
        rows = [r for r in trials if r["program"] == program]
        receipt = next(r for r in receipts if r["bundle_fingerprint"] == program_bundle(program).fingerprint)
        assert len(rows) == receipt["n"] == 24
        assert sum(r["passed"] for r in rows) == receipt["passed"]
        assert digest(rows) == receipt["outcomes_sha256"]
        assert receipt["executed_source_sha256"] == program_bundle(program).expected_hashes["scripts/run.py"]
        assert digest({k: v for k, v in receipt.items() if k != "receipt_id"}) == receipt["receipt_id"]
        for input_hash, result in receipt["input_outcomes"].items():
            selected = [r for r in rows if r["input_sha256"] == input_hash]
            assert result == {"n": len(selected), "passed": sum(r["passed"] for r in selected)}
        for row in rows:
            fixture = fixture_by_id[row["fixture_id"]]
            assert digest(fixture["input"]) == row["input_sha256"]
            assert row["executed_source_sha256"] == receipt["executed_source_sha256"]
            assert (row["returncode"] == 0 and verify_output(fixture, row["artifact"])) == row["passed"]
        by_program[program] = receipt
    for row in predictions:
        if row["cohort"] == "static":
            bundle = Bundle(**by_case[row["case_id"]]["bundle"])
            result = predict(bundle, row["method"])
        else:
            bundle = program_bundle(row["case_id"])
            result = predict(bundle, row["method"], receipt=by_program[row["case_id"]])
        assert result["decision"] == row["decision"]
    for cohort in ["development", "test", "behavior"]:
        for method in METHODS:
            subset = [
                r
                for r in predictions
                if r["method"] == method
                and ((r["cohort"] == "static" and r["split"] == cohort) or r["cohort"] == cohort)
            ]
            assert summarize(subset) == summary["metrics"][cohort][method]
    natural = root / "natural-v3"
    verify_files(natural, json.loads((natural / "manifest.json").read_text(encoding="utf-8")))
    reports = read_jsonl(natural / "reports.jsonl")
    assert len(reports) == 200 and sum(r["decision"] == "repair_required" for r in reports) == 1
    assert sum(len(r["command_observations"]) for r in reports) == 470
    unresolved = sum(c["reason"] == "entrypoint_unresolved" for r in reports for c in r["unknown_checks"])
    assert unresolved == 79
    return {
        "status": "PASS",
        "api_calls": 0,
        "programs_executed_by_replay": 0,
        "predictions_recomputed": len(predictions),
        "owned_artifacts_reverified": len(trials),
        "static_test_parents": 20,
        "static_test_cases": 200,
        "natural_packages": 200,
        "natural_command_observations": 470,
        "natural_unresolved_entrypoints_separately_accounted": unresolved,
        "scope": "Offline integrity and decision reproduction, not independent human semantic validation",
    }


if __name__ == "__main__":
    print(json.dumps(reproduce(), ensure_ascii=False, indent=2))
