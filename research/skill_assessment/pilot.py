"""Replay D1 cases into a new immutable run directory; no network/model calls."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from research.skill_quality.manifest import file_sha, freeze_files, read_jsonl, write_once
from research.skill_quality.schemas import SkillSnapshot

from .cases import PILOT_NAMES, build_case
from .evidence import Bundle, Citation, load_bundle
from .verifier import CSV_INPUT, mutation_diagnostics, reference_fixture, task_spec


def verify_embedded_citations(bundle: Bundle, value: Any) -> int:
    count = 0
    if isinstance(value, dict):
        if set(value) == {"path", "sha256", "start_line", "end_line", "quote"}:
            bundle.verify(Citation(**value))
            return 1
        for child in value.values():
            count += verify_embedded_citations(bundle, child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            count += verify_embedded_citations(bundle, child)
    return count


def run(root: Path, frozen: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("Run outputs are write-once: choose a new run-id")
    dataset_path = frozen / "dataset_manifest.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    d1, d2 = set(dataset["sample_ids"]["D1"]), set(dataset["sample_ids"]["D2"])
    # The frozen JSONL includes all items; only the selected D1 records are
    # passed to the package reader, inspectors, boundary cases or output writer.
    snapshots = {
        row["name"]: row
        for row in read_jsonl(frozen / "snapshots/skills.jsonl")
        if row["name"] in PILOT_NAMES
    }
    baseline = {r["name"]: r for r in read_jsonl(frozen / "baseline.jsonl") if r["name"] in PILOT_NAMES}
    if set(snapshots) != set(PILOT_NAMES) or set(baseline) != set(PILOT_NAMES):
        raise ValueError("Pilot cases missing from frozen input")
    cases, citation_count = [], 0
    for name in PILOT_NAMES:
        snapshot = SkillSnapshot.model_validate(snapshots[name])
        if snapshot.skill_uid not in d1 or snapshot.skill_uid in d2:
            raise ValueError("Case is not an exclusive D1 development item")
        bundle = load_bundle(root, snapshot)
        case = build_case(bundle, baseline[name])
        citation_count += verify_embedded_citations(bundle, case)
        cases.append(case)
    diagnostics = mutation_diagnostics()
    if not all(d["diagnostic_pass"] for d in diagnostics):
        raise AssertionError("Verifier mutation diagnostics failed")
    # Every read/review above completes before the immutable output is created.
    output.mkdir(parents=True, exist_ok=False)
    write_once(output / "cases.json", cases)
    write_once(output / "verifier-diagnostics.json", diagnostics)
    write_once(output / "task.json", task_spec())
    write_once(output / "reference-fixture-not-agent-output.json", reference_fixture())
    for rater in ("A", "B"):
        write_once(
            output / ("blind-review-template-" + rater + ".json"),
            {
                "rater_slot": rater,
                "annotator_id": None,
                "status": "unlabelled",
                "instructions": "Review the full registered package independently using RUBRIC.md; do not open cases.json or historical scores before submission.",
                "items": [
                    {
                        "skill_uid": c["skill_uid"],
                        "name": c["name"],
                        "source_repo": c["source_repo"],
                        "source_commit": c["source_commit"],
                        "package_path": "seed/community/skills/" + c["name"],
                        "registered_files": c["source_files"],
                        "dimensions": {
                            dim: {
                                "score": None,
                                "state": "unassigned",
                                "reason": None,
                                "citations": [],
                                "counterevidence": [],
                            }
                            for dim in c["ordinal_ratings"]
                        },
                        "safety_license_review": None,
                        "independent_boundary_clauses": [],
                    }
                    for c in cases
                ],
            },
        )
    (output / "input.csv").write_text(CSV_INPUT, encoding="utf-8", newline="\n")
    statuses = Counter(s["result"]["status"] for c in cases for s in c["preflight_scenarios"])
    summary = {
        "pilot_kind": "D1_purposive_static_case_study_not_population_accuracy",
        "cases": len(cases),
        "d2_cases_used_for_development": 0,
        "source_files_rehashed": sum(len(c["source_files"]) for c in cases),
        "citation_occurrences_verified": citation_count,
        "citation_check_scope": "source_coordinates_and_hash_not_semantic_entailment",
        "cli_examples_inspected": sum(len(c["static_checks"]["cli_checks"]) for c in cases),
        "cli_examples_with_review_leads": sum(
            x["status"] == "review_required" for c in cases for x in c["static_checks"]["cli_checks"]
        ),
        "literal_measurement_defaults": sum(len(c["static_checks"]["default_measurements"]) for c in cases),
        "unresolved_resource_mentions": sum(len(c["static_checks"]["missing_resources"]) for c in cases),
        "preflight_scenarios": sum(statuses.values()),
        "preflight_status_counts": dict(statuses),
        "verifier_constructed_cases": len(diagnostics),
        "verifier_diagnostic_passes": sum(d["diagnostic_pass"] for d in diagnostics),
        "human_gold_items": 0,
        "independent_ordinal_labels": 0,
        "skill_execution_trials": 0,
        "paired_utility_trials": 0,
        "model_api_calls": 0,
        "research_api_spend": 0,
        "general_quality_accuracy": None,
        "general_safety_accuracy": None,
        "stage_two_network_optimization": "deferred",
        "frozen_inputs": {
            "dataset_manifest_sha256": file_sha(dataset_path),
            "snapshots_sha256": file_sha(frozen / "snapshots/skills.jsonl"),
            "baseline_sha256": file_sha(frozen / "baseline.jsonl"),
            "prior_research_code_manifest_sha256": file_sha(frozen / "research_code_manifest.json"),
        },
        "findings_are_agent_review_not_gold": True,
    }
    write_once(output / "summary.json", summary)
    code_paths = [p for p in Path(__file__).parent.rglob("*") if p.suffix in {".py", ".md", ".json"}]
    code_paths.append(root / ".github/workflows/research-assessment.yml")
    write_once(output / "code-manifest.json", freeze_files(root, code_paths))
    write_once(output / "artifact-manifest.json", freeze_files(output, output.iterdir()))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--frozen-run", type=Path, default=Path("out/research/skill-quality/20261104-phase-a-v3")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    frozen = args.frozen_run if args.frozen_run.is_absolute() else root / args.frozen_run
    output = args.output if args.output.is_absolute() else root / args.output
    print(json.dumps(run(root, frozen, output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
