"""Executable fixtures authored here, never arbitrary community/model code."""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from research.skill_quality.manifest import digest

from .gate import Bundle, from_texts, text_sha

PROGRAMS = {
    "sum_correct": ("integer_sum", "return {'value': sum(case['values'])}"),
    "sum_abs": ("integer_sum", "return {'value': sum(abs(x) for x in case['values'])}"),
    "sum_drop_last": ("integer_sum", "return {'value': sum(case['values'][:-1])}"),
    "sum_stub": ("integer_sum", "return {'success': True}"),
    "dedup_correct": (
        "stable_full_row_dedup",
        "return {'rows': [list(r) for r in dict.fromkeys(tuple(r) for r in case['rows'])]}",
    ),
    "dedup_key": (
        "stable_full_row_dedup",
        "seen = set()\n    return {'rows': [r for r in case['rows'] if not (r[0] in seen or seen.add(r[0]))]}",
    ),
    "dedup_sort": (
        "stable_full_row_dedup",
        "return {'rows': [list(r) for r in sorted(set(tuple(r) for r in case['rows']))]}",
    ),
    "dedup_stub": ("stable_full_row_dedup", "return {'success': True}"),
    "dag_correct": (
        "directed_order",
        "nodes = case['nodes']\n    remaining = set(nodes)\n    order = []\n    while remaining:\n        ready = [n for n in nodes if n in remaining and not any(v == n and u in remaining for u, v in case['edges'])]\n        if not ready:\n            return {'status': 'cycle', 'order': []}\n        order.extend(ready)\n        remaining.difference_update(ready)\n    return {'status': 'ok', 'order': order}",
    ),
    "dag_ignore_edges": ("directed_order", "return {'status': 'ok', 'order': sorted(case['nodes'])}"),
    "dag_reverse": (
        "directed_order",
        "nodes = case['nodes']\n    remaining = set(nodes)\n    order = []\n    while remaining:\n        ready = [n for n in nodes if n in remaining and not any(u == n and v in remaining for u, v in case['edges'])]\n        if not ready:\n            return {'status': 'cycle', 'order': []}\n        order.extend(ready)\n        remaining.difference_update(ready)\n    return {'status': 'ok', 'order': order}",
    ),
    "dag_stub": ("directed_order", "return {'success': True}"),
}


def script_source(program: str) -> str:
    body = PROGRAMS[program][1]
    return (
        "import argparse\nimport json\nfrom pathlib import Path\n\n"
        + "def solve(case):\n    "
        + body
        + "\n\n"
        + "parser = argparse.ArgumentParser(allow_abbrev=False)\n"
        + "parser.add_argument('--input', required=True)\n"
        + "args = parser.parse_args()\n"
        + "print(json.dumps(solve(json.loads(Path(args.input).read_text(encoding='utf-8')))))\n"
    )


def program_bundle(program: str) -> Bundle:
    family = PROGRAMS[program][0]
    doc = (
        f"# Controlled fixture for {family}\n"
        + "Input and output rules are fixed by the task contract.\n"
        + "1. Read the JSON input.\n2. Calculate the requested output.\n"
        + "3. Preserve required ordering.\n4. Check the result before release.\n"
        + "Pitfalls: do not delete inputs; do not invent success.\n"
        + "Verification: compare artifacts; check exact schema.\n"
        + "Budget: standard-library CPU only.\n"
        + "```bash\npython scripts/run.py --input input.json\n```\n"
    )
    # Program identity is deliberately absent from prose, making documentation
    # identical across correct and defective implementations of a given task.
    return from_texts(program, {"SKILL.md": doc, "scripts/run.py": script_source(program)})


def make_inputs(seed: int = 20261112) -> list[dict]:
    rng = random.Random(seed)
    output = []
    for i in range(24):
        values = [rng.randrange(-40, 41) for _ in range(2 + i % 11)]
        if i == 0:
            values = []
        elif i % 3 == 0:
            values[-1] = -7
        output.append(
            {"family": "integer_sum", "id": f"sum-{i:02}", "input": {"values": values}, "truth": sum(values)}
        )
        rows = [[str(rng.randrange(4)), str(rng.randrange(5))] for _ in range(4 + i % 8)]
        if i == 0:
            rows = []
        elif i % 2 == 0:
            rows.extend([rows[0].copy(), rows[1].copy()])
        expected = []
        for row in rows:
            if row not in expected:
                expected.append(row.copy())
        output.append(
            {
                "family": "stable_full_row_dedup",
                "id": f"dedup-{i:02}",
                "input": {"rows": rows},
                "truth": expected,
            }
        )
        nodes = [f"n{j}" for j in range(3 + i % 7)]
        rng.shuffle(nodes)
        edges = [[nodes[j], nodes[j + 1]] for j in range(len(nodes) - 1)]
        cyclic = i % 4 == 0
        if cyclic:
            edges.append([nodes[-1], nodes[0]])
        shown_nodes = nodes.copy()
        rng.shuffle(shown_nodes)
        output.append(
            {
                "family": "directed_order",
                "id": f"dag-{i:02}",
                "input": {"nodes": shown_nodes, "edges": edges},
                "truth": "cycle" if cyclic else "dag",
            }
        )
    return output


def verify_output(fixture: dict, artifact: object) -> bool:
    if not isinstance(artifact, dict):
        return False
    family = fixture["family"]
    if family == "integer_sum":
        return (
            set(artifact) == {"value"}
            and type(artifact["value"]) is int
            and artifact["value"] == fixture["truth"]
        )
    if family == "stable_full_row_dedup":
        return set(artifact) == {"rows"} and artifact["rows"] == fixture["truth"]
    if set(artifact) != {"status", "order"}:
        return False
    order = artifact["order"]
    if fixture["truth"] == "cycle":
        return artifact["status"] == "cycle" and order == []
    nodes = fixture["input"]["nodes"]
    if artifact["status"] != "ok" or not isinstance(order, list) or len(order) != len(nodes):
        return False
    if any(type(n) is not str for n in order) or set(order) != set(nodes):
        return False
    position = {n: i for i, n in enumerate(order)}
    return all(position[u] < position[v] for u, v in fixture["input"]["edges"])


def run_owned(
    bundle: Bundle, program: str, fixtures: list[dict], *, backend: str = "trusted_process"
) -> tuple[dict, list[dict]]:
    # Never use this to import/run an arbitrary Skill. Exact registry bytes and
    # a fixed command separate owned diagnostic code from untrusted packages.
    source = bundle.files.get("scripts/run.py", "")
    if source != script_source(program) or bundle.expected_hashes.get("scripts/run.py") != text_sha(source):
        raise ValueError("Only exact locally authored registry programs can run")
    if backend not in {"trusted_process", "docker"}:
        raise ValueError("Unknown execution backend")
    results = []
    selected = [f for f in fixtures if f["family"] == PROGRAMS[program][0]]
    with tempfile.TemporaryDirectory(prefix="skill-owned-") as directory:
        work = Path(directory)
        if backend == "docker":
            work.chmod(0o755)
        script = work / "run.py"
        # Write bytes so Windows newline conversion cannot change the exact
        # registered source version used by the child process.
        script.write_bytes(source.encode("utf-8"))
        executed_source_sha256 = text_sha(script.read_bytes().decode("utf-8"))
        assert executed_source_sha256 == bundle.expected_hashes["scripts/run.py"]
        if backend == "docker":
            script.chmod(0o644)
        env = {k: v for k, v in os.environ.items() if k in {"SYSTEMROOT", "WINDIR", "PATH", "LANG", "LC_ALL"}}
        env.update({"HOME": str(work), "TMP": str(work), "TEMP": str(work)})
        for fixture in selected:
            data = work / "input.json"
            data.write_text(json.dumps(fixture["input"]), encoding="utf-8")
            if backend == "docker":
                data.chmod(0o644)
            if backend == "docker":
                # No network, credentials or project/host mounts. Image must
                # already be supplied and inspected by the CI runner.
                image = os.environ["SKILL_DECISION_IMAGE"]
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
                    f"type=bind,source={work},target=/work,readonly",
                    image,
                    "python",
                    "-I",
                    "-B",
                    "/work/run.py",
                    "--input",
                    "/work/input.json",
                ]
            else:
                command = [sys.executable, "-I", "-B", "-X", "utf8", str(script), "--input", str(data)]
            proc = subprocess.run(
                command,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
                env=env,
                cwd=work,
            )
            try:
                artifact = json.loads(proc.stdout) if proc.returncode == 0 else None
            except json.JSONDecodeError:
                artifact = None
            results.append(
                {
                    "program": program,
                    "fixture_id": fixture["id"],
                    "family": fixture["family"],
                    "input_sha256": digest(fixture["input"]),
                    "artifact": artifact,
                    "passed": proc.returncode == 0 and verify_output(fixture, artifact),
                    "returncode": proc.returncode,
                    "stderr": proc.stderr[:1000],
                    "backend": backend,
                    "executed_source_sha256": executed_source_sha256,
                }
            )
    per_input: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "passed": 0})
    for row in results:
        per_input[row["input_sha256"]]["n"] += 1
        per_input[row["input_sha256"]]["passed"] += int(row["passed"])
    receipt = {
        "bundle_fingerprint": bundle.fingerprint,
        "task_family": PROGRAMS[program][0],
        "n": len(results),
        "passed": sum(r["passed"] for r in results),
        "outcomes_sha256": digest(results),
        "backend": backend,
        "input_outcomes": dict(per_input),
        "executed_source_sha256": executed_source_sha256,
        "scope": "owned executable fixture; not arbitrary community code or a security certificate",
    }
    receipt["receipt_id"] = digest(receipt)
    return receipt, results
