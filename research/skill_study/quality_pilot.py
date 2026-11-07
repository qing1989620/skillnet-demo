"""D1-only package audit and controlled CLI interventions; not human gold."""

from __future__ import annotations

import argparse
import json
import shlex
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from research.skill_quality.manifest import digest, file_sha, freeze_files, write_once

from .cli_contracts import ParserContract, check_command, parse_contract, standard_library_reference
from .package_audit import audit_package, load_d1


def variants(command: str, contract: ParserContract) -> list[tuple[str, str, bool]]:
    tokens = shlex.split(command, comments=True)
    found, index = [], 2
    while index < len(tokens):
        start = index
        name, equal, attached = tokens[index].partition("=")
        option = contract.by_name[name]
        if option.takes_value:
            value = attached if equal else tokens[index + 1]
            index += 1 if equal else 2
        else:
            value = None
            index += 1
        found.append((start, index, name, option, value))
    result = [
        ("original", command, False),
        ("equivalent_whitespace", "  " + shlex.join(tokens) + "   ", False),
    ]
    unknown_name = "--skillstudy-undeclared-20261106"
    while unknown_name in contract.by_name:
        unknown_name += "x"
    result.append(("invented_option", shlex.join(tokens + [unknown_name]), True))
    value_options = [item for item in found if item[3].takes_value]
    if value_options:
        start, stop, name, _, value = value_options[0]
        assert value is not None
        result.append(
            (
                "equivalent_equals_syntax",
                shlex.join(tokens[:start] + [name + "=" + value] + tokens[stop:]),
                False,
            )
        )
    required = [item for item in found if item[3].required]
    if required:
        target = required[0][3]
        removed = list(tokens)
        for start, stop, _, option, _ in reversed(found):
            if option.names == target.names:
                del removed[start:stop]
        result.append(("missing_required_option", shlex.join(removed), True))
    choices = [item for item in value_options if item[3].choices]
    if choices:
        start, stop, name, option, _ = choices[0]
        assert option.choices is not None
        bad = "__skillstudy_invalid_choice__" if option.value_type == "str" else "987654321"
        convert = {"str": str, "int": int, "float": float}[option.value_type]
        while convert(bad) in option.choices:
            bad = bad + "x" if option.value_type == "str" else str(int(bad) + 1)
        result.append(
            ("invalid_literal_choice", shlex.join(tokens[:start] + [name, bad] + tokens[stop:]), True)
        )
    typed = [item for item in value_options if item[3].value_type in {"int", "float"}]
    if typed:
        start, stop, name, *_ = typed[0]
        result.append(
            (
                "invalid_literal_type",
                shlex.join(tokens[:start] + [name, "not-a-number"] + tokens[stop:]),
                True,
            )
        )
    return result


def paired_parent_interval(rows: list[dict[str, Any]], *, seed: int, n_boot: int = 10_000) -> dict[str, Any]:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row["known_injected_defect"]:
            groups[row["parent_skill_uid"]].append(
                float(row["extended"]["status"] == "inconsistent_static")
                - float(row["flags_only"]["status"] == "inconsistent_static")
            )
    means = np.array([np.mean(groups[k]) for k in sorted(groups)])
    if len(means) < 2:
        return {"parents": len(means), "interval": None, "reason": "insufficient_parents"}
    rng = np.random.default_rng(seed)
    bootstrap = means[rng.integers(0, len(means), size=(n_boot, len(means)))].mean(axis=1)
    return {
        "parents": len(means),
        "parent_macro_detection_delta": float(means.mean()),
        "conditional_parent_bootstrap_95_interval": np.quantile(bootstrap, [0.025, 0.975]).tolist(),
        "scope": "selected_D1_parents_and_constructed_defects_not_open_ecosystem_accuracy",
    }


def run(root: Path, frozen: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("Preserve old runs; choose a new ID")
    plan_path = Path(__file__).with_name("experiment_plan.json")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    packages = load_d1(root, frozen)
    audits, cases = [], []
    source_hashes: list[dict[str, Any]] = []
    reference_disagreements = []
    for package in packages:
        audit, observations = audit_package(package)
        audits.append(audit)
        source_hashes.extend(
            {"skill_uid": package.snapshot.skill_uid, "path": path, "sha256": sha, "bytes": size}
            for path, (sha, size) in package.inventory.items()
        )
        eligible = []
        for observation in observations:
            if observation["result"]["status"] != "consistent_static":
                continue
            spec = parse_contract(package.texts[observation["resolved_script"]])
            reference = standard_library_reference(spec, observation["command"])
            if reference != "consistent_static":
                reference_disagreements.append(
                    {"parent": package.snapshot.skill_uid, "observation": observation, "reference": reference}
                )
                continue
            eligible.append((digest([package.snapshot.skill_uid, observation]), observation, spec))
        for _, observation, spec in sorted(eligible, key=lambda item: item[0])[:3]:
            for kind, command, bad in variants(observation["command"], spec):
                reference = standard_library_reference(spec, command)
                expected = "inconsistent_static" if bad else "consistent_static"
                row = {
                    "parent_skill_uid": package.snapshot.skill_uid,
                    "parent_name": package.snapshot.name,
                    "source_repo": package.snapshot.source_repo,
                    "document": observation["document"],
                    "source_script": observation["resolved_script"],
                    "original_command_line": observation["start_line"],
                    "original_document_sha256": package.inventory[observation["document"]][0],
                    "source_script_sha256": package.inventory[observation["resolved_script"]][0],
                    "variant_kind": kind,
                    "command": command,
                    "known_injected_defect": bad,
                    "reference_argparse": reference,
                    "reference_matches_constructed_expectation": reference == expected,
                    "flags_only": check_command(spec, command, values=False),
                    "extended": check_command(spec, command),
                    "provenance": "in_memory_controlled_edit_not_upstream_Skill_result",
                }
                row["case_id"] = digest(row)
                cases.append(row)
    by_kind = {}
    for kind in sorted({r["variant_kind"] for r in cases}):
        subset = [r for r in cases if r["variant_kind"] == kind]
        by_kind[kind] = {
            "cases": len(subset),
            "parents": len({r["parent_skill_uid"] for r in subset}),
            "known_defect": subset[0]["known_injected_defect"],
        }
        for method in ("flags_only", "extended"):
            by_kind[kind][method] = dict(Counter(r[method]["status"] for r in subset))
        by_kind[kind]["standard_library_reference"] = dict(Counter(r["reference_argparse"] for r in subset))
    observation_statuses = Counter(o["result"]["status"] for a in audits for o in a["command_observations"])
    missing_parents = [a for a in audits if a["unresolved_resource_mentions"]]
    summary = {
        "experiment": "D1_mechanical_contract_audit_and_interventions_v1",
        "plan_sha256": file_sha(plan_path),
        "parents_audited": len(packages),
        "d2_used": 0,
        "source_repositories": dict(Counter(p.snapshot.source_repo for p in packages)),
        "files_rehashed": sum(len(p.inventory) for p in packages),
        "python_files": sum(path.endswith(".py") for p in packages for path in p.texts),
        "opaque_files": sum(len(p.opaque) for p in packages),
        "command_observations": sum(observation_statuses.values()),
        "command_statuses": dict(observation_statuses),
        "parents_with_eligible_commands": len({r["parent_skill_uid"] for r in cases}),
        "parents_with_unresolved_resource_mentions": len(missing_parents),
        "unresolved_resource_mentions": sum(len(a["unresolved_resource_mentions"]) for a in audits),
        "distinct_unresolved_parent_targets": sum(
            len({r["target"] for r in a["unresolved_resource_mentions"]}) for a in audits
        ),
        "controlled_cases": len(cases),
        "by_variant": by_kind,
        "base_static_reference_disagreements": len(reference_disagreements),
        "variant_reference_mismatches": sum(
            not r["reference_matches_constructed_expectation"] for r in cases
        ),
        "extended_reference_disagreements": sum(
            r["extended"]["status"] != r["reference_argparse"] for r in cases
        ),
        "paired_parent_analysis": paired_parent_interval(cases, seed=plan["seed"]),
        "human_gold_items": 0,
        "skill_execution_trials": 0,
        "api_calls": 0,
        "limitations": [
            "only supported literal CLI contracts; unknown is not good or bad",
            "resource mentions include examples and optional links; not confirmed defects",
            "edit labels are mechanical ground truth, not semantic quality labels",
            "standard argparse is a strong independent baseline; matching it is not novel superiority",
            "two source repositories and D1-only development; no confirmatory generalization claim",
        ],
        "inputs": {
            "snapshots_sha256": file_sha(frozen / "snapshots/skills.jsonl"),
            "dataset_manifest_sha256": file_sha(frozen / "dataset_manifest.json"),
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    write_once(output / "audits.jsonl", audits, jsonl=True)
    write_once(output / "controlled-cases.jsonl", cases, jsonl=True)
    write_once(output / "resource-fingerprints.jsonl", source_hashes, jsonl=True)
    write_once(output / "base-reference-disagreements.json", reference_disagreements)
    write_once(output / "summary.json", summary)
    code_paths = [
        Path(__file__).with_name(name)
        for name in (
            "__init__.py",
            "cli_contracts.py",
            "package_audit.py",
            "quality_pilot.py",
            "experiment_plan.json",
        )
    ]
    snapshot_dir = output / "code-snapshot"
    snapshot_dir.mkdir()
    for path in code_paths:
        (snapshot_dir / path.name).write_bytes(path.read_bytes())
    write_once(output / "code-manifest.json", freeze_files(root, code_paths))
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen", type=Path, default=Path("out/research/skill-quality/20261104-phase-a-v3"))
    args = parser.parse_args()
    print(json.dumps(run(Path.cwd(), args.frozen, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
