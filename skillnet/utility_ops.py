"""Reviewed, finite tabular skill interventions; never execute model-written code.

The three bits enable first-id deduplication, cross-split subject exclusion,
and blank-value deletion. A common aggregator always runs last. Task intent
belongs to the independent evaluator, not to the program being evaluated.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from .frontier_ops import _linked, _read_input

VERSION = 'conditional-tabular-operators-v1'
NAMES = ('deduplicate', 'exclude_cross_split', 'drop_missing')
HEADER = ['sample_id', 'subject_id', 'split', 'group', 'value']
SOURCE = '''import csv, io, json, os, sys, encodings.utf_8_sig
from pathlib import Path
from decimal import Decimal, localcontext

root = Path.cwd().resolve()
allowed = {root / n for n in ('main.py','input.csv','output.csv','summary.csv')}
def audit(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.exec','os.posix_spawn'):
        raise PermissionError('network and subprocesses forbidden')
    if event == 'open' and not isinstance(args[0], int):
        if Path(os.fsdecode(args[0])).resolve() not in allowed:
            raise PermissionError('only frozen local artifacts allowed')
sys.addaudithook(audit)
mask = int(sys.argv[1])
if not 0 <= mask <= 7: raise ValueError('unregistered mask')
raw = Path('input.csv').read_bytes()
if len(raw) > 1048576: raise ValueError('input too large')
table = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'),newline=''),strict=True))
if not table or table[0] != ['sample_id','subject_id','split','group','value']:
    raise ValueError('schema mismatch')
rows = table[1:]
if len(rows) > 5000 or any(len(r) != 5 for r in rows): raise ValueError('invalid rows')
if mask & 1:
    seen = set(); kept = []
    for r in rows:
        if r[0] not in seen: kept.append(r); seen.add(r[0])
    rows = kept
if mask & 2:
    splits = {}
    for r in rows: splits.setdefault(r[1],set()).add(r[2])
    rows = [r for r in rows if len(splits[r[1]]) == 1]
if mask & 4: rows = [r for r in rows if r[4].strip()]
with Path('output.csv').open('w',encoding='utf-8',newline='') as f:
    w = csv.writer(f); w.writerow(table[0]); w.writerows(rows)
groups = {}
for r in rows:
    if r[2] != 'test': continue
    groups.setdefault(r[3],[]).append(r[4])
if not groups: raise ValueError('no test records')
out = []
with localcontext() as ctx:
    ctx.prec = 40
    for group, values in sorted(groups.items()):
        numeric = [Decimal(v.strip()) for v in values if v.strip()]
        if not numeric or any(not v.is_finite() or abs(v) > Decimal('1e12') for v in numeric):
            raise ValueError('no finite numeric values for group')
        total = sum(numeric,Decimal(0))
        out.append([group,str(len(values)),str(len(numeric)),str(total),str(total/len(numeric))])
with Path('summary.csv').open('w',encoding='utf-8',newline='') as f:
    w = csv.writer(f); w.writerow(['group','n_rows','n_numeric','sum','mean']); w.writerows(out)
print(json.dumps({'mask':mask,'rows':len(rows),'groups':len(out)}))
'''
CODE_SHA = hashlib.sha256(SOURCE.encode()).hexdigest()


def execute(mask: int, source: Path, workspace: Path) -> dict:
    if type(mask) is not int or not 0 <= mask <= 7:
        raise ValueError('mask must be a registered integer in [0,7]')
    work = Path(workspace).absolute()
    if _linked(work):
        raise ValueError('linked workspaces are forbidden')
    work.mkdir(parents=True, exist_ok=False)
    raw = _read_input(Path(source))
    (work / 'input.csv').write_bytes(raw)
    (work / 'main.py').write_text(SOURCE, encoding='utf-8', newline='\n')
    started = time.time_ns()
    try:
        result = subprocess.run([sys.executable, '-I', '-S', str(work / 'main.py'), str(mask)],
                                cwd=work, capture_output=True, timeout=8, shell=False)
        status = 'completed' if result.returncode == 0 else 'failed'
        stderr = result.stderr.decode('utf-8', 'replace').replace(str(work), '<workspace>').replace(sys.prefix, '<python>')[-2000:]
    except subprocess.TimeoutExpired:
        status, stderr = 'timeout', 'fixed operator exceeded eight seconds'
    artifacts = {}
    for name in ('output.csv', 'summary.csv'):
        path = work / name
        if path.is_file():
            value = _read_input(path)
            artifacts[name] = {'sha256': hashlib.sha256(value).hexdigest(), 'bytes': len(value)}
    return {'version': VERSION, 'mask': mask, 'code_sha256': CODE_SHA,
            'input_sha256': hashlib.sha256(raw).hexdigest(), 'started_at_ns': started,
            'finished_at_ns': time.time_ns(), 'status': status, 'stderr': stderr,
            'artifacts': artifacts, 'operator_calls': 1 + mask.bit_count()}
