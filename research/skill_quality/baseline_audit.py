"""Run trusted repository diagnostics in a separate worktree; never replay paid calls."""

from __future__ import annotations

import argparse
import ast
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .manifest import file_sha, write_once
from .snapshot import git_commit

SOURCE_FILES = (
    "skillnet/schema.py",
    "skillnet/catalog.py",
    "skillnet/retriever.py",
    "skillnet/judge.py",
    "skillnet/assessment.py",
    "skillnet/reward_gates.py",
    "skillnet/resources.py",
    "skillnet/llm.py",
    "skillnet/semantic.py",
    "bench/run_bench.py",
)


def inspect_repository(root: Path) -> dict[str, Any]:
    interfaces = []
    for name in SOURCE_FILES:
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                interfaces.append(
                    {"file": name, "name": node.name, "line": node.lineno, "args": ast.unparse(node.args)}
                )
            elif isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and method.name in (
                        "__init__",
                        "load",
                        "search",
                        "build",
                        "save",
                    ):
                        interfaces.append(
                            {
                                "file": name,
                                "name": node.name + "." + method.name,
                                "line": method.lineno,
                                "args": ast.unparse(method.args),
                            }
                        )
    release = json.loads((root / "config/delivery.json").read_text(encoding="utf-8"))
    return {
        "commit": git_commit(root),
        "release": release,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "docker_available": shutil.which("docker") is not None,
        "interfaces": interfaces,
        "source_hashes": {name: file_sha(root / name) for name in SOURCE_FILES},
        "tracked_secret_files": subprocess.check_output(
            ["git", "ls-files", ".env", ".env.local"], cwd=root, text=True
        ).splitlines(),
    }


def run_check(
    name: str, args: list[str], root: Path, output: Path, env: dict[str, str], timeout: int
) -> dict[str, Any]:
    log = output / (name + ".log")
    started = time.monotonic()
    print("START " + name, flush=True)
    status, exit_code = "finished", None
    with log.open("xb") as stream:
        try:
            result = subprocess.run(
                args, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout, check=False
            )
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            status = "timeout"
    row = {
        "name": name,
        "command": args,
        "status": status,
        "exit_code": exit_code,
        "seconds": round(time.monotonic() - started, 3),
        "log": log.name,
        "log_sha256": file_sha(log),
    }
    write_once(output / (name + ".json"), row)
    print(f"END {name}: {exit_code} ({row['seconds']}s)", flush=True)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--validation-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.validation_root.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_once(output / "repository_audit.json", inspect_repository(args.repo.resolve()))
    if git_commit(root) != git_commit(args.repo.resolve()):
        raise ValueError("Validation worktree differs from baseline commit")
    env = {
        k: v
        for k, v in os.environ.items()
        if not any(word in k.upper() for word in ("API_KEY", "TOKEN", "SECRET", "PASSWORD"))
    }
    # Environment data paths are deliberately left at the cloned defaults for
    # regression parity. All mutations are confined to the validation worktree.
    for k in list(env):
        if k.startswith("SKILLNET_"):
            del env[k]
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    env["PYTHONPATH"] = str(Path(__file__).parent / "_offline_site") + os.pathsep + str(root)
    checks = [
        ("delivery_before", [sys.executable, "tools/verify_delivery.py", "--strict-runtime"], 180),
        ("dependencies", [sys.executable, "-m", "pip", "freeze", "--all"], 120),
        ("pip_check", [sys.executable, "-m", "pip", "check"], 120),
        (
            "pytest",
            [sys.executable, "-m", "pytest", "tests", "-q", "--junitxml=" + str(output / "pytest.xml")],
            1800,
        ),
        ("verify", [sys.executable, "verify.py"], 600),
        ("conditional_evidence", [sys.executable, "tools/verify_conditional_evidence.py"], 240),
        (
            "semantic_evidence",
            [sys.executable, "tools/verify_semantic_routing.py", "--public", "assets/semantic-routing/v1"],
            240,
        ),
        (
            "guard_evidence",
            [
                sys.executable,
                "tools/verify_reviewed_guard.py",
                "--public",
                "assets/semantic-routing/guard-v1",
            ],
            240,
        ),
        ("delivery_after", [sys.executable, "tools/verify_delivery.py", "--strict-runtime"], 180),
        ("worktree_diff", ["git", "status", "--short"], 60),
    ]
    results = [run_check(name, command, root, output, env, timeout) for name, command, timeout in checks]
    write_once(output / "checks.json", results)


if __name__ == "__main__":
    main()
