"""Verify the published file set; no model, network or third-party packages."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'config/delivery-manifest.json'
RELEASE = 'config/delivery.json'
EXCLUDE = {MANIFEST, RELEASE, 'out/exec_log/executions.jsonl', 'out/verify_report.json'}
MUTABLE = {'data/library.json'}


def safe_path(root, name):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
        raise ValueError('Invalid delivery path')
    if (relative.name in {'.env', '.env.local'} or relative.suffix in {'.key', '.pem'}
            or any(p in {'.git', '.venv', '__pycache__', '.models'} or p.startswith(('.e_', '.audit-tmp'))
                   for p in relative.parts)):
        raise ValueError('Private or environment file is outside public delivery')
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Delivery path escapes project')
    return path


def digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False,
                                   separators=(',', ':')).encode()).hexdigest()


def write_manifest(root=ROOT):
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    rows = []
    for name in sorted(set(names) - EXCLUDE - {''}):
        path = safe_path(root, name)
        if not path.is_file(): raise ValueError('Missing tracked delivery file: ' + name)
        raw = path.read_bytes()
        rows.append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                     'mutable': name in MUTABLE})
    tree = digest(rows)
    manifest = {'schema_version': 1, 'release': '2026.10.14-complete.19',
                'source_tree_sha256': tree, 'files': rows}
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    safe_path(root, MANIFEST).write_bytes(raw)
    release = {'release': manifest['release'], 'expected_skills': 1881,
               'source_tree_sha256': tree, 'files': len(rows),
               'manifest_sha256': hashlib.sha256(raw).hexdigest()}
    safe_path(root, RELEASE).write_text(json.dumps(release, indent=2) + '\n', encoding='utf-8', newline='\n')
    return release


def verify(root=ROOT, strict_runtime=False):
    release = json.loads(safe_path(root, RELEASE).read_text(encoding='utf-8'))
    raw = safe_path(root, MANIFEST).read_bytes()
    if hashlib.sha256(raw).hexdigest() != release['manifest_sha256']:
        raise ValueError('Delivery manifest SHA mismatch')
    manifest = json.loads(raw)
    if digest(manifest['files']) != release['source_tree_sha256']:
        raise ValueError('Delivery file set SHA mismatch')
    bad = []; skipped = []; checked = 0; seen = set()
    for row in manifest['files']:
        name = row['path']
        if name in seen: raise ValueError('Duplicate delivery file')
        seen.add(name)
        path = safe_path(root, name)
        if name in MUTABLE and not strict_runtime:
            skipped.append(name); continue
        checked += 1
        if not path.is_file(): bad.append({'path': name, 'reason': 'missing'}); continue
        data = path.read_bytes()
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
            bad.append({'path': name, 'reason': 'changed'})
    return {'ok': not bad, 'release': release['release'], 'source_tree_sha256': release['source_tree_sha256'],
            'checked': checked, 'skipped_runtime': skipped, 'differences': bad}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Maintainer: freeze staged delivery files')
    parser.add_argument('--strict-runtime', action='store_true', help='Also check the initial runtime library snapshot')
    args = parser.parse_args()
    result = write_manifest() if args.write else verify(strict_runtime=args.strict_runtime)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get('ok') is False: raise SystemExit(1)


if __name__ == '__main__': main()
