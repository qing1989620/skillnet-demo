"""Targeted original community CLI execution and minimal repairs, Docker only."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
from fractions import Fraction
from pathlib import Path

from research.skill_network.sources import source_records
from research.skill_quality.manifest import digest, file_sha, freeze_files, write_once

DQA = "gh-claude-data-quality-auditor-9d8e63"
STUBS = {
    "gh-claude-senior-data-scientist-3337e5": [
        "experiment_designer",
        "feature_engineering_pipeline",
        "model_evaluation_suite",
    ],
    "gh-claude-senior-ml-engineer-9b50c5": [
        "ml_monitoring_suite",
        "model_deployment_pipeline",
        "rag_system_builder",
    ],
}
NULLS = {"", "null", "none", "n/a", "na", "nan", "nil"}


def fixtures(source: Path) -> list[dict]:
    output = []
    for name in ["iris", "wine", "wdbc", "banknote"]:
        records = source_records(source, name)
        for size in [1, 8, 48]:
            for condition in ["plain", "quoted", "literal_na", "whitespace"]:
                rows = [
                    [f"row-{i}", r["score"], "train" if i % 2 else "test", "ordinary"]
                    for i, r in enumerate(records[:size])
                ]
                if condition == "quoted":
                    rows[0][3] = "quoted, text\nsecond line"
                elif condition == "literal_na":
                    rows[0][1] = "NA"
                elif condition == "whitespace":
                    rows[0][1] = "  "
                output.append(
                    {
                        "id": f"{name}-n{size}-{condition}",
                        "dataset": name,
                        "condition": condition,
                        "rows": rows,
                    }
                )
    output.append(
        {
            "id": "targeted-iqr-threshold",
            "dataset": "explicit_regression",
            "condition": "threshold",
            "rows": [
                [f"row-{i}", str(v), "train", "ordinary"] for i, v in enumerate([0, 1, 2, 3, 4, 5, 6, 14])
            ],
        }
    )
    return output


def prepare(root: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Immutable community runtime batch")
    bundle = output / "bundle"
    bundle.mkdir(parents=True)
    registry = json.loads((root / "seed/community/packages.json").read_text(encoding="utf-8"))
    entries = []
    for skill, names in {
        DQA: ["data_profiler", "missing_value_analyzer", "outlier_detector"],
        **STUBS,
    }.items():
        package = registry[skill]
        for name in names:
            rel = "scripts/" + name + ".py"
            source = root / package["package_path"] / rel
            expected = next(r for r in package["files"] if r["path"] == rel)
            assert file_sha(source) == expected["sha256"]
            dest = bundle / "scripts" / (name + ".py")
            dest.parent.mkdir(exist_ok=True)
            dest.write_bytes(source.read_bytes())
            entries.append(
                {
                    "skill": skill,
                    "script": rel,
                    "commit": package["commit"],
                    "file": dest.name,
                    "source_sha256": file_sha(dest),
                    "variant": "original",
                }
            )
    repairs = {
        "data_profiler": (
            'profile["std"] = round(safe_std(nums, mean), 4) if mean is not None else None',
            'profile["std"] = round(safe_std(nums, mean), 4) if len(nums) >= 2 and mean is not None else None',
        ),
        "outlier_detector": ("multiplier=threshold if threshold != 3.0 else 1.5", "multiplier=threshold"),
    }
    for name, (old, new) in repairs.items():
        original = bundle / "scripts" / (name + ".py")
        code = original.read_text(encoding="utf-8")
        assert code.count(old) == 1
        dest = bundle / "scripts" / (name + "_repaired.py")
        dest.write_text(code.replace(old, new), encoding="utf-8", newline="\n")
        entries.append(
            {
                "skill": DQA,
                "script": "scripts/" + name + ".py",
                "file": dest.name,
                "source_sha256": file_sha(dest),
                "variant": "minimal_repair",
                "parent_sha256": file_sha(original),
                "old": old,
                "new": new,
            }
        )
    cases = fixtures(root / "research/skill_network/results/sources-v2")
    requests = []
    for case in cases:
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["id", "value", "group", "note"])
        writer.writerows(case["rows"])
        filename = case["id"] + ".csv"
        (bundle / filename).write_text(stream.getvalue(), encoding="utf-8", newline="\n")
        for name in [
            "data_profiler",
            "data_profiler_repaired",
            "missing_value_analyzer",
            "outlier_detector",
            "outlier_detector_repaired",
        ]:
            thresholds = [1.5, 3.0] if name.startswith("outlier") else [None]
            for threshold in thresholds:
                args = ["--file", "/work/" + filename, "--format", "json"]
                if threshold is not None:
                    args += ["--columns", "value", "--method", "iqr", "--threshold", str(threshold)]
                requests.append(
                    {
                        "id": digest([case["id"], name, threshold]),
                        "case_id": case["id"],
                        "script": name + ".py",
                        "args": args,
                        "threshold": threshold,
                        "kind": "csv",
                    }
                )
    for names in STUBS.values():
        for name in names:
            for exists in [True, False]:
                requests.append(
                    {
                        "id": digest([name, exists]),
                        "script": name + ".py",
                        "kind": "artifact_contract",
                        "input_exists": exists,
                        "args": [
                            "--input",
                            "/work/iris-n8-plain.csv" if exists else "/work/absent.csv",
                            "--output",
                            "/tmp/requested-output.json",
                        ],
                    }
                )
    write_once(bundle / "requests.json", requests)
    write_once(output / "fixtures.json", cases)
    write_once(output / "entries.json", entries)
    (bundle / "worker.py").write_bytes(Path(__file__).with_name("community_worker.py").read_bytes())
    write_once(
        output / "protocol.json",
        {
            "date": "2026-11-13",
            "scope": "targeted natural-CLI case study, 3 known D1 packages, not representative blind skill-quality sample",
            "original_scripts": 9,
            "minimal_repaired_variants": 2,
            "csv_inputs": 49,
            "planned_processes": len(requests),
            "source_inspection_precedes_test": True,
            "problems_previously_identified_or_inspected": True,
            "labels": "independent CSV rows/declared null policy/exact IQR arithmetic and explicit output-path existence; not an overall Skill gold label",
            "strict_null_policy": "only empty string; divergence from documented broader null policy is task incompatibility, not an intrinsic defect",
            "repairs": "one-line changes fixed before runtime; no semantic logic imported from verifier",
            "community_code_executed_only_inside": "pinned no-network read-only nonroot Docker with tmpfs /tmp and no API credentials",
        },
    )
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return {"requests": len(requests), "inputs": 49, "original_scripts": 9, "repaired_variants": 2}


def reference(case: dict, threshold: float) -> dict:
    rows = case["rows"]
    broad = {
        col: sum(r[i].strip().lower() in NULLS for r in rows)
        for i, col in enumerate(["id", "value", "group", "note"])
    }
    strict = {col: sum(r[i] == "" for r in rows) for i, col in enumerate(["id", "value", "group", "note"])}
    nums = sorted(Fraction(r[1]) for r in rows if r[1].strip().lower() not in NULLS)
    if len(nums) < 4:
        outlier = None
    else:

        def quartile(k):
            pos = Fraction((len(nums) - 1) * k, 4)
            lo = pos.numerator // pos.denominator
            hi = min(lo + 1, len(nums) - 1)
            return nums[lo] + (pos - lo) * (nums[hi] - nums[lo])

        q1, q3 = quartile(1), quartile(3)
        delta = Fraction(str(threshold)) * (q3 - q1)
        outlier = sum(n < q1 - delta or n > q3 + delta for n in nums)
    return {"rows": len(rows), "broad_nulls": broad, "strict_nulls": strict, "outlier_count": outlier}


def analyze(output: Path) -> dict:
    cases = {r["id"]: r for r in json.loads((output / "fixtures.json").read_text(encoding="utf-8"))}
    rows = json.loads((output / "outcomes.json").read_text(encoding="utf-8"))
    verdicts = []
    for row in rows:
        passed = False
        strict = None
        try:
            if row["kind"] == "artifact_contract":
                passed = (
                    (row["returncode"] == 0 and row["output_exists"])
                    if row["input_exists"]
                    else row["returncode"] != 0
                )
            else:
                expected = reference(cases[row["case_id"]], row["threshold"] or 1.5)
                actual = json.loads(row["stdout"])
                if row["script"].startswith("outlier"):
                    passed = (
                        row["returncode"] == 0
                        and len(actual) == 1
                        and (
                            ("Skipped" in actual[0].get("status", "") and expected["outlier_count"] is None)
                            or actual[0].get("outlier_count") == expected["outlier_count"]
                            and expected["outlier_count"] is not None
                        )
                    )
                else:
                    observed = {c["column"]: c["null_count"] for c in actual["columns"]}
                    passed = (
                        row["returncode"] == 0
                        and actual["total_rows"] == expected["rows"]
                        and observed == expected["broad_nulls"]
                    )
                    strict = (
                        row["returncode"] == 0
                        and actual["total_rows"] == expected["rows"]
                        and observed == expected["strict_nulls"]
                    )
        except (ValueError, TypeError, KeyError, IndexError):
            passed = False
        verdicts.append(
            {
                "id": row["id"],
                "case_id": row.get("case_id"),
                "script": row["script"],
                "threshold": row.get("threshold"),
                "passed": passed,
                "strict_null_task_passed": strict,
                "returncode": row["returncode"],
                "output_exists": row.get("output_exists"),
            }
        )
    groups = []
    for script, threshold in sorted({(r["script"], r.get("threshold") or 0) for r in verdicts}):
        selected = [r for r in verdicts if r["script"] == script and (r["threshold"] or 0) == threshold]
        groups.append(
            {
                "script": script,
                "threshold": threshold,
                "n": len(selected),
                "passed": sum(r["passed"] for r in selected),
                "strict_null_task_passed": sum(r["strict_null_task_passed"] is True for r in selected),
                "nonzero_exit": sum(r["returncode"] != 0 for r in selected),
            }
        )
    summary = {
        "processes": len(rows),
        "groups": groups,
        "api_calls": 0,
        "gold_scope": "targeted CLI/output contracts only",
    }
    write_once(output / "verdicts.json", verdicts)
    write_once(output / "summary.json", summary)
    return summary


def run(root: Path, output: Path) -> dict:
    prepare(root, output)
    bundle = output / "bundle"
    for p in bundle.rglob("*"):
        p.chmod(0o755 if p.is_dir() else 0o644)
    bundle.chmod(0o755)
    image = os.environ["SKILL_COMMUNITY_IMAGE"]
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        "128m",
        "--cpus",
        "1",
        "--pids-limit",
        "32",
        "--user",
        "65534:65534",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",
        "--mount",
        f"type=bind,source={bundle.resolve()},target=/work,readonly",
        image,
        "python",
        "-I",
        "-B",
        "/work/worker.py",
    ]
    proc = subprocess.run(command, capture_output=True, encoding="utf-8", timeout=180)
    assert proc.returncode == 0, proc.stderr[:1000]
    result = json.loads(proc.stdout)
    write_once(output / "outcomes.json", result["outcomes"])
    write_once(output / "boundary.json", {**result["boundary"], "image": image})
    summary = analyze(output)
    write_once(output / "final-manifest.json", freeze_files(output, output.rglob("*")))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(Path.cwd(), args.output), ensure_ascii=False, indent=2))
