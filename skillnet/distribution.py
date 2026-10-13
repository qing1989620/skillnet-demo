"""Public build identity, independent of credentials and mutable run data."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def build_identity(root: Path = ROOT) -> dict:
    try:
        release = json.loads((root / 'config/delivery.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        release = {}
    commit = None
    if (root / '.git').exists():
        try:
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root,
                stderr=subprocess.DEVNULL, timeout=2).decode().strip()
        except (OSError, subprocess.SubprocessError):
            pass
    backend = root / 'server.py'
    return {'release': release.get('release', 'development'), 'git_commit': commit,
            'source_tree_sha256': release.get('source_tree_sha256'),
            'backend_sha256': hashlib.sha256(backend.read_bytes()).hexdigest() if backend.exists() else None,
            'expected_skills': release.get('expected_skills'),
            'repository': 'https://github.com/qing1989620/skillnet-demo'}
