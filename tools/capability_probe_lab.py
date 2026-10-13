"""Execute reviewed implementations against frozen, synthetic capability probes.

This experiment changes an admission policy, not skill wording, a model or the
production library. No LLM or network is used. Finite probe agreement is not a
proof of universal equivalence, and admission is not a causal skill score.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
from pathlib import Path
import random
import sys
import time
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from skillnet import sandbox
from skillnet.state_contracts import VERSION as CONTRACT_VERSION, evaluate

VERSION = 'capability-probe-lab-v1'
SEED = 20261012
HEADER = ['sample_id', 'subject_id', 'split', 'label', 'score']

# These are fixed reviewed programs, not retrieved code or generated output.
# No credentials, package installs, external writes or networking are involved.
CSV_IMPLEMENTATION = '''import csv, json
from pathlib import Path
rows = list(csv.DictReader(Path('predictions.csv').open(encoding='utf-8-sig', newline='')))
test = [r for r in rows if r['split'] == 'test']
counts = dict(n=len(test), tp=0, fp=0, tn=0, fn=0)
for r in test:
    positive = float(r['score']) >= 0.5
    actual = int(r['label']) == 1
    key = 'tp' if positive and actual else 'fp' if positive else 'fn' if actual else 'tn'
    counts[key] += 1
Path('heldout_metrics.json').write_text(json.dumps(counts, sort_keys=True), encoding='utf-8')
'''

DECIMAL_IMPLEMENTATION = '''from decimal import Decimal
import csv
import json
from pathlib import Path
with Path('predictions.csv').open(encoding='utf-8-sig', newline='') as stream:
    reader = csv.reader(stream)
    columns = next(reader)
    values = [dict(zip(columns, row)) for row in reader]
pairs = [(r['label'] == '1', Decimal(r['score']) >= Decimal('0.5'))
         for r in values if r['split'] == 'test']
result = {'n': len(pairs),
          'tp': sum(a and p for a, p in pairs),
          'fp': sum(not a and p for a, p in pairs),
          'tn': sum(not a and not p for a, p in pairs),
          'fn': sum(a and not p for a, p in pairs)}
Path('heldout_metrics.json').write_text(json.dumps(result, sort_keys=True), encoding='utf-8')
'''

IMPLEMENTATIONS = {
    'csv-threshold-ge': CSV_IMPLEMENTATION,
    'decimal-sum-ge': DECIMAL_IMPLEMENTATION,
    'csv-threshold-gt-bug': CSV_IMPLEMENTATION.replace("float(r['score']) >= 0.5", "float(r['score']) > 0.5"),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def csv_bytes(rows, header=HEADER):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def predicates():
    """Authored scope for fixed-threshold metrics, not an inferred cleaning policy."""
    return [
        dict(kind='csv_schema', file='predictions.csv', columns=HEADER, exact=True),
        dict(kind='csv_nonempty', file='predictions.csv'),
        dict(kind='csv_no_missing', file='predictions.csv', columns=HEADER),
        dict(kind='csv_unique', file='predictions.csv', columns=['sample_id']),
        dict(kind='csv_numeric_range', file='predictions.csv', column='score', min=0, max=1),
        dict(kind='csv_values_in', file='predictions.csv', column='label', values=[0, 1]),
        dict(kind='csv_disjoint_groups', file='predictions.csv', entity='subject_id', group='split'),
    ]


def fixtures():
    normal = [
        ['s01', 'p01', 'train', '0', '0.1'],
        ['s02', 'p02', 'train', '1', '0.9'],
        ['s03', 'p03', 'test', '1', '0.9'],
        ['s04', 'p04', 'test', '0', '0.2'],
        ['s05', 'p05', 'test', '1', '0.4'],
        ['s06', 'p06', 'test', '0', '0.8'],
    ]
    def changed(row, column, value):
        out = [r[:] for r in normal]
        out[row][column] = value
        return out
    boundary = changed(2, 4, '0.5')
    boundary[3][4] = '0.5'
    specs = [
        ('clean', normal, HEADER, 'passed', True, None),
        ('threshold_boundary', boundary, HEADER, 'passed', True, None),
        ('missing_score', changed(2, 4, ''), HEADER, 'failed', False, 'missing score'),
        ('duplicate_sample', normal + [normal[2][:]], HEADER, 'failed', False, 'duplicate sample_id'),
        ('score_out_of_range', changed(2, 4, '1.4'), HEADER, 'failed', False, 'score outside [0,1]'),
        ('schema_drift', normal, HEADER[:-1] + ['prediction'], 'failed', False, 'score column renamed'),
        ('subject_leakage', changed(2, 1, 'p01'), HEADER, 'failed', False, 'subject crosses train/test'),
        ('nonfinite_score', changed(2, 4, 'NaN'), HEADER, 'failed', False, 'nonfinite score'),
        ('fractional_label', changed(2, 3, '0.5'), HEADER, 'failed', False, 'binary label is neither 0 nor 1'),
        ('empty_table', [], HEADER, 'failed', False, 'no observations'),
        ('unsupported_unit_constraint', normal, HEADER, 'unknown', None, 'required unit semantics have no verifier'),
    ]
    result = []
    for name, rows, header, expected_state, in_scope, reason in specs:
        content = csv_bytes(rows, header)
        requires = predicates()
        if expected_state == 'unknown':
            requires.append(dict(kind='scientific_unit_consistency', file='predictions.csv', column='score'))
        result.append(dict(id=name, input_utf8=content.decode(), input_sha256=hashlib.sha256(content).hexdigest(),
            requires=requires, ensures=[dict(kind='file_exists', file='heldout_metrics.json')],
            expected_admission=expected_state, in_scope=in_scope, independent_reason=reason,
            oracle=oracle(rows) if in_scope is True else None))
    return result


def oracle(rows):
    """Separate frozen Decimal reference; never imports implementation functions."""
    values = [dict(zip(HEADER, row)) for row in rows]
    matrix = {(True, True): 0, (True, False): 0, (False, True): 0, (False, False): 0}
    for row in values:
        if row['split'] != 'test':
            continue
        actual = Decimal(row['label']) == Decimal(1)
        predicted = Decimal(row['score']) >= Decimal('0.5')
        matrix[actual, predicted] += 1
    return dict(n=sum(matrix.values()), tp=matrix[True, True], fn=matrix[True, False],
                fp=matrix[False, True], tn=matrix[False, False])


def independent_verdict(probe, output):
    if probe['in_scope'] is None:
        return dict(state='unknown', reason=probe['independent_reason'])
    if probe['in_scope'] is False:
        return dict(state='failed', reason='input violates frozen scientific scope; a metrics file is unsafe to certify')
    passed = (isinstance(output, dict) and set(output) == set(probe['oracle'])
        and all(type(output[k]) is int and output[k] == v for k, v in probe['oracle'].items()))
    return dict(state='passed' if passed else 'failed', reason='independent fixed-threshold integer confusion matrix',
                expected=probe['oracle'])


def _environment():
    return dict(python=platform.python_version(), implementation=platform.python_implementation(),
        platform=platform.system(), machine=platform.machine(),
        sandbox=os.environ.get('SKILLNET_SANDBOX', 'process'), model=None,
        model_calls=0, network_used=False)


def execute_arm(workspace, probe, implementation, arm, pre):
    directory = workspace / probe['id'] / implementation / arm
    directory.mkdir(parents=True, exist_ok=False)
    input_path = directory / 'predictions.csv'
    input_path.write_text(probe['input_utf8'], encoding='utf-8', newline='')
    assert hashlib.sha256(input_path.read_bytes()).hexdigest() == probe['input_sha256']
    allowed = arm == 'unconditional' or pre['state'] == 'passed'
    record = dict(probe=probe['id'], implementation=implementation, arm=arm,
        input_sha256=probe['input_sha256'], admission=pre['state'], allowed=allowed,
        code_sha256=hashlib.sha256(IMPLEMENTATIONS[implementation].encode()).hexdigest(),
        code_calls=0, executed=False, execution_ok=None, output=None, output_sha256=None,
        post=None, independent=None, duration_seconds=0)
    if not allowed:
        record['independent'] = dict(state='not_executed', reason='preconditions did not all pass; no code call')
        return record
    record['started_at_us'] = time.time_ns() // 1000
    run = sandbox.run_python(IMPLEMENTATIONS[implementation], timeout=10, keep_dir=True, workdir=directory)
    executed_code_sha = hashlib.sha256((directory/'main.py').read_bytes()).hexdigest()
    expected_code_sha = hashlib.sha256(IMPLEMENTATIONS[implementation].replace('\n', os.linesep).encode()).hexdigest()
    assert executed_code_sha == expected_code_sha
    record.update(code_calls=1, executed=True, execution_ok=run['ok'],
        returncode=run['returncode'], error_kind=run['error_kind'], stderr=run['stderr'][-800:],
        duration_seconds=run['duration'], finished_at_us=time.time_ns() // 1000,
        executed_code_sha256=executed_code_sha)
    output_path = directory / 'heldout_metrics.json'
    files = {'heldout_metrics.json': output_path} if output_path.is_file() else {}
    record['post'] = evaluate(probe['ensures'], files)
    if output_path.is_file():
        raw = output_path.read_bytes()
        record['output_sha256'] = hashlib.sha256(raw).hexdigest()
        try:
            record['output'] = json.loads(raw)
        except (UnicodeError, ValueError):
            pass
    record['independent'] = independent_verdict(probe, record['output'])
    return record


def summarize(records, probes):
    by_probe = {p['id']: p for p in probes}
    summary = {}
    for arm in ('unconditional', 'contract_gate'):
        rows = [r for r in records if r['arm'] == arm]
        summary[arm] = dict(
            attempts=len(rows), code_calls=sum(r['code_calls'] for r in rows),
            valid_tasks=sum(by_probe[r['probe']]['in_scope'] is True for r in rows),
            invalid_tasks=sum(by_probe[r['probe']]['in_scope'] is False for r in rows),
            scope_unknown_tasks=sum(by_probe[r['probe']]['in_scope'] is None for r in rows),
            blocked=sum(not r['allowed'] for r in rows),
            unknown_blocked=sum(not r['allowed'] and r['admission']=='unknown' for r in rows),
            valid_false_blocks=sum(not r['allowed'] and by_probe[r['probe']]['in_scope'] is True for r in rows),
            invalid_false_admissions=sum(r['allowed'] and by_probe[r['probe']]['in_scope'] is False for r in rows),
            invalid_inputs_executed=sum(r['executed'] and by_probe[r['probe']]['in_scope'] is False for r in rows),
            invalid_input_outputs=sum(r['output'] is not None and by_probe[r['probe']]['in_scope'] is False for r in rows),
            independent_passes=sum(r['independent']['state']=='passed' for r in rows),
            valid_output_failures=sum(r['executed'] and by_probe[r['probe']]['in_scope'] is True
                and r['independent']['state']=='failed' for r in rows),
            seconds=round(sum(r['duration_seconds'] for r in rows), 3))
    return summary


def behavioral_comparisons(records, probes):
    from itertools import combinations
    ids = [p['id'] for p in probes if p['in_scope'] is True]
    observed = {(r['implementation'], r['probe']): r for r in records
        if r['arm']=='unconditional' and r['executed'] and r['execution_ok'] and r['output'] is not None}
    rows = []
    for left, right in combinations(IMPLEMENTATIONS, 2):
        common = [p for p in ids if (left,p) in observed and (right,p) in observed]
        mismatches = [p for p in common if observed[left,p]['output'] != observed[right,p]['output']]
        complete = bool(ids) and len(common) == len(ids)
        rows.append(dict(left=left, right=right, planned_probes=ids, observed_probes=common,
            status='distinguished_by_counterexample' if mismatches else 'finite_probe_agreement' if complete else 'insufficient_evidence',
            counterexamples=mismatches,
            signatures={name:digest({p:observed[name,p]['output'] for p in common}) for name in (left,right)},
            boundary='Only observed valid synthetic probes; not universal equivalence or automatic deduplication'))
    return rows


def run_lab(output: Path, workspace: Path):
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=False)
    probes = fixtures()
    order = [(p['id'], name) for p in probes for name in IMPLEMENTATIONS]
    random.Random(SEED).shuffle(order)
    protocol = dict(version=VERSION, seed=SEED, contract_version=CONTRACT_VERSION,
        preregistered_at_us=time.time_ns() // 1000,
        purpose='gate intervention on reviewed implementations; no causal attribution to learned skills',
        environment=_environment(), implementations=IMPLEMENTATIONS, probes=probes,
        executed_code_sha256={name:hashlib.sha256(code.replace('\n', os.linesep).encode()).hexdigest()
                             for name,code in IMPLEMENTATIONS.items()},
        pair_order=[dict(probe=p, implementation=n,
            arms=['unconditional','contract_gate'] if i%2==0 else ['contract_gate','unconditional'])
            for i,(p,n) in enumerate(order)],
        oracle_sha256=hashlib.sha256(__import__('inspect').getsource(oracle).encode()).hexdigest(),
        contract_code_sha256=hashlib.sha256((ROOT/'skillnet'/'state_contracts.py').read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        claims_excluded=['general causal model','universal behavioral equivalence','minimal complete skill basis',
                         'LLM or skill-selection performance improvement','production reward eligibility'])
    frozen_sha = digest(protocol)
    frozen_path = workspace / 'preregistered-protocol.json'
    frozen_path.write_text(json.dumps(dict(protocol_sha256=frozen_sha, protocol=protocol),
        ensure_ascii=False, indent=2), encoding='utf-8')
    # Freeze to disk before the first implementation process is started.
    assert digest(json.loads(frozen_path.read_text(encoding='utf-8'))['protocol']) == frozen_sha
    rows, admissions = [], []
    by_id = {p['id']: p for p in probes}
    for pair in protocol['pair_order']:
        probe = by_id[pair['probe']]
        source_dir = workspace / 'observed_inputs' / probe['id']
        source_dir.mkdir(parents=True, exist_ok=True)
        source = source_dir / 'predictions.csv'
        source.write_text(probe['input_utf8'], encoding='utf-8', newline='')
        pre = evaluate(probe['requires'], {'predictions.csv':source})
        if not any(r['probe']==probe['id'] for r in admissions):
            admissions.append(dict(probe=probe['id'], expected=probe['expected_admission'],
                matched=pre['state']==probe['expected_admission'], result=pre))
        for arm in pair['arms']:
            rows.append(execute_arm(workspace, probe, pair['implementation'], arm, pre))
    assert all(r['started_at_us'] > protocol['preregistered_at_us']
               for r in rows if r['executed'])
    report = dict(version=VERSION, protocol_sha256=frozen_sha, protocol=protocol,
        admissions=admissions, records=rows, summary=summarize(rows, probes),
        behavioral_comparisons=behavioral_comparisons(rows, probes),
        reward_applied=False, production_library_modified=False,
        boundary='Synthetic reviewed-code experiment. Structural postconditions do not establish numerical correctness; independent oracle remains necessary.')
    report['report_sha256'] = digest(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs'/'evidence'/'capability-probes.json')
    parser.add_argument('--workspace', type=Path, default=ROOT/'.audit-tmp-upgrade'/f'capability-probes-{time.time_ns()}')
    args = parser.parse_args()
    report = run_lab(args.output.resolve(), args.workspace)
    print(json.dumps(dict(report_sha256=report['report_sha256'], output=str(args.output),
        admissions_matched=sum(a['matched'] for a in report['admissions']),
        admissions=len(report['admissions']), summary=report['summary'],
        behavioral_comparisons=report['behavioral_comparisons']), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
