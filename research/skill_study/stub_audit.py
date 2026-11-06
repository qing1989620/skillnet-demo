"""Post-hoc D1 exploration of explicit constant-success placeholder methods."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from collections import Counter
from pathlib import Path

from research.skill_quality.manifest import freeze_files, write_once

from .package_audit import load_d1


def run(root: Path, frozen: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Use a new exploratory run ID")
    packages = load_d1(root, frozen)
    findings = []
    for package in packages:
        for path, text in package.texts.items():
            if not path.endswith(".py"):
                continue
            try:
                tree = ast.parse(text, filename=path)
            except (SyntaxError, ValueError, RecursionError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != "_execute":
                    continue
                body = [
                    s
                    for s in node.body
                    if not (
                        isinstance(s, ast.Expr)
                        and isinstance(s.value, ast.Constant)
                        and isinstance(s.value.value, str)
                    )
                ]
                if len(body) != 1 or not isinstance(body[0], ast.Return):
                    continue
                if body[0].value is None:
                    continue
                try:
                    value = ast.literal_eval(body[0].value)
                except (ValueError, TypeError):
                    continue
                if not isinstance(value, dict) or value.get("success") is not True:
                    continue
                lines = text.splitlines()
                start, end = node.lineno, node.end_lineno
                excerpt = "\n".join(lines[start - 1 : end])
                if not any(
                    word in excerpt.lower() for word in ("implementation here", "placeholder", "todo")
                ):
                    continue
                findings.append(
                    {
                        "skill_uid": package.snapshot.skill_uid,
                        "name": package.snapshot.name,
                        "source_repo": package.snapshot.source_repo,
                        "source_commit": package.snapshot.source_commit,
                        "path": path,
                        "sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "start_line": start,
                        "end_line": end,
                        "quote": excerpt,
                        "finding": "explicit_placeholder_execute_method_returns_literal_success",
                        "status": "static_structure_confirmed_runtime_and_whole_skill_impact_not_tested",
                    }
                )
    summary = {
        "experiment": "posthoc_D1_constant_success_placeholder_exploration",
        "posthoc": True,
        "parents_inspected": len(packages),
        "d2_used": 0,
        "methods_flagged": len(findings),
        "parent_skills_flagged": len({r["skill_uid"] for r in findings}),
        "source_counts_by_method": dict(Counter(r["source_repo"] for r in findings)),
        "api_calls": 0,
        "community_code_executed": False,
        "interpretation": "literal placeholder methods, not proof all enclosing skills fail or are malicious",
    }
    output.mkdir(parents=True, exist_ok=False)
    write_once(output / "findings.jsonl", findings, jsonl=True)
    write_once(output / "summary.json", summary)
    write_once(output / "code-manifest.json", freeze_files(root, [Path(__file__)]))
    write_once(output / "manifest.json", freeze_files(output, output.iterdir()))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run(Path.cwd(), Path("out/research/skill-quality/20261104-phase-a-v3"), args.output), indent=2
        )
    )
