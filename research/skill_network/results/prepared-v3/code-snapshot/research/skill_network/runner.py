"""One fixed owned worker per batch, local or Docker; no arbitrary code input."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from research.skill_quality.manifest import file_sha, write_once


def execute_batch(requests: list[dict], output: Path, *, backend: str = "trusted_process") -> list[dict]:
    if output.exists():
        raise FileExistsError("Execution batches are immutable")
    output.mkdir(parents=True)
    worker = Path(__file__).with_name("kernels.py")
    script, input_path = output / "worker.py", output / "requests.jsonl"
    script.write_bytes(worker.read_bytes())
    assert file_sha(script) == file_sha(worker)
    write_once(input_path, requests, jsonl=True)
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "SYSTEMROOT", "WINDIR", "LANG", "LC_ALL"}}
    if backend == "docker":
        output.chmod(0o755)
        script.chmod(0o644)
        input_path.chmod(0o644)
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
            "--mount",
            f"type=bind,source={output.resolve()},target=/work,readonly",
            os.environ["SKILL_NETWORK_IMAGE"],
            "python",
            "-I",
            "-B",
            "/work/worker.py",
            "/work/requests.jsonl",
        ]
    elif backend == "trusted_process":
        command = [sys.executable, "-I", "-B", "-X", "utf8", str(script.resolve()), str(input_path.resolve())]
    else:
        raise ValueError("Unknown backend; no automatic fallback")
    started = time.monotonic()
    proc = subprocess.run(
        command, capture_output=True, encoding="utf-8", errors="strict", timeout=180, env=env
    )
    if proc.returncode != 0:
        write_once(output / "infra-error.json", {"returncode": proc.returncode, "stderr": proc.stderr[:4000]})
        raise RuntimeError("Owned worker infrastructure failed; no task score imputed")
    rows = [json.loads(line) for line in proc.stdout.splitlines()]
    assert len(rows) == len(requests)
    assert [r["execution_id"] for r in rows] == [r["execution_id"] for r in requests]
    write_once(output / "outcomes.jsonl", rows, jsonl=True)
    write_once(
        output / "batch.json",
        {
            "backend": backend,
            "worker_sha256": file_sha(script),
            "executions": len(rows),
            "wall_seconds": time.monotonic() - started,
            "model_calls": 0,
            "api_cost_usd": 0,
            "scope": "only owned fixed worker; local process is not an untrusted-code sandbox",
        },
    )
    return rows
