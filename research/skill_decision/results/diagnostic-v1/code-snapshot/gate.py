"""Evidence-constrained decisions. No package source is imported or executed."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from typing import Any

from research.skill_quality.manifest import digest
from research.skill_study.cli_contracts import check_command, parse_contract
from research.skill_study.package_audit import commands


@dataclass(frozen=True)
class Bundle:
    identity: str
    files: dict[str, str]
    expected_hashes: dict[str, str]
    examples: tuple[dict, ...]

    @property
    def fingerprint(self) -> str:
        return digest(
            {
                "identity": self.identity,
                "files": self.files,
                "expected_hashes": self.expected_hashes,
                "examples": self.examples,
            }
        )


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def from_texts(identity: str, texts: dict[str, str]) -> Bundle:
    examples = tuple({**e, "document": "SKILL.md"} for e in commands(texts.get("SKILL.md", "")))
    return Bundle(identity, texts, {p: text_sha(t) for p, t in texts.items()}, examples)


def source_evidence(bundle: Bundle, path: str, start: int = 1, end: int | None = None) -> dict:
    content = bundle.files.get(path)
    if content is None:
        return {"path": path, "status": "missing", "expected_sha256": bundle.expected_hashes.get(path)}
    lines = content.splitlines()
    finish = min(end or start, len(lines))
    return {
        "path": path,
        "sha256": text_sha(content),
        "start_line": start,
        "end_line": finish,
        "quote": "\n".join(lines[max(0, start - 1) : finish]),
    }


def evaluate(
    bundle: Bundle,
    *,
    task_family: str | None = None,
    behavior: dict | None = None,
    trusted_behavior_ids: frozenset[str] = frozenset(),
    omit: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    findings, unknown, observations = [], [], []

    def add(kind: str, layer: str, path: str, explanation: str, line: int = 1, **detail: Any) -> None:
        findings.append(
            {
                "kind": kind,
                "layer": layer,
                "explanation": explanation,
                "evidence": source_evidence(bundle, path, line),
                **detail,
            }
        )

    if "integrity" not in omit:
        for path, expected in bundle.expected_hashes.items():
            if path not in bundle.files:
                add("registered_resource_missing", "integrity", path, "版本清单中的文件缺失")
            elif text_sha(bundle.files[path]) != expected:
                add("registered_hash_mismatch", "integrity", path, "文件与被评价版本的指纹不符")
    for example in bundle.examples:
        script = example.get("script")
        if not script or script not in bundle.files:
            unknown.append({"layer": "cli", "reason": "entrypoint_unresolved", "example": example})
            continue
        source = bundle.files[script]
        try:
            ast.parse(source, filename=script)
        except (SyntaxError, ValueError, RecursionError) as exc:
            add(
                "entrypoint_syntax_error",
                "syntax",
                script,
                "文档指向的入口无法通过 Python 语法解析",
                getattr(exc, "lineno", 1) or 1,
            )
            continue
        if "cli" in omit:
            continue
        contract = parse_contract(source, script)
        if any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr in {"parse_known_args", "parse_intermixed_args", "parse_known_intermixed_args"}
            for n in ast.walk(ast.parse(source))
        ):
            unknown.append({"layer": "cli", "reason": "non_strict_argument_consumption_not_supported"})
            continue
        result = check_command(contract, example["command"])
        observations.append({**example, "result": result})
        if result["status"] == "inconsistent_static":
            for finding in result["findings"]:
                add(
                    finding["kind"],
                    "cli",
                    example.get("document", "SKILL.md"),
                    "文档命令与受支持的字面参数契约冲突",
                    example.get("start_line", 1),
                    command=example["command"],
                    contract_evidence=source_evidence(
                        bundle,
                        script,
                        min((o.line for o in contract.options), default=1),
                        max((o.line for o in contract.options), default=1),
                    ),
                    detail=finding,
                )
        elif result["status"] != "consistent_static":
            unknown.append({"layer": "cli", "reason": result["status"], "details": result.get("reasons", [])})
    if not bundle.examples:
        unknown.append({"layer": "cli", "reason": "no_literal_python_task_example_not_a_defect"})

    runtime = {"state": "not_tested", "task_family": task_family}
    if behavior is not None and "behavior" not in omit:
        if (
            behavior.get("receipt_id") not in trusted_behavior_ids
            or behavior.get("bundle_fingerprint") != bundle.fingerprint
        ):
            runtime = {"state": "untrusted_or_version_mismatched_receipt", "task_family": task_family}
        elif task_family != behavior.get("task_family"):
            runtime = {
                "state": "outside_tested_scope",
                "task_family": task_family,
                "tested_family": behavior.get("task_family"),
            }
        elif behavior.get("n", 0) <= 0 or behavior.get("passed", -1) not in range(behavior["n"] + 1):
            raise ValueError("Invalid behavior receipt counts")
        else:
            runtime = {
                **behavior,
                "state": "passed_tested_suite" if behavior["passed"] == behavior["n"] else "observed_failure",
            }
            if runtime["state"] == "observed_failure":
                add(
                    "independent_artifact_failure",
                    "behavior",
                    "SKILL.md",
                    "匹配版本和任务的独立产物测试中观察到失败",
                    receipt_id=behavior["receipt_id"],
                    failed=behavior["n"] - behavior["passed"],
                )
    if findings:
        decision = "repair_required"
    elif runtime["state"] == "outside_tested_scope":
        decision = "outside_tested_scope"
    elif runtime["state"] == "passed_tested_suite" and not unknown:
        decision = "tested_pass_within_scope"
    else:
        decision = "insufficient_evidence"
    return {
        "method": "evidence_constrained_skill_decision_v1",
        "identity": bundle.identity,
        "bundle_fingerprint": bundle.fingerprint,
        "decision": decision,
        "confirmed_defect": bool(findings),
        "findings": findings,
        "unknown_checks": unknown,
        "command_observations": observations,
        "behavior": runtime,
        "overall_semantic_quality": "not_established",
        "security_certificate": False,
        "model_api_calls": 0,
        "package_code_executed": False,
    }
