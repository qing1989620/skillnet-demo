"""Constructive diagnostic truth, independent reference, fixed splits and ablations."""

from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import random
import shlex
from pathlib import Path

from research.skill_quality.manifest import freeze_files, read_jsonl, verify_files, write_once
from research.skill_study.cli_contracts import check_command, parse_contract, standard_library_reference

from .gate import Bundle, evaluate, from_texts
from .owned import PROGRAMS, make_inputs, program_bundle, run_owned

METHODS = [
    "document_heuristic",
    "option_names_only",
    "native_argparse_only",
    "static_gate",
    "full_gate",
    "without_integrity",
    "without_cli",
    "without_behavior",
]


def native_spec_reference(spec: dict, command: str) -> bool:
    # This reference never parses the detector's AST or uses its extracted
    # ParserContract: construct argparse directly from the generator schema.
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(spec["source"], required=True)
    parser.add_argument(spec["mode"], choices=spec["choices"])
    parser.add_argument(spec["limit"], type=int)
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            parser.parse_args(shlex.split(command, comments=True)[2:])
        except SystemExit:
            return False
    return True


def make_static_cases() -> list[dict]:
    parents = list(range(60))
    random.Random(20261111).shuffle(parents)
    test_parents = set(parents[:20])
    output = []
    for parent in range(60):
        spec = {
            "source": f"--source-{parent}",
            "mode": f"--format-{parent}",
            "limit": f"--count-{parent}",
            "choices": [f"json{parent}", f"csv{parent}"],
        }
        parser_name = ["parser", "cli", "options"][parent % 3]
        source = (
            f"import argparse\n{parser_name} = argparse.ArgumentParser(allow_abbrev=False)\n"
            f"{parser_name}.add_argument('{spec['source']}', required=True)\n"
            f"{parser_name}.add_argument('{spec['mode']}', choices={spec['choices']!r})\n"
            f"{parser_name}.add_argument('{spec['limit']}', type=int)\n"
            f"args = {parser_name}.parse_args()\n"
        )
        command = f"python scripts/run.py {spec['source']} 'input {parent}.csv' {spec['mode']} {spec['choices'][0]} {spec['limit']} -7"
        doc = (
            "# Dataset audit fixture\n1. Read the data with Python.\n2. Check the input schema.\n"
            "3. Compute the statistics.\n4. Verify the result JSON.\n"
            "Pitfalls: preserve source rows; validate date boundaries.\n"
            "Verification: exact schema; compare expected outputs.\n"
            "Budget: 1000 token budget.\n```bash\n" + command + "\n```\n"
        )
        base = from_texts(f"controlled-{parent:02}", {"SKILL.md": doc, "scripts/run.py": source})
        for kind in [
            "intact",
            "benign_comment",
            "unknown_option",
            "missing_required",
            "invalid_choice",
            "wrong_type",
            "missing_entry",
            "tampered_resource",
            "syntax_error",
            "unsupported_factory",
        ]:
            files, hashes = copy.deepcopy(base.files), copy.deepcopy(base.expected_hashes)
            edited_command, edited_source = command, source
            defect: bool | None = kind not in {"intact", "benign_comment"}
            if kind == "benign_comment":
                edited_command += "  # documentation comment --not-an-option"
            elif kind == "unknown_option":
                edited_command += " --invented-option 1"
            elif kind == "missing_required":
                edited_command = f"python scripts/run.py {spec['mode']} {spec['choices'][0]}"
            elif kind == "invalid_choice":
                edited_command = command.replace(spec["choices"][0], "unlisted")
            elif kind == "wrong_type":
                edited_command = command.replace(" -7", " not-an-int")
            elif kind == "syntax_error":
                edited_source += "def unfinished(\n"
            elif kind == "unsupported_factory":
                edited_source = (
                    "from helper import parser_factory\nparser = parser_factory()\nparser.parse_args()\n"
                )
                defect = None
            files["SKILL.md"] = doc.replace(command, edited_command)
            files["scripts/run.py"] = edited_source
            # For most counterfactual versions, update their declared inventory.
            # Missing/tampered versions deliberately violate the pinned inventory.
            bundle = from_texts(base.identity, files)
            if kind == "missing_entry":
                files.pop("scripts/run.py")
                bundle = Bundle(base.identity, files, hashes, bundle.examples)
            elif kind == "tampered_resource":
                files["scripts/run.py"] += "# bytes changed after the version was pinned\n"
                bundle = Bundle(base.identity, files, hashes, bundle.examples)
            if kind in {
                "intact",
                "benign_comment",
                "unknown_option",
                "missing_required",
                "invalid_choice",
                "wrong_type",
            }:
                assert native_spec_reference(spec, edited_command) is (not defect)
            output.append(
                {
                    "id": f"p{parent:02}-{kind}",
                    "parent": f"p{parent:02}",
                    "split": "test" if parent in test_parents else "development",
                    "kind": kind,
                    "known_defect": defect,
                    "bundle": {
                        "identity": bundle.identity,
                        "files": bundle.files,
                        "expected_hashes": bundle.expected_hashes,
                        "examples": bundle.examples,
                    },
                }
            )
    return output


def document_score(bundle: Bundle) -> float:
    from skillnet.schema import Skill, assess_quality, quality_score

    document = bundle.files.get("SKILL.md", "")
    steps = [line for line in document.splitlines() if line[:1].isdigit()]
    card = Skill(
        name=bundle.identity,
        description=document,
        domain="research",
        steps=steps,
        pitfalls=["preserve input", "validate boundary"],
        verification=["schema", "outputs"],
        relations=[("related", "audit")],
    )
    return quality_score(assess_quality(card))


def predict(bundle: Bundle, method: str, *, receipt: dict | None = None) -> dict:
    if method == "document_heuristic":
        score = document_score(bundle)
        # Fixed reporting adaptation; production uses a ranking prior, not this
        # binary release rule. It was not calibrated on this diagnostic test.
        return {
            "decision": "repair_required" if score < 0.8 else "tested_pass_within_scope",
            "confirmed_defect": score < 0.8,
            "document_score": score,
            "interpretation": "uncalibrated >=.8 document-score acceptance comparator",
        }
    if method in {"option_names_only", "native_argparse_only"}:
        observed = []
        for example in bundle.examples:
            if example["script"] not in bundle.files:
                observed.append("unknown")
                continue
            contract = parse_contract(bundle.files[example["script"]])
            observed.append(
                check_command(contract, example["command"], values=False)["status"]
                if method == "option_names_only"
                else standard_library_reference(contract, example["command"])
            )
        bad = "inconsistent_static" in observed
        decision = (
            "repair_required"
            if bad
            else "insufficient_evidence"
            if "unknown" in observed or not observed
            else "tested_pass_within_scope"
        )
        return {
            "decision": decision,
            "confirmed_defect": bad,
            "interpretation": "CLI-only diagnostic acceptance, not a runtime certificate",
        }
    omission = {
        "static_gate": {"behavior"},
        "full_gate": set(),
        "without_integrity": {"integrity"},
        "without_cli": {"cli"},
        "without_behavior": {"behavior"},
    }[method]
    return evaluate(
        bundle,
        task_family=receipt["task_family"] if receipt else None,
        behavior=receipt,
        trusted_behavior_ids=frozenset({receipt["receipt_id"]}) if receipt else frozenset(),
        omit=frozenset(omission),
    )


def summarize(rows: list[dict]) -> dict:
    positives = [r for r in rows if r["gold_defect"] is True]
    benign = [r for r in rows if r["gold_defect"] is False]
    unknown = [r for r in rows if r["gold_defect"] is None]
    tp = sum(r["decision"] == "repair_required" for r in positives)
    fp = sum(r["decision"] == "repair_required" for r in benign)
    accepted = [r for r in rows if r["decision"] == "tested_pass_within_scope"]
    return {
        "n": len(rows),
        "known_defects": len(positives),
        "benign_controls": len(benign),
        "unlabelled_scope_cases": len(unknown),
        "defects_detected": tp,
        "false_alarms": fp,
        "defect_recall": tp / len(positives) if positives else None,
        "benign_false_alarm_rate": fp / len(benign) if benign else None,
        "abstentions": sum(r["decision"] == "insufficient_evidence" for r in rows),
        "correct_releases": sum(r["gold_defect"] is False for r in accepted),
        "incorrect_releases": sum(r["gold_defect"] is True for r in accepted),
        "unlabelled_releases": sum(r["gold_defect"] is None for r in accepted),
        "correct_release_coverage": sum(r["gold_defect"] is False for r in accepted) / len(benign)
        if benign
        else None,
    }


def run(output: Path, *, backend: str = "trusted_process") -> dict:
    if output.exists():
        raise FileExistsError("Use a fresh diagnostic run ID")
    output.mkdir(parents=True)
    static, fixtures = make_static_cases(), make_inputs()
    write_once(
        output / "plan.json",
        json.loads(Path(__file__).with_name("protocol.json").read_text(encoding="utf-8")),
    )
    write_once(output / "static-fixtures.jsonl", static, jsonl=True)
    write_once(output / "behavior-inputs.jsonl", fixtures, jsonl=True)
    source = list(Path(__file__).parent.glob("*.py")) + [Path(__file__).with_name("protocol.json")]
    write_once(output / "code-manifest.json", freeze_files(Path.cwd(), source))
    for path in source:
        target = output / "code-snapshot" / path.name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(path.read_bytes())
    predictions = []
    for case in static:
        bundle = Bundle(**case["bundle"])
        for method in METHODS:
            result = predict(bundle, method)
            predictions.append(
                {
                    "case_id": case["id"],
                    "parent": case["parent"],
                    "cohort": "static",
                    "split": case["split"],
                    "kind": case["kind"],
                    "method": method,
                    "gold_defect": case["known_defect"],
                    "decision": result["decision"],
                }
            )
    receipts, trials, behavior_reports = [], [], []
    for program in PROGRAMS:
        bundle = program_bundle(program)
        receipt, observed = run_owned(bundle, program, fixtures, backend=backend)
        receipts.append(receipt)
        trials.extend(observed)
        for method in METHODS:
            result = predict(bundle, method, receipt=receipt)
            predictions.append(
                {
                    "case_id": program,
                    "parent": program,
                    "cohort": "behavior",
                    "split": "constructed_behavior",
                    "kind": PROGRAMS[program][0],
                    "method": method,
                    "gold_defect": not program.endswith("_correct"),
                    "decision": result["decision"],
                }
            )
            if method == "full_gate":
                behavior_reports.append({"program": program, "report": result})
    summary = {
        "date": "2026-11-11",
        "method": "evidence_constrained_skill_decision_v1",
        "api_calls": 0,
        "api_cost_usd": 0,
        "backend": backend,
        "community_code_executions": 0,
        "owned_programs": len(PROGRAMS),
        "owned_artifact_trials": len(trials),
        "behavior_by_program": [
            {
                "program": p,
                "n": sum(r["program"] == p for r in trials),
                "passed": sum(r["passed"] for r in trials if r["program"] == p),
            }
            for p in PROGRAMS
        ],
        "static_parents": 60,
        "static_cases": len(static),
        "test_parent_count": 20,
        "metrics": {
            cohort: {
                method: summarize(
                    [
                        r
                        for r in predictions
                        if r["method"] == method
                        and ((r["cohort"] == "static" and r["split"] == cohort) or r["cohort"] == cohort)
                    ]
                )
                for method in METHODS
            }
            for cohort in ["development", "test", "behavior"]
        },
        "scope": "Constructed mechanical faults and owned behavioral implementations; not natural-Skill semantic accuracy",
        "human_semantic_gold": 0,
        "learned_neural_model": False,
        "split": "Synthetic parent-disjoint development/test; fixed rules, no threshold fitting",
        "truth_reference": "CLI reference from generator specs independently of AST; constructive artifact constraints",
    }
    for name, data in [
        ("predictions.jsonl", predictions),
        ("receipts.jsonl", receipts),
        ("owned-trials.jsonl", trials),
        ("behavior-reports.jsonl", behavior_reports),
    ]:
        write_once(output / name, data, jsonl=True)
    write_once(output / "summary.json", summary)
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return summary


def replay(run_path: Path) -> dict:
    verify_files(run_path, json.loads((run_path / "manifest.json").read_text(encoding="utf-8")))
    for record in read_jsonl(run_path / "behavior-reports.jsonl"):
        report = record["report"]
        assert report["decision"] == (
            "tested_pass_within_scope" if record["program"].endswith("_correct") else "repair_required"
        )
    return json.loads((run_path / "summary.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=["trusted_process", "docker"], default="trusted_process")
    args = parser.parse_args()
    summary = run(args.output, backend=args.backend)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
