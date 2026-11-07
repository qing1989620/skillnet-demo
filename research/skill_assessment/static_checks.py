"""Narrow, inspectable review leads; Python sources are parsed, never imported."""

from __future__ import annotations

import ast
import re
import shlex
from dataclasses import asdict
from pathlib import PurePosixPath
from typing import Any

from .evidence import Bundle, SourceFile


def literal_options(source: SourceFile) -> dict[str, Any]:
    tree = ast.parse(source.text, filename=source.path)
    options: dict[str, dict[str, Any]] = {}
    unresolved = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_argument":
            continue
        names = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if len(names) != len(node.args):
            unresolved += 1
        for name in names:
            if name.startswith("-"):
                item: dict[str, Any] = {"line": node.lineno}
                for keyword in node.keywords:
                    if keyword.arg in {"choices", "required", "default", "action"}:
                        try:
                            item[keyword.arg] = ast.literal_eval(keyword.value)
                        except (ValueError, TypeError):
                            item[keyword.arg] = "not_literal"
                options[name] = item
    return {"options": options, "unresolved_calls": unresolved, "scope": "literal_AST_only_not_runtime"}


def inspect_package(bundle: Bundle) -> dict[str, Any]:
    parsers = {path: literal_options(source) for path, source in bundle.files.items() if path.endswith(".py")}
    cli_checks: list[dict[str, Any]] = []
    missing_resources: list[dict[str, Any]] = []
    default_measurements: list[dict[str, Any]] = []
    self_attestations: list[dict[str, Any]] = []
    for path, source in bundle.files.items():
        if path.endswith(".md"):
            for number, line in enumerate(source.text.splitlines(), 1):
                if re.match(r"\s*risk:\s*safe\s*$", line, re.I):
                    self_attestations.append(
                        {
                            "citation": asdict(bundle.cite(path, number)),
                            "meaning": "author_claim_not_independent_safety_evidence",
                        }
                    )
                for match in re.finditer(
                    r"((?:scripts|references|resources|assets)/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)", line
                ):
                    target = match.group(1)
                    if ":" in target or ".." in PurePosixPath(target).parts:
                        continue
                    local = str(PurePosixPath(path).parent / target)
                    if target not in bundle.files and local not in bundle.files:
                        missing_resources.append(
                            {
                                "target": target,
                                "citation": asdict(bundle.cite(path, number)),
                                "status": "absent_from_registered_package_requires_review",
                            }
                        )
                if not re.match(r"^\s*python(?:3)?\s+", line):
                    continue
                try:
                    tokens = shlex.split(line)
                except ValueError:
                    continue
                target = tokens[1]
                if not target.endswith(".py"):
                    continue
                local = str(PurePosixPath(path).parent / target)
                script = target if target in bundle.files else local
                flags = sorted({t.split("=", 1)[0] for t in tokens[2:] if t.startswith("--")})
                parser = parsers.get(script)
                unsupported = flags if parser is None else [f for f in flags if f not in parser["options"]]
                cli_checks.append(
                    {
                        "citation": asdict(bundle.cite(path, number)),
                        "script": script,
                        "flags": flags,
                        "not_found_flags": unsupported,
                        "status": "review_required"
                        if parser is None or unsupported
                        else "literal_flags_found",
                        "not_proven": "runtime_success_argument_values_and_control_flow",
                    }
                )
        if path.endswith(".py"):
            tree = ast.parse(source.text, filename=path)
            lines = source.text.splitlines()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
                    continue
                if type(node.value.value) not in (int, float):
                    continue
                context = "\n".join(lines[max(0, node.lineno - 3) : node.lineno + 1]).lower()
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if "placeholder" not in context and "conservative default" not in context:
                    continue
                for name in names:
                    if name not in {"uniqueness", "timeliness", "accuracy", "validity", "completeness"}:
                        continue
                    default_measurements.append(
                        {
                            "dimension": name,
                            "literal_value": node.value.value,
                            "citation": asdict(bundle.cite(path, max(1, node.lineno - 1), node.lineno)),
                            "status": "literal_default_not_observed_measurement_requires_review",
                        }
                    )
    return {
        "method": "bounded_static_checks_v1",
        "executed_community_code": False,
        "cli_checks": cli_checks,
        "parser_summaries": parsers,
        "missing_resources": missing_resources,
        "default_measurements": default_measurements,
        "self_attestations": self_attestations,
        "safety_verdict": "not_established",
        "limitations": [
            "literal AST matches are not control-flow or runtime verification",
            "missing resource references can be advisory; review context before grading",
            "quote and SHA validation do not prove semantic relevance or truth",
            "no scan coverage or safety accuracy claim is made",
        ],
    }
