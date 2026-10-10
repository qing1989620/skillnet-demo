"""Exercise the production Docker adapter on Linux; no model calls or credentials."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skillnet.sandbox import run_python

PROBE = r'''
import csv, json, os, socket
from pathlib import Path
import numpy, pandas
status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
mounts = [line.split() for line in Path('/proc/mounts').read_text().splitlines()]
root = next(line for line in mounts if line[1] == '/')
network_blocked = False
try:
    connection = socket.create_connection(('1.1.1.1', 443), timeout=2)
    connection.close()
except OSError:
    network_blocked = True
facts = dict(uid=os.getuid(), no_new_privileges=status['NoNewPrivs'].strip() == '1',
             capabilities_zero=int(status['CapEff'].strip(), 16) == 0,
             root_read_only='ro' in root[3].split(','), network_blocked=network_blocked,
             credentials_absent=not any(os.environ.get(k) for k in ['DEEPSEEK_API_KEY','SKILLNET_TOKEN','SKILLNET_S1_SIGNING_KEY','SKILLNET_SMOKE_SECRET']),
             memory_limit=Path('/sys/fs/cgroup/memory.max').read_text().strip(),
             pids_limit=Path('/sys/fs/cgroup/pids.max').read_text().strip(),
             cpu_limit=Path('/sys/fs/cgroup/cpu.max').read_text().strip())
values = [int(row['value']) for row in csv.DictReader(Path('input.csv').open())]
assert values == [2, 3, 5]
facts['input_sum'] = sum(values)
Path('result.json').write_text(json.dumps(facts))
print(json.dumps(facts))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, default=ROOT / 'out/docker-smoke.json')
    args = parser.parse_args()
    os.environ['SKILLNET_SANDBOX'] = 'docker'
    os.environ['SKILLNET_SMOKE_SECRET'] = 'public-smoke-sentinel'
    with tempfile.TemporaryDirectory(prefix='skillnet-docker-') as directory:
        work = Path(directory)
        (work / 'input.csv').write_text('value\n2\n3\n5\n', encoding='utf-8')
        first = run_python(PROBE, workdir=work, keep_dir=True, timeout=90)
        if not first['ok']:
            raise RuntimeError('Container probe failed: ' + first['stderr'])
        facts = json.loads((work / 'result.json').read_text())
        assert facts['uid'] != 0, facts
        for key in ['no_new_privileges', 'capabilities_zero', 'root_read_only', 'network_blocked', 'credentials_absent']:
            assert facts[key] is True, (key, facts)
        assert facts['input_sum'] == 10
        assert facts['memory_limit'] == str(768 * 1024 * 1024)
        assert facts['pids_limit'] == '64'
        quota, period = facts['cpu_limit'].split()
        assert int(quota) / int(period) == 2
        assert {a['name'] for a in first['artifacts']} == {'result.json'}
        second = run_python("import json\nfrom pathlib import Path\nf=json.loads(Path('result.json').read_text())\nPath('followup.csv').write_text('sum\\n'+str(f['input_sum'])+'\\n')", workdir=work, keep_dir=True)
        assert second['ok'], second['stderr']
        assert (work / 'followup.csv').read_text() == 'sum\n10\n'
        timeout = run_python('import time;time.sleep(30)', workdir=work, keep_dir=True, timeout=2)
        assert not timeout['ok'] and timeout['error_kind'] == 'timeout'
        report = dict(status='passed', platform=sys.platform, image=os.environ.get('SKILLNET_SANDBOX_IMAGE', 'skillnet-executor:local'),
                      facts=facts, consecutive_file_handoff=True, timeout_enforced=True,
                      result_sha256=hashlib.sha256((work / 'result.json').read_bytes()).hexdigest(),
                      model_calls=0, boundary='Linux Docker smoke; not a penetration test or Windows Docker validation')
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
