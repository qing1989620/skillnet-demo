"""Replaceable local multilingual ONNX encoder, with explicit lexical fallback."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import threading

from .index import VectorIndex

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = (0.70, 0.20, 0.10)
DENSE_WEIGHTS = (0.35, 0.55, 0.10)


class DenseIndex:
    def __init__(self, model_dir: Path):
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.np = np
        self.model_dir = model_dir
        self.manifest = json.loads((model_dir / 'manifest.json').read_text())
        for name, info in self.manifest['files'].items():
            if hashlib.sha256((model_dir / name).read_bytes()).hexdigest() != info['sha256']:
                raise ValueError('Semantic model integrity check failed: ' + name)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(model_dir / 'onnx/model_quantized.onnx'), sess_options=options,
                                           providers=['CPUExecutionProvider'])
        self.tokenizer = Tokenizer.from_file(str(model_dir / 'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=256)
        self.tokenizer.enable_padding()
        self.lock = threading.Lock()
        self.snapshot = ([], np.empty((0, 384), dtype=np.float32))
        self.status = dict(kind='dense-onnx', active=True, model=self.manifest['repository'],
                           revision=self.manifest['revision'], dimension=384, max_tokens=256)

    def embed(self, texts, prefix):
        np = self.np
        matrices = []
        with self.lock:
            for start in range(0, len(texts), 24):
                tokens = self.tokenizer.encode_batch([prefix + t for t in texts[start:start + 24]])
                arrays = dict(input_ids=np.array([t.ids for t in tokens], dtype=np.int64),
                              attention_mask=np.array([t.attention_mask for t in tokens], dtype=np.int64),
                              token_type_ids=np.array([t.type_ids for t in tokens], dtype=np.int64))
                output = self.session.run(None, {i.name: arrays[i.name] for i in self.session.get_inputs()})[0]
                mask = arrays['attention_mask'][..., None]
                pooled = (output * mask).sum(axis=1) / mask.sum(axis=1).clip(min=1)
                pooled /= np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-12)
                matrices.append(pooled.astype(np.float32))
        return np.concatenate(matrices) if matrices else np.empty((0, 384), dtype=np.float32)

    def fit(self, ids, texts):
        key = hashlib.sha256(json.dumps([self.status['revision'], self.status['max_tokens'], ids, texts], ensure_ascii=False).encode()).hexdigest()
        cache = ROOT / 'data/semantic-cache' / (key + '.npz')
        if cache.exists():
            with self.np.load(cache, allow_pickle=False) as data:
                matrix = data['embeddings']
        else:
            matrix = self.embed(texts, 'passage: ')
            cache.parent.mkdir(parents=True, exist_ok=True)
            temp = cache.with_name(key + '-' + str(os.getpid()) + '.tmp.npz')
            self.np.savez_compressed(temp, embeddings=matrix)
            os.replace(temp, cache)
        if matrix.shape != (len(ids), 384):
            raise ValueError('Semantic cache shape mismatch')
        self.snapshot = (list(ids), matrix)

    def search(self, query, top_k=20):
        ids, matrix = self.snapshot
        if not ids:
            return []
        scores = matrix @ self.embed([query], 'query: ')[0]
        order = self.np.argsort(-scores)[:top_k]
        return [(ids[i], round(float(scores[i]), 5)) for i in order]


def make_index():
    mode = os.environ.get('SKILLNET_ENCODER', 'auto')
    path = Path(os.environ.get('SKILLNET_ENCODER_DIR', str(ROOT / '.models/multilingual-e5-small')))
    if mode != 'lexical' and (path / 'manifest.json').exists():
        try:
            return DenseIndex(path)
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            if mode == 'dense':
                raise RuntimeError(f'Requested dense encoder unavailable: {exc}') from exc
            reason = str(exc)
    else:
        reason = '本地多语言模型未安装；运行 tools/setup_semantic_model.py' if mode != 'lexical' else '配置选择词法向量'
    if mode == 'dense':
        raise RuntimeError(reason)
    index = VectorIndex()
    index.status = dict(kind='lexical-hashing', active=True, degraded=True, reason=reason)
    return index
