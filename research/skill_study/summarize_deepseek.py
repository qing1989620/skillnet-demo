"""Describe all direct-API pilot responses without turning locator checks into human gold."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from research.skill_quality.manifest import file_sha, read_jsonl, verify_files

from .deepseek_pilot import Assessment


def summarize(run: Path) -> dict:
    verify_files(run, json.loads((run / "manifest.json").read_text(encoding="utf-8")))
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    rows = read_jsonl(run / "observations.jsonl") if (run / "observations.jsonl").exists() else []
    requests = read_jsonl(run / "adapted-requests.private.jsonl")
    by_request = {r["run_id"]: r for r in requests}
    groups = defaultdict(list)
    diagnostics, repairs = [], []
    for index, row in enumerate(rows):
        groups[row["arm"]].append(row)
        raw = json.loads((run / f"response-{index:03}.private.json").read_text(encoding="utf-8"))
        if not row["schema_valid"]:
            try:
                Assessment.model_validate_json(raw["choices"][0]["message"]["content"])
            except ValidationError as error:
                diagnostics.append(
                    {
                        "run_id": row["run_id"],
                        "arm": row["arm"],
                        "issues": [{k: e[k] for k in ("loc", "type", "msg")} for e in error.errors()],
                    }
                )
        if row["assessment"]:
            material = json.loads(
                by_request[row["run_id"].removesuffix("-direct-v1")]["messages"][1]["content"]
            )
            docs = {d["path"]: d for d in material["included_documents"]}
            for dimension in row["assessment"]["dimensions"]:
                for citation in dimension["citations"]:
                    doc = docs.get(citation["path"])
                    if doc is None:
                        continue
                    lines = {r["line"]: r["text"] for r in doc["numbered_lines"]}
                    low, high = citation["start_line"], citation["end_line"]
                    if (
                        high < low
                        or high - low > len(lines)
                        or any(i not in lines for i in range(low, high + 1))
                    ):
                        continue
                    source = "\n".join(lines[i] for i in range(low, high + 1))
                    quote = citation["exact_quote"]
                    repairs.append(
                        {
                            "arm": row["arm"],
                            "sha_matches": citation["sha256"] == doc["sha256"],
                            "exact_quote_matches": quote == source and bool(quote.strip()),
                            "nonempty_quote_is_substring": bool(quote.strip()) and quote in source,
                            "kind": "posthoc_format_diagnostic_not_semantic_entailment",
                        }
                    )
    results = []
    for arm in ("rubric_only", "evidence_first", "counterevidence_first"):
        items = groups[arm]
        checks = [c for r in items for c in r["citation_checks"]]
        dims = [d for r in items if r["assessment"] for d in r["assessment"]["dimensions"]]
        parent_cites = [r for r in items if r["schema_valid"] and r["citation_checks"]]
        results.append(
            {
                "arm": arm,
                "requests": len(items),
                "schema_valid": sum(r["schema_valid"] for r in items),
                "dimensions_in_valid_responses": len(dims),
                "unknown_dimensions": sum(d["state"] == "unknown" for d in dims),
                "not_applicable_dimensions": sum(d["state"] == "not_applicable" for d in dims),
                "model_marked_conflict_dimensions": sum(d["state"] == "conflict" for d in dims),
                "citations_from_schema_valid_responses": len(checks),
                "exact_valid_locators": sum(c["valid_locator"] for c in checks),
                "locator_valid_fraction": sum(c["valid_locator"] for c in checks) / len(checks)
                if checks
                else None,
                "parents_with_citations": len(parent_cites),
                "parents_all_emitted_citations_valid": sum(
                    all(c["valid_locator"] for c in r["citation_checks"]) for r in parent_cites
                ),
                "invalid_reasons": dict(
                    Counter(c["invalid_reason"] for c in checks if not c["valid_locator"])
                ),
            }
        )
    account_delta = None
    before, after = run / "balance-before.private.json", run / "balance-after.private.json"
    if before.exists() and after.exists():
        first = {
            r["currency"]: r["total_balance"]
            for r in json.loads(before.read_text(encoding="utf-8"))["balance_infos"]
        }
        last = {
            r["currency"]: r["total_balance"]
            for r in json.loads(after.read_text(encoding="utf-8"))["balance_infos"]
        }
        account_delta = {c: str(Decimal(first[c]) - Decimal(last[c])) for c in first.keys() & last.keys()}
    report = {
        "run_id": run.name,
        "source_summary_sha256": file_sha(run / "summary.json"),
        "model_requests_attempted": summary["model_requests_attempted"],
        "model_requests_completed": summary["model_requests_completed"],
        "complete": summary["complete"],
        "served_model_values": summary["served_model_values"],
        "parent_skills": len({r["skill_uid"] for r in rows}),
        "groups": results,
        "schema_failures": diagnostics,
        "prompt_tokens": summary["prompt_tokens"],
        "completion_tokens": summary["completion_tokens"],
        "tariff_upper_from_observed_usage": summary["tariff_upper_from_observed_usage"],
        "observed_account_balance_decrease": account_delta,
        "balance_decrease_is_not_attributed_as_batch_invoice": True,
        "posthoc_format_diagnostic": {
            "citations_with_supplied_path_and_line_range": len(repairs),
            "hash_and_exact_quote_valid": sum(r["sha_matches"] and r["exact_quote_matches"] for r in repairs),
            "exact_quote_valid_if_system_binds_registered_hash": sum(
                r["exact_quote_matches"] for r in repairs
            ),
            "substring_quote_valid_if_system_binds_hash": sum(
                r["nonempty_quote_is_substring"] for r in repairs
            ),
            "not_a_new_model_run_or_semantic_validation": True,
        },
        "human_quality_gold": 0,
        "skill_execution_trials": 0,
        "limitations": summary["limitations"],
    }
    destination = Path(__file__).with_name("results") / "deepseek-readiness-analysis.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    report = summarize(args.run)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "model_requests_completed",
                    "groups",
                    "posthoc_format_diagnostic",
                    "tariff_upper_from_observed_usage",
                    "observed_account_balance_decrease",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
