"""Portable learned skill-network adapter. NumPy inference; training is optional.

The frozen text encoder supplies public document representations. These weights
learn task-to-skill relevance and typed-neighbour mixing, not execution success.
Unknown / unadmitted checkpoints are available only for explicit shadow previews.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import os
import tempfile
import zipfile
from typing import Any

import numpy as np

VERSION = 'skill-network-adapter-v1'
RELATIONS = ('depend_on', 'compose_with', 'similar_to', 'co_use')
DIMENSION = 384
RANK = 48


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def normalize(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-8)


def neighbour_features(features, ids, edges):
    """Directional typed means. co_use is observational, never a causal edge."""
    x = np.asarray(features, dtype=np.float32)
    by = {name: i for i, name in enumerate(ids)}
    out = np.zeros((len(ids), len(RELATIONS), x.shape[1]), dtype=np.float32)
    counts = np.zeros((len(ids), len(RELATIONS)), dtype=np.float32)
    seen = set()
    for edge in edges:
        source, target, relation = edge['source'], edge['target'], edge['type']
        if source not in by or target not in by or relation not in RELATIONS:
            continue
        key = source, target, relation
        if key in seen or source == target:
            continue
        seen.add(key)
        i, j, r = by[source], by[target], RELATIONS.index(relation)
        out[i, r] += x[j]
        counts[i, r] += 1
    return out / np.maximum(counts[..., None], 1)


class NetworkAdapter:
    def __init__(self, weights: dict[str, np.ndarray], metadata: dict[str, Any]):
        self.metadata = dict(metadata)
        expected = {'q_down': (DIMENSION, RANK), 'q_up': (RANK, DIMENSION),
            's_down': (DIMENSION, RANK), 's_up': (RANK, DIMENSION),
            'g_down': (DIMENSION, RANK), 'g_up': (RANK, DIMENSION),
            'relation_logits': (len(RELATIONS),)}
        if set(weights) != set(expected):
            raise ValueError('Unexpected learned network parameter names')
        self.weights = {}
        for name, shape in expected.items():
            a = np.asarray(weights[name], dtype=np.float32)
            if a.shape != shape or not np.isfinite(a).all():
                raise ValueError('Invalid network parameter: ' + name)
            self.weights[name] = a.copy()

    @classmethod
    def identity(cls, seed=17):
        rng = np.random.default_rng(seed)
        w = {}
        for side in ('q', 's', 'g'):
            w[side + '_down'] = rng.normal(0, .025, (DIMENSION, RANK)).astype(np.float32)
            w[side + '_up'] = np.zeros((RANK, DIMENSION), dtype=np.float32)
        w['relation_logits'] = np.zeros(len(RELATIONS), dtype=np.float32)
        return cls(w, {'version': VERSION, 'stage': 'identity'})

    @classmethod
    def load(cls, directory: Path):
        directory = Path(directory)
        meta_path, weight_path = directory / 'manifest.json', directory / 'model.npz'
        if meta_path.stat().st_size>65536:raise ValueError('Oversized network manifest')
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        if meta.get('version') != VERSION or weight_path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError('Unsupported / oversized network checkpoint')
        if hashlib.sha256(weight_path.read_bytes()).hexdigest() != meta.get('weights_sha256'):
            raise ValueError('Network checkpoint fingerprint mismatch')
        try:
            with zipfile.ZipFile(weight_path) as archive:
                if sum(i.file_size for i in archive.infolist()) > 2 * 1024 * 1024:
                    raise ValueError('Expanded network checkpoint exceeds its parameter budget')
        except zipfile.BadZipFile:raise ValueError('Invalid network weight archive') from None
        with np.load(weight_path, allow_pickle=False) as z:
            weights = {key: z[key] for key in z.files}
        return cls(weights, meta)

    def save(self, directory: Path, **metadata):
        directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(suffix='.npz', dir=directory)
        os.close(fd)
        try:
            np.savez_compressed(temp, **self.weights)
            weight_sha = hashlib.sha256(Path(temp).read_bytes()).hexdigest()
            os.replace(temp, directory / 'model.npz')
        finally:
            Path(temp).unlink(missing_ok=True)
        value = {**self.metadata, **metadata, 'version': VERSION,
            'weights_sha256': weight_sha, 'dimension': DIMENSION, 'rank': RANK,
            'trainable_parameters': sum(w.size for w in self.weights.values()),
            'score_kind': 'learned_relevance_not_success_probability',
            'model_id': 'network-' + weight_sha[:16]}
        manifest = directory / 'manifest.json'
        staged = manifest.with_suffix('.tmp')
        staged.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        os.replace(staged, manifest)
        self.metadata = value
        return value

    def query(self, features):
        x = np.asarray(features, dtype=np.float32)
        w = self.weights
        return normalize(x + .25 * (np.tanh(x @ w['q_down']) @ w['q_up']))

    def skills(self, features, neighbours=None, *, graph=True):
        x = np.asarray(features, dtype=np.float32)
        w = self.weights
        out = x + .25 * (np.tanh(x @ w['s_down']) @ w['s_up'])
        if graph and neighbours is not None:
            z = w['relation_logits'] - np.max(w['relation_logits'])
            a = np.exp(z); a /= a.sum()
            g = (np.asarray(neighbours) * a[None, :, None]).sum(axis=1)
            out += .15 * (np.tanh(g @ w['g_down']) @ w['g_up'])
        return normalize(out)

    def rank(self, query_features, skill_features, ids, neighbours=None, k=10):
        scores = self.skills(skill_features, neighbours) @ self.query(query_features).reshape(-1)
        order = np.argsort(-scores, kind='stable')[:k]
        return [{'name': ids[i], 'score': round(float(scores[i]), 6)} for i in order]
