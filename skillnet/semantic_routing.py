"""Small supervised intent router. Scores are not probabilities or utility.

This research candidate never replaces the production retriever. Its labels
describe requested effects, not a reward for the skills executing those effects.
"""
from __future__ import annotations
import hashlib
import json
import numpy as np

VERSION = 'semantic-intent-routing-v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def fit(embeddings, labels, alpha):
    x = np.asarray(embeddings, dtype=np.float64)
    y = np.eye(9)[np.asarray(labels, dtype=int)]
    if x.ndim != 2 or x.shape[1] != 384 or len(y) != len(x):
        raise ValueError('invalid training matrix')
    # Centering leaves the intercept unpenalized. No test inputs or labels.
    xm, ym = x.mean(axis=0), y.mean(axis=0)
    z = x - xm
    w = z.T @ np.linalg.solve(z @ z.T + alpha * np.eye(len(x)), y - ym)
    return {'version': VERSION, 'alpha': alpha, 'weights': w.tolist(),
            'intercept': (ym - xm @ w).tolist(), 'classes': list(range(9))}


def predict(model, embeddings):
    if model.get('version') != VERSION or model.get('classes') != list(range(9)):
        raise ValueError('unsupported router')
    w, b = np.asarray(model['weights']), np.asarray(model['intercept'])
    x = np.asarray(embeddings)
    if (w.shape != (384, 9) or b.shape != (9,) or x.ndim != 2 or x.shape[1] != 384
            or not all(np.isfinite(v).all() for v in (w, b, x))):
        raise ValueError('invalid numeric router')
    scores = x @ w + b
    return [{'label': int(np.argmax(s)), 'scores': s.tolist()} for s in scores]


def action(label):
    if type(label) is not int or not 0 <= label <= 8:
        raise ValueError('invalid label')
    return {'mask': None if label == 8 else label, 'reject': label == 8}


def parse_action(text):
    value = json.loads(text)
    if type(value) is not dict or set(value) != {'mask', 'reject'} or type(value['reject']) is not bool:
        raise ValueError('invalid action')
    if value['reject']:
        if value['mask'] is not None: raise ValueError('invalid rejection')
    elif type(value['mask']) is not int or not 0 <= value['mask'] <= 7:
        raise ValueError('invalid mask')
    return value
