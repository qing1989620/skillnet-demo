"""Independent reference for the explicitly scoped public CSV experiment.

This module does not import the implementations, planner or their predictions.
It verifies the task's original-cell and fixed-threshold requirements directly.
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
import stat
from decimal import Decimal, InvalidOperation
from pathlib import Path

VERSION = 'frontier-csv-oracle-v1'
HEADER = ['sample_id', 'subject_id', 'split', 'label', 'score']
METRICS = ['n', 'tp', 'tn', 'fp', 'fn', 'accuracy', 'precision', 'recall', 'f1']
MAX_BYTES = 1024 * 1024
MAX_ROWS = 50_000


def _snapshot(path: Path, limit: int = MAX_BYTES) -> bytes:
    """A bounded independent byte snapshot; no-follow and immutable-read checks."""
    path = Path(path).absolute()
    if any(item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction())
           for item in (path, *path.parents)):
        raise ValueError('reference does not follow linked paths')
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        raise ValueError('reference requires a bounded regular file')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError('reference input changed before snapshot')
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    if (len(raw) > limit or len(raw) != before.st_size
            or (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
        raise ValueError('reference input changed during snapshot or exceeded byte limit')
    return raw


def _read(path: Path):
    raw = _snapshot(path)
    reader = csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True)
    header = next(reader, None)
    if not header or len(header) != len(HEADER) or set(header) != set(HEADER):
        raise ValueError('reference requires the exact five-column schema')
    indices = [header.index(column) for column in HEADER]
    rows = []
    for row in reader:
        if len(row) != len(HEADER):
            raise ValueError('reference requires consistent five-column records')
        if len(rows) >= MAX_ROWS:
            raise ValueError('reference exceeds the row verification bound')
        # Canonical field order permits the same column-set contract as the
        # executor while preserving every original cell spelling and row order.
        rows.append([row[index] for index in indices])
    return raw, rows


def reference(source: Path):
    """Fixed task semantics: first-ID dedup, remove ALL leaking subjects, blank drop."""
    raw, rows = _read(source)
    seen = set()
    unique = []
    for row in rows:
        if row[0] not in seen:
            seen.add(row[0])
            unique.append(row)
    splits = {}
    for row in unique:
        splits.setdefault(row[1], set()).add(row[2])
    cleaned = [r for r in unique if len(splits[r[1]]) == 1 and r[4].strip()]
    if not cleaned:
        raise ValueError('no rows remain under the approved cleaning policy')
    for row in cleaned:
        score, label = Decimal(row[4].strip()), Decimal(row[3].strip())
        if (not score.is_finite() or not 0 <= score <= 1
                or not label.is_finite() or label not in (Decimal(0), Decimal(1))):
            raise ValueError('out-of-domain labels/scores cannot be silently repaired')
    heldout = [r for r in cleaned if r[2] == 'test']
    if not heldout:
        raise ValueError('no held-out test rows')
    counts = dict(n=len(heldout), tp=0, tn=0, fp=0, fn=0)
    # Arithmetic reference is separate from the registered executable source.
    for row in heldout:
        truth, prediction = Decimal(row[3].strip()) == Decimal(1), Decimal(row[4].strip()) >= Decimal('0.5')
        counts[{(True, True): 'tp', (True, False): 'fn',
                (False, True): 'fp', (False, False): 'tn'}[truth, prediction]] += 1
    def ratio(a, b):
        return Decimal(a) / Decimal(b) if b else Decimal(0)
    values = {k: Decimal(v) for k, v in counts.items()}
    values.update(accuracy=ratio(counts['tp'] + counts['tn'], counts['n']),
                  precision=ratio(counts['tp'], counts['tp'] + counts['fp']),
                  recall=ratio(counts['tp'], counts['tp'] + counts['fn']),
                  f1=ratio(2 * counts['tp'], 2 * counts['tp'] + counts['fp'] + counts['fn']))
    return raw, cleaned, values


def evaluate(source: Path, final_data: Path, metrics: Path | None) -> dict:
    report = {'version': VERSION, 'state': 'unknown', 'checks': [],
              'scope': 'public synthetic CSV / first-ID dedup / all-subject leakage exclusion / blank-score drop / test split / threshold >= 0.5'}
    try:
        raw, expected_rows, expected = reference(source)
        report['input_sha256'] = hashlib.sha256(raw).hexdigest()
        final_raw, actual_rows = _read(final_data)
        report['data_sha256'] = hashlib.sha256(final_raw).hexdigest()
        checks = report['checks']
        checks.append({'id': 'original_cells_and_policy', 'passed': actual_rows == expected_rows,
                       'expected_rows': len(expected_rows), 'actual_rows': len(actual_rows)})
        if metrics is None:
            report['reason'] = 'metrics were not produced'
            return report
        metric_raw = _snapshot(metrics, 65536)
        report['metrics_sha256'] = hashlib.sha256(metric_raw).hexdigest()
        table = list(csv.reader(io.StringIO(metric_raw.decode('utf-8-sig'), newline=''), strict=True))
        shape = (bool(table) and table[0] == ['metric', 'value'] and len(table) == 10
                 and all(len(r) == 2 for r in table[1:])
                 and {r[0] for r in table[1:]} == set(METRICS))
        checks.append({'id': 'metric_schema', 'passed': shape})
        actual = {}
        if shape:
            for key, text in table[1:]:
                try:
                    value = Decimal(text) if len(text) <= 128 else None
                    upper = MAX_ROWS if key in ('n', 'tp', 'tn', 'fp', 'fn') else 1
                    actual[key] = value if value is not None and value.is_finite() and 0 <= value <= upper else None
                except (InvalidOperation, ValueError):
                    actual[key] = None
        for key in METRICS:
            value = actual.get(key)
            valid = value is not None and value.is_finite()
            checks.append({'id': key, 'passed': bool(valid and abs(value - expected[key]) <= Decimal('1e-12')),
                           'expected': str(expected[key]), 'actual': str(value) if value is not None else None})
        report['state'] = 'passed' if all(c['passed'] for c in checks) else 'failed'
    except (OSError, UnicodeError, csv.Error, ValueError, InvalidOperation) as exc:
        report['reason'] = str(exc)
    return report
