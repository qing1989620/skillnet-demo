"""Observe the Docker execution boundary; never fall back to host execution."""

from __future__ import annotations

import json
import os
import subprocess

PROBE = """import json,os,socket
from pathlib import Path
status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
mounts=[line.split() for line in Path('/proc/mounts').read_text().splitlines()]
root=next(line for line in mounts if line[1]=='/')
blocked=False
try:
    conn=socket.create_connection(('1.1.1.1',443),timeout=1)
    conn.close()
except OSError:
    blocked=True
facts={'uid':os.getuid(),'no_new_privileges':status['NoNewPrivs'].strip()=='1',
'capabilities_zero':int(status['CapEff'].strip(),16)==0,'root_read_only':'ro' in root[3].split(','),
'network_blocked':blocked,'credentials_absent':not any(os.environ.get(k) for k in
['DEEPSEEK_API_KEY','OPENROUTER_API_KEY','GITHUB_TOKEN','GH_TOKEN']),
'memory_limit':Path('/sys/fs/cgroup/memory.max').read_text().strip(),
'pids_limit':Path('/sys/fs/cgroup/pids.max').read_text().strip(),
'cpu_limit':Path('/sys/fs/cgroup/cpu.max').read_text().strip()}
print(json.dumps(facts))
"""


def probe() -> dict:
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
        os.environ["SKILL_DECISION_IMAGE"],
        "python",
        "-I",
        "-B",
        "-c",
        PROBE,
    ]
    result = subprocess.run(command, capture_output=True, encoding="utf-8", timeout=30, check=True)
    facts = json.loads(result.stdout)
    assert facts["uid"] != 0
    for key in [
        "no_new_privileges",
        "capabilities_zero",
        "root_read_only",
        "network_blocked",
        "credentials_absent",
    ]:
        assert facts[key] is True, key
    assert facts["memory_limit"] == str(128 * 1024 * 1024)
    assert facts["pids_limit"] == "32"
    quota, period = facts["cpu_limit"].split()
    assert int(quota) / int(period) == 1
    return {
        "status": "PASS",
        "image": os.environ["SKILL_DECISION_IMAGE"],
        "facts": facts,
        "scope": "Observed owned-code container boundary, not a penetration test",
    }


if __name__ == "__main__":
    print(json.dumps(probe(), indent=2))
