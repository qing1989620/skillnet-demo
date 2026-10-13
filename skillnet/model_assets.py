"""Restore the pinned public encoder from the repository's offline bundle."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def restore_bundled_model(target: Path, root: Path = ROOT) -> dict:
    raw = (root / 'config/semantic_model.json').read_bytes()
    manifest = json.loads(raw)
    bundle = root / 'assets/semantic/multilingual-e5-small.zip'
    with zipfile.ZipFile(bundle) as archive:
        expected = manifest['files']
        if set(archive.namelist()) != set(expected) or len(archive.namelist()) != len(expected):
            raise ValueError('Encoder bundle file set mismatch')
        for name, info in expected.items():
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
                raise ValueError('Invalid encoder file path')
            if archive.getinfo(name).file_size != info['bytes']:
                raise ValueError('Encoder bundle file size mismatch: ' + name)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(destination.name + '.' + uuid.uuid4().hex + '.partial')
            try:
                sha = hashlib.sha256()
                with archive.open(name) as source, temporary.open('wb') as output:
                    while block := source.read(1024 * 1024):
                        sha.update(block)
                        output.write(block)
                if sha.hexdigest() != info['sha256']:
                    raise ValueError('Encoder bundle SHA mismatch: ' + name)
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
    # Commit readiness last. No published config or model hash is rewritten.
    temporary = target / ('manifest.' + uuid.uuid4().hex + '.partial')
    temporary.write_bytes(raw)
    temporary.replace(target / 'manifest.json')
    return manifest
