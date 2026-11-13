"""Container-only fixed original-CLI worker. No arbitrary commands accepted."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

assert Path("/.dockerenv").exists() and os.getuid() == 65534
assert not any(os.environ.get(k) for k in ["DEEPSEEK_API_KEY", "OPENROUTER_API_KEY", "GITHUB_TOKEN"])
work = Path("/work")
requests = json.loads((work / "requests.json").read_text())
outcomes = []
for row in requests:
    target = Path("/tmp/requested-output.json")
    if target.exists():
        target.unlink()
    script = work / "scripts" / row["script"]
    proc = subprocess.run(
        [sys.executable, "-I", "-B", str(script), *row["args"]],
        capture_output=True,
        encoding="utf-8",
        timeout=10,
        cwd="/tmp",
    )
    outcomes.append(
        {
            **row,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "output_exists": target.exists(),
            "source_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        }
    )
status = dict(
    line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":" in line
)
boundary = {
    "uid": os.getuid(),
    "no_new_privileges": status["NoNewPrivs"].strip() == "1",
    "capabilities_zero": int(status["CapEff"].strip(), 16) == 0,
    "credentials_absent": True,
    "scope": "fixed reviewed 9 original CLIs plus 2 minimally repaired copies",
}
print(json.dumps({"outcomes": outcomes, "boundary": boundary}))
