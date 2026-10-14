"""Interpretable outcome prediction from paired, executed tabular interventions.

This finite experimental model is NOT a universal skill reward model. It never
writes library weights, grants points, or interprets missing evidence as success.
Only pre-execution facts and the explicit task contract enter its features.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

VERSION = 'conditional-utility-v1'
KEYS = ('deduplicate', 'exclude_cross_split', 'drop_missing')
FEATURES = ('want_dedup', 'want_disjoint', 'want_drop_missing', 'has_duplicate',
            'has_cross_split', 'has_missing', 'has_bad_test_number', 'has_test',
            'all_test_blank', 'schema_ok')
MAX_MODEL_BYTES = 512 * 1024


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def features(raw: bytes, intent: dict) -> dict:
    if (type(intent) is not dict or set(intent) != {*KEYS, 'goal'}
            or any(type(intent.get(k)) is not bool for k in KEYS)):
        raise ValueError('invalid bounded task contract')
    vector = [int(intent[k]) for k in KEYS] + [0] * 7
    supported_goal = intent['goal'] == 'group_mean'
    counts = {'rows': 0, 'test_rows': 0, 'bad_test_numbers': 0}
    try:
        if len(raw) > 1048576:
            raise ValueError('byte limit')
        table = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True))
        if (not table or table[0] != ['sample_id','subject_id','split','group','value']
                or len(table) > 5001 or any(len(r) != 5 for r in table)):
            raise ValueError('schema')
        rows = table[1:]
        groups = {}
        for row in rows:
            groups.setdefault(row[1], set()).add(row[2])
        test = [r for r in rows if r[2] == 'test']
        bad = 0
        for row in test:
            if row[4].strip():
                try:
                    number = Decimal(row[4].strip())
                    bad += int(not number.is_finite() or abs(number) > Decimal('1e12'))
                except InvalidOperation:
                    bad += 1
        vector[3:] = [int(len({r[0] for r in rows}) < len(rows)),
                      int(any(len(v) > 1 for v in groups.values())),
                      int(any(not r[4].strip() for r in rows)), int(bad > 0),
                      int(bool(test)), int(bool(test) and all(not r[4].strip() for r in test)), 1]
        counts.update(rows=len(rows), test_rows=len(test), bad_test_numbers=bad)
    except (ValueError, UnicodeError, csv.Error):
        pass
    return {'version': VERSION, 'input_sha256': hashlib.sha256(raw).hexdigest(),
            'contract_sha256': digest(intent), 'features': dict(zip(FEATURES, vector)),
            'vector': vector, 'counts': counts, 'supported_contract': supported_goal and bool(vector[-1])}


def fit_tree(x: np.ndarray, y: np.ndarray, *, depth: int = 8, min_leaf: int = 2) -> dict:
    """Fixed binary-feature CART; no task ID, data-source ID or test labels."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if x.ndim != 2 or x.shape[1] != len(FEATURES) or y.shape != (len(x), 16) or len(x) < 4:
        raise ValueError('invalid training matrices')
    if not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isin(x, [0,1]).all():
        raise ValueError('invalid training values')

    def build(ids: np.ndarray, remaining: int) -> dict:
        values = y[ids]
        node = {'n': int(len(ids)), 'value': values.mean(axis=0).tolist()}
        error = float(((values - values.mean(axis=0)) ** 2).sum())
        if remaining == 0 or error < 1e-12:
            return node
        best = None
        for j in range(x.shape[1]):
            left, right = ids[x[ids,j] < .5], ids[x[ids,j] >= .5]
            if min(len(left), len(right)) < min_leaf:
                continue
            loss = sum(float(((y[a] - y[a].mean(axis=0)) ** 2).sum()) for a in (left,right))
            if loss < error - 1e-12 and (best is None or loss < best[0] - 1e-12):
                best = (loss,j,left,right)
        if best is not None:
            _, j, left, right = best
            node.update(feature=FEATURES[j], left=build(left,remaining-1), right=build(right,remaining-1))
        return node

    return {'version': VERSION, 'features': list(FEATURES), 'tree': build(np.arange(len(x)),depth),
            'support': sorted({tuple(int(v) for v in row) for row in x}),
            'depth_limit': depth, 'min_leaf': min_leaf, 'training_tasks': len(x),
            'scope': 'reviewed three-bit tabular programs / explicit group-mean contracts',
            'formal_routing_deployed': False, 'reward_applied': False}


def validate_model(model: dict) -> None:
    if (model.get('version') != VERSION or model.get('features') != list(FEATURES)
            or type(model.get('support')) is not list or not 1 <= len(model['support']) <= 2048):
        raise ValueError('invalid model metadata')
    for vector in model['support']:
        if len(vector) != len(FEATURES) or any(type(v) is not int or v not in (0,1) for v in vector):
            raise ValueError('invalid support')
    nodes = 0
    def visit(node, depth):
        nonlocal nodes
        nodes += 1
        if (nodes > 1023 or depth > 10 or type(node) is not dict or type(node.get('n')) is not int
                or not 1 <= node['n'] <= 100000):
            raise ValueError('invalid tree shape')
        values = node.get('value')
        if (type(values) is not list or len(values) != 16
                or any(type(v) not in (float,int) or not math.isfinite(v) or not 0 <= v <= 1 for v in values)):
            raise ValueError('invalid outcomes')
        if 'feature' in node:
            if node['feature'] not in FEATURES:
                raise ValueError('invalid feature')
            visit(node.get('left'), depth+1); visit(node.get('right'), depth+1)
    visit(model.get('tree'),0)


def predict(model: dict, observed: dict, *, minimum_quality: float = .75) -> dict:
    validate_model(model)
    vector = observed['vector']
    node, path = model['tree'], []
    while 'feature' in node:
        name = node['feature']; present = bool(vector[FEATURES.index(name)])
        path.append({'condition': name, 'observed': present})
        node = node['right' if present else 'left']
    scores, failures = node['value'][:8], node['value'][8:]
    mask = max(range(8), key=lambda m: (scores[m], -m.bit_count(), -m))
    supported = (observed['supported_contract'] and tuple(vector) in {tuple(s) for s in model['support']})
    abstain = not supported or scores[mask] < minimum_quality or failures[mask] > .25
    marginal = []
    for bit, name in enumerate(KEYS):
        pairs = [(m,m | (1 << bit)) for m in range(8) if not m & (1 << bit)]
        delta = sum(scores[b] - scores[a] for a,b in pairs) / len(pairs)
        marginal.append({'skill': name, 'predicted_marginal_gain': delta,
                         'meaning': 'averaged over four fixed co-skill masks; not universal causal credit'})
    return {'version': VERSION, 'model_sha256': digest(model), 'observed': observed,
            'proposed_mask': mask, 'mask': None if abstain else mask, 'abstain': abstain,
            'reason': 'outside_training_support' if not supported else 'predicted_failure_or_low_quality' if abstain else 'within_finite_training_support',
            'predicted_quality': scores[mask], 'predicted_execution_failure': failures[mask],
            'predicted_gain_vs_all_skills': scores[mask]-scores[7],
            'mask_quality': scores, 'mask_execution_failure': failures,
            'marginal': marginal, 'conditions': path, 'training_leaf_tasks': node['n'],
            'uncertainty': 'empirical leaf means; not calibrated probabilities or confidence certificates',
            'formal_routing_deployed': False, 'reward_applied': False}


def load_model(path: Path) -> dict:
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_MODEL_BYTES + 1)
    if len(raw) > MAX_MODEL_BYTES:
        raise ValueError('model exceeds byte limit')
    result = json.loads(raw)
    validate_model(result)
    return result
