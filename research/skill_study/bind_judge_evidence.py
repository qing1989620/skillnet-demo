"""Post-hoc source binding: verify registered windows, preserve model quote discrepancies."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from research.skill_quality.manifest import file_sha, freeze_files, read_jsonl, safe_read, write_once

from .deepseek_pilot import Citation
from .package_audit import load_d1


def bind_registered(
    root: Path,
    package_prefix: str,
    inventory: dict[str, tuple[str, int]],
    citation: Citation,
    supplied: set[str],
) -> dict:
    common = {"semantic_support": "not_assessed", "runtime_ability": "not_assessed"}
    expected = inventory.get(citation.path)
    if expected is None:
        return {**common, "status": "unregistered_path"}
    if citation.sha256 != expected[0]:
        return {**common, "status": "claimed_version_conflict"}
    if citation.end_line < citation.start_line or citation.end_line - citation.start_line >= 50:
        return {**common, "status": "unbounded_or_reversed_window"}
    raw = safe_read(root, package_prefix + "/" + citation.path)
    if len(raw) != expected[1] or hashlib.sha256(raw).hexdigest() != expected[0]:
        return {**common, "status": "registered_resource_changed"}
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return {**common, "status": "opaque_resource"}
    if citation.end_line > len(lines):
        return {**common, "status": "line_out_of_range"}
    quote = "\n".join(lines[citation.start_line - 1 : citation.end_line])
    return {
        **common,
        "status": "source_window_bound",
        "origin": "supplied_numbered_document"
        if citation.path in supplied
        else "additional_registered_resource_fetch",
        "source_sha256": expected[0],
        "server_extracted_quote": quote,
        "model_quote_exact": citation.exact_quote == quote,
        "model_quote_preserved": citation.exact_quote,
        "binding_does_not_repair_or_validate_model_judgment": True,
    }


def run(source: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Use a new binding run ID")
    frozen = Path("out/research/skill-quality/20261104-phase-a-v3")
    packages = {p.snapshot.skill_uid: p for p in load_d1(Path.cwd(), frozen)}
    requests = {r["run_id"]: r for r in read_jsonl(source / "adapted-requests.private.jsonl")}
    bound = []
    for row in read_jsonl(source / "observations.jsonl"):
        if row["assessment"] is None:
            continue
        package = packages[row["skill_uid"]]
        request = requests[row["run_id"].removesuffix("-direct-v1")]
        material = json.loads(request["messages"][1]["content"])
        supplied = {d["path"] for d in material["included_documents"]}
        for dimension in row["assessment"]["dimensions"]:
            for data in dimension["citations"]:
                citation = Citation.model_validate(data)
                result = bind_registered(
                    Path.cwd(),
                    "seed/community/skills/" + package.snapshot.name,
                    package.inventory,
                    citation,
                    supplied,
                )
                bound.append(
                    {
                        "run_id": row["run_id"],
                        "skill_uid": row["skill_uid"],
                        "arm": row["arm"],
                        "dimension": dimension["dimension"],
                        "citation": data,
                        **result,
                    }
                )
    counts = Counter(r["status"] for r in bound)
    summary = {
        "experiment": "posthoc_registered_source_binding_not_new_model_trial",
        "source_run": source.name,
        "source_observations_sha256": file_sha(source / "observations.jsonl"),
        "citations": len(bound),
        "binding_status": dict(counts),
        "origins": dict(Counter(r.get("origin", "unbound") for r in bound)),
        "model_quote_discrepancies_preserved": sum(r.get("model_quote_exact") is False for r in bound),
        "additional_resources_fetched": len(
            {
                (r["skill_uid"], r["citation"]["path"])
                for r in bound
                if r.get("origin") == "additional_registered_resource_fetch"
            }
        ),
        "semantic_support_claims_verified": 0,
        "new_api_calls": 0,
        "skills_executed": 0,
        "limitations": [
            "posthoc engineering diagnostic, not a pre-registered method-effect result",
            "retrieving a matching source window does not prove it supports the score or capability",
            "additional resources were system-fetched after prediction, not seen as numbered evidence by the model",
            "original strict locator failures and model quotes are retained, not relabeled as correct",
        ],
    }
    output.mkdir(parents=True)
    write_once(output / "bindings.private.jsonl", bound, jsonl=True)
    write_once(output / "summary.json", summary)
    paths = [Path(__file__), Path(__file__).with_name("package_audit.py")]
    write_once(output / "code-manifest.json", freeze_files(Path.cwd(), paths))
    write_once(output / "manifest.json", freeze_files(output, output.iterdir()))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output), ensure_ascii=False, indent=2))
