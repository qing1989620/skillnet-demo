"""Finite, reviewed CSV operators for capability-frontier experiments.

The registry contains declarations, not learned causal guarantees. Execution uses
only fixed source selected by a whitelisted identifier in a fresh subprocess;
business correctness must be measured by an independent oracle elsewhere.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import uuid

from . import state_contracts

VERSION = 'frontier-csv-operators-v1'
_COLUMNS = ['sample_id', 'subject_id', 'split', 'label', 'score']
FACT_SPECS: dict[str, dict] = {
    'data.file': {'kind': 'file_exists', 'file': 'data.csv'},
    'data.schema': {'kind': 'csv_schema', 'file': 'data.csv', 'columns': _COLUMNS, 'exact': True},
    'data.nonempty': {'kind': 'csv_nonempty', 'file': 'data.csv'},
    'data.unique': {'kind': 'csv_unique', 'file': 'data.csv', 'columns': ['sample_id']},
    'data.disjoint': {'kind': 'csv_disjoint_groups', 'file': 'data.csv', 'entity': 'subject_id', 'group': 'split'},
    'data.complete': {'kind': 'csv_no_missing', 'file': 'data.csv', 'columns': ['score']},
    'data.range': {'kind': 'csv_numeric_range', 'file': 'data.csv', 'column': 'score', 'min': '0', 'max': '1'},
    'data.binary': {'kind': 'csv_values_in', 'file': 'data.csv', 'column': 'label', 'values': ['0', '1']},
    'metrics.file': {'kind': 'file_exists', 'file': 'metrics.csv'},
}

_PREFIX = '''import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from decimal import Decimal, localcontext

ROOT = Path.cwd().resolve()
ALLOWED = {ROOT / name for name in ('main.py', 'input.csv', 'output.csv', 'metrics.csv')}

def audit(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn'):
        raise PermissionError('network and child processes are forbidden')
    if event == 'open' and not isinstance(args[0], int):
        candidate = Path(os.fsdecode(args[0])).resolve()
        if candidate not in ALLOWED:
            raise PermissionError('operator may access only its frozen local artifacts')

sys.addaudithook(audit)
raw = Path('input.csv').read_bytes()
if len(raw) > 16 * 1024 * 1024:
    raise ValueError('input exceeds byte limit')
reader = csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True)
header = next(reader, None)
required = ['sample_id', 'subject_id', 'split', 'label', 'score']
if not header or len(header) != len(required) or set(header) != set(required):
    raise ValueError('input must have exactly the five reviewed CSV columns')
rows = []
for row in reader:
    if len(row) != len(header):
        raise ValueError('inconsistent CSV record width')
    if len(rows) >= 50000:
        raise ValueError('input exceeds row limit')
    rows.append(row)
column = {name: header.index(name) for name in required}

def save_data(selected):
    with Path('output.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(selected)
    print(json.dumps({'input_rows': len(rows), 'output_rows': len(selected)}, sort_keys=True))
'''

_METRICS = '''
metric_rows = [row for row in rows if row[column['split']] == 'test']
if not metric_rows:
    raise ValueError('metrics require at least one split=test holdout record')
tp = tn = fp = fn = 0
for row in metric_rows:
    label = Decimal(row[column['label']].strip())
    score = Decimal(row[column['score']].strip())
    if not label.is_finite() or label not in (Decimal(0), Decimal(1)):
        raise ValueError('label must be binary')
    if not score.is_finite() or not Decimal(0) <= score <= Decimal(1):
        raise ValueError('score must be finite in [0, 1]')
    predicted = score THRESHOLD Decimal('0.5')
    actual = label == Decimal(1)
    tp += int(predicted and actual)
    tn += int(not predicted and not actual)
    fp += int(predicted and not actual)
    fn += int(not predicted and actual)
with localcontext() as context:
    context.prec = 40
    def ratio(numerator, denominator):
        return Decimal(numerator) / Decimal(denominator) if denominator else Decimal(0)
    values = [
        ('n', str(len(metric_rows))), ('tp', str(tp)), ('tn', str(tn)),
        ('fp', str(fp)), ('fn', str(fn)),
        ('accuracy', str(ratio(tp + tn, len(metric_rows)))),
        ('precision', str(ratio(tp, tp + fp))),
        ('recall', str(ratio(tp, tp + fn))),
        ('f1', str(ratio(2 * tp, 2 * tp + fp + fn))),
    ]
with Path('metrics.csv').open('w', encoding='utf-8', newline='') as stream:
    writer = csv.writer(stream)
    writer.writerow(['metric', 'value'])
    writer.writerows(values)
print(json.dumps({'input_rows': len(rows), 'evaluation_rows': len(metric_rows), 'metrics': dict(values)}, sort_keys=True))
'''

_SOURCES = {
    'deduplicate': _PREFIX + '''
seen = set()
selected = []
for row in rows:
    key = row[column['sample_id']]
    if key not in seen:
        selected.append(row)
        seen.add(key)
save_data(selected)
''',
    'exclude_cross_split': _PREFIX + '''
groups = {}
for row in rows:
    groups.setdefault(row[column['subject_id']], set()).add(row[column['split']])
contaminated = {subject for subject, splits in groups.items() if len(splits) > 1}
save_data([row for row in rows if row[column['subject_id']] not in contaminated])
''',
    'drop_missing_score': _PREFIX + '''
save_data([row for row in rows if row[column['score']].strip()])
''',
    'metrics_decimal': _PREFIX + _METRICS.replace('THRESHOLD', '>='),
    'metrics_strict_bug': _PREFIX + _METRICS.replace('THRESHOLD', '>'),
}


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def registry() -> list[dict]:
    """Return independent declaration copies; no operator is auto-certified."""
    labels = {
        'deduplicate': '按 sample_id 保留首次记录',
        'exclude_cross_split': '删除跨 split 的全部 subject 记录',
        'drop_missing_score': '删除空 score 记录',
        'metrics_decimal': 'Decimal 二分类指标（score >= 0.5）',
        'metrics_strict_bug': '实验反例：错误阈值 score > 0.5',
    }
    adds = {'deduplicate': 'data.unique', 'exclude_cross_split': 'data.disjoint',
            'drop_missing_score': 'data.complete'}
    data_facts = [name for name in FACT_SPECS if name.startswith('data.')]
    return [
        {'id': identifier,
         'requires': ['data.schema'] if identifier in adds else list(data_facts),
         'adds': [adds[identifier]] if identifier in adds else ['metrics.file'],
         'deletes': ['data.nonempty', 'data.range', 'data.binary', 'metrics.file'] if identifier in adds else [],
         'cost': 1,
         'metadata': {'label': labels[identifier], 'version': VERSION,
                      'code_sha256': _sha(source.encode('utf-8')),
                      'experimental': True, 'certified': False,
                      'intentional_bug': identifier == 'metrics_strict_bug',
                      'scope': 'fixed five-column CSV; declarations require observed verification'}}
        for identifier, source in _SOURCES.items()
    ]


def observe(data_path: Path, metrics_path: Path | None = None) -> dict:
    """Observe real artifact snapshots, preserving unknown as distinct from false."""
    names = list(FACT_SPECS)
    files = {'data.csv': Path(data_path)}
    if metrics_path is not None:
        files['metrics.csv'] = Path(metrics_path)
    report = state_contracts.evaluate([copy.deepcopy(FACT_SPECS[name]) for name in names], files)
    for name, check in zip(names, report['checks']):
        check['fact_id'] = name
    # Missing columns / parser boundaries do not constitute operator-effect
    # counterexamples. Keep the original schema observation; qualify dependent
    # facts as unknown so experiments cannot learn a false negative effect.
    schema = next(check for check in report['checks'] if check['fact_id'] == 'data.schema')
    if schema['state'] != 'passed':
        for check in report['checks']:
            if check['fact_id'] not in ('data.file', 'data.schema', 'metrics.file'):
                check['observed_state'] = check['state']
                check['state'] = 'unknown'
                check['detail'] = 'data schema was not established; dependent fact is not usable causal evidence'
    states = {check['state'] for check in report['checks']}
    report['state'] = 'failed' if 'failed' in states else 'unknown' if 'unknown' in states else 'passed'
    return {'facts': [check['fact_id'] for check in report['checks'] if check['state'] == 'passed'],
            'checks': report}


def _linked(path: Path) -> bool:
    return any(item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction())
               for item in (path, *path.parents))


def _read_input(path: Path) -> bytes:
    path = path.absolute()
    if _linked(path):
        raise ValueError('linked input paths are not admissible')
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_size > state_contracts.MAX_BYTES:
        raise ValueError('input must be a bounded regular file')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError('input changed before snapshot')
        raw = stream.read(state_contracts.MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
    if (len(raw) > state_contracts.MAX_BYTES or len(raw) != before.st_size
            or (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
        raise ValueError('input changed during snapshot or exceeded byte limit')
    return raw


def execute(operator_id: str, input_path: Path, workspace: Path, *, timeout_seconds: float = 5) -> dict:
    """Run one fixed operator and retain its frozen input, source and artifacts.

    Status reports process completion only. In particular, successful execution
    of ``metrics_strict_bug`` is deliberately not evidence of correctness.
    No network, shell, arbitrary user code, model calls, or original-file writes
    occur in this executor. This bounded experiment runner is not an OS sandbox
    for untrusted programs.
    """
    result = {'version': VERSION, 'operator_id': operator_id, 'status': 'rejected',
              'output_path': None, 'metrics_path': None, 'returncode': None,
              'stdout': '', 'stderr': '', 'code_sha256': None,
              'input_sha256': None, 'output_sha256': None, 'metrics_sha256': None,
              'workspace': None, 'network_allowed': False, 'certified': False}
    if not isinstance(operator_id, str) or operator_id not in _SOURCES:
        result['stderr'] = 'unsupported operator identifier'
        return result
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 30):
        result['stderr'] = 'timeout_seconds must be finite and in (0, 30]'
        return result
    source = _SOURCES[operator_id].encode('utf-8')
    result['code_sha256'] = _sha(source)
    try:
        raw = _read_input(Path(input_path))
        workspace = Path(workspace).absolute()
        if _linked(workspace):
            raise ValueError('linked workspace paths are not admissible')
        workspace.mkdir(parents=True, exist_ok=True)
        if _linked(workspace):
            raise ValueError('linked workspace paths are not admissible')
        attempt = workspace / f'{operator_id}-{uuid.uuid4().hex}'
        attempt.mkdir(exist_ok=False)
        (attempt / 'input.csv').write_bytes(raw)
        (attempt / 'main.py').write_bytes(source)
        result.update(workspace=str(attempt), input_sha256=_sha(raw))
        try:
            completed = subprocess.run(
                [sys.executable, '-I', '-B', 'main.py'], cwd=str(attempt),
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=timeout_seconds, shell=False,
                env={key: value for key, value in os.environ.items()
                     if key.upper() in ('SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'PATH', 'LANG', 'LC_ALL')},
            )
            result.update(status='completed' if completed.returncode == 0 else 'failed',
                          returncode=completed.returncode,
                          stdout=completed.stdout[:8192], stderr=completed.stderr[:8192])
        except subprocess.TimeoutExpired as exc:
            def decoded(value):
                return value.decode('utf-8', 'replace') if isinstance(value, bytes) else (value or '')
            result.update(status='timeout', stdout=decoded(exc.stdout)[:8192],
                          stderr=(decoded(exc.stderr) + '\nfixed operator exceeded execution timeout')[:8192])
        for filename, path_key, sha_key in (
            ('output.csv', 'output_path', 'output_sha256'),
            ('metrics.csv', 'metrics_path', 'metrics_sha256'),
        ):
            artifact = attempt / filename
            if artifact.is_file() and not _linked(artifact):
                result[path_key] = str(artifact)
                result[sha_key] = _sha(artifact.read_bytes())
        # A zero exit without its promised artifact cannot be a completed action.
        expected = 'metrics_path' if operator_id.startswith('metrics_') else 'output_path'
        if result['status'] == 'completed' and result[expected] is None:
            result.update(status='failed', stderr='fixed operator did not create its promised artifact')
        if result['stdout']:
            try:
                result['execution_summary'] = json.loads(result['stdout'])
            except (ValueError, TypeError):
                pass
    except (OSError, ValueError, TypeError) as exc:
        result.update(status='rejected', stderr=str(exc)[:8192])
    return result
