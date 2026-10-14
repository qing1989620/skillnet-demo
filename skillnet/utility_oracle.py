"""Independent task semantics for the bounded conditional-utility study.

No imports from the executor, learner, or predictor. Compares original cells,
row policy and every numeric field, rather than grading an LLM explanation.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import io
from pathlib import Path

VERSION = 'conditional-tabular-oracle-v1'
HEADER = ['sample_id', 'subject_id', 'split', 'group', 'value']
KEYS = ('deduplicate', 'exclude_cross_split', 'drop_missing')


def read(raw: bytes) -> list[list[str]]:
    if len(raw) > 1048576:
        raise ValueError('reference byte limit')
    table = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True))
    if not table or table[0] != HEADER or len(table) > 5001 or any(len(r) != 5 for r in table):
        raise ValueError('reference schema/row limit')
    return table[1:]


def reference(raw: bytes, intent: dict) -> tuple[list, dict]:
    if (set(intent) != {*KEYS, 'goal'} or intent['goal'] != 'group_mean'
            or any(type(intent[k]) is not bool for k in KEYS)):
        raise ValueError('unsupported task contract')
    source = read(raw)
    # Independent index-based implementation. Operations have a frozen order.
    selected = list(range(len(source)))
    if intent['deduplicate']:
        first = {}
        for i, row in enumerate(source):
            first.setdefault(row[0], i)
        selected = sorted(first.values())
    if intent['exclude_cross_split']:
        entities = {source[i][1] for i in selected}
        bad = {entity for entity in entities
               if len({source[i][2] for i in selected if source[i][1] == entity}) > 1}
        selected = [i for i in selected if source[i][1] not in bad]
    if intent['drop_missing']:
        selected = [i for i in selected if source[i][4].strip() != '']
    rows = [source[i] for i in selected]
    labels = sorted({r[3] for r in rows if r[2] == 'test'})
    if not labels:
        raise ValueError('reference has no test groups')
    stats = {}
    with localcontext() as ctx:
        ctx.prec = 48
        for label in labels:
            cells = [r[4] for r in rows if r[2] == 'test' and r[3] == label]
            numbers = []
            for text in cells:
                if text.strip():
                    try:
                        v = Decimal(text.strip())
                    except InvalidOperation:
                        raise ValueError('reference rejects nonnumeric input') from None
                    if not v.is_finite() or abs(v) > Decimal('1e12'):
                        raise ValueError('reference rejects nonfinite input')
                    numbers.append(v)
            if not numbers:
                raise ValueError('reference group has no numeric values')
            total = sum(numbers, Decimal(0))
            stats[label] = [Decimal(len(cells)), Decimal(len(numbers)), total, total / len(numbers)]
    return rows, stats


def evaluate(raw: bytes, intent: dict, workspace: Path | None) -> dict:
    report = {'version': VERSION, 'input_sha256': hashlib.sha256(raw).hexdigest(),
              'deliverable': False, 'reference_valid': False, 'state': 'unknown', 'checks': []}
    try:
        expected_rows, expected_stats = reference(raw, intent)
        report['reference_valid'] = True
    except (ValueError, UnicodeError, csv.Error, InvalidOperation) as exc:
        report['reason'] = str(exc)
        return report
    if workspace is None:
        report['state'] = 'not_executed'
        return report
    try:
        data = (workspace / 'output.csv').read_bytes()
        summary = (workspace / 'summary.csv').read_bytes()
        if len(data) > 1048576 or len(summary) > 65536:
            raise ValueError('reference output size limit')
        table = list(csv.reader(io.StringIO(summary.decode('utf-8-sig'), newline=''), strict=True))
        schema = (bool(table) and table[0] == ['group','n_rows','n_numeric','sum','mean']
                  and len(table) == len(expected_stats) + 1 and all(len(r) == 5 for r in table))
        checks = [dict(id='original_cells_and_policy', passed=read(data) == expected_rows),
                  dict(id='summary_schema', passed=schema)]
        seen = set()
        for row in table[1:] if schema else []:
            valid = row[0] in expected_stats and row[0] not in seen
            seen.add(row[0])
            for actual, expected in zip(row[1:], expected_stats.get(row[0], [0] * 4)):
                v = Decimal(actual) if len(actual) < 128 else Decimal('NaN')
                valid = valid and v.is_finite() and abs(v - expected) <= Decimal('1e-12') * max(1, abs(expected))
            checks.append(dict(id='numeric_group_' + row[0], passed=bool(valid)))
        report.update(checks=checks, deliverable=all(c['passed'] for c in checks),
                      output_sha256=hashlib.sha256(data).hexdigest(),
                      summary_sha256=hashlib.sha256(summary).hexdigest())
        report['state'] = 'passed' if report['deliverable'] else 'failed'
    except (OSError, ValueError, UnicodeError, csv.Error, InvalidOperation) as exc:
        report.update(state='failed', reason=str(exc))
    return report
