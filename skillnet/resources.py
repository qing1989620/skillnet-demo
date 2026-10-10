"""Pinned, read-only community resources. Bytes are data, never imported/executed."""
from __future__ import annotations
from functools import lru_cache
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from .evidence import digest

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'skillnet-package-v1'
MAX_FILE_BYTES = 2_000_000


class ResourceIntegrityError(ValueError):
    pass


def resource_path(value):
    if (not isinstance(value,str) or not value or len(value)>400 or '\\' in value
        or ':' in value or re.search(r'[\x00-\x1f\x7f]',value)
        or any(not part or part.startswith('.') for part in value.split('/'))
        or PurePosixPath(value).is_absolute()):
        raise ValueError('Invalid resource path')
    return value


@lru_cache(maxsize=1)
def _snapshots():
    return json.loads((ROOT/'seed/community/packages.json').read_text(encoding='utf-8'))


def package_manifest(skill):
    if skill.source != 'github':
        raise FileNotFoundError('This skill has no community resource package')
    record = _snapshots().get(skill.name)
    if not record:
        raise FileNotFoundError('Skill resource snapshot is unavailable')
    if (record['package_path'] != skill.metadata.get('package_path')
        or record['skill_md_sha256'] != skill.metadata.get('content_sha256')):
        raise ResourceIntegrityError('Skill metadata does not match the registered package')
    return json.loads(json.dumps(record))


def read_resource(skill, path):
    path = resource_path(path)
    record = package_manifest(skill)
    registered = next((f for f in record['files'] if f['path']==path), None)
    if registered is None:
        raise FileNotFoundError('Resource is not in the registered package')
    base = (ROOT/'seed/community/skills').resolve()
    package = (ROOT/record['package_path']).resolve()
    target = (package/path).resolve()
    if not package.is_relative_to(base) or not target.is_relative_to(package) or not target.is_file():
        raise FileNotFoundError('Resource is outside the package or unavailable')
    if target.stat().st_size > MAX_FILE_BYTES:
        raise ResourceIntegrityError('Resource exceeds the delivery size limit')
    with target.open('rb') as stream:
        raw = stream.read(MAX_FILE_BYTES+1)
    if len(raw)!=registered['bytes'] or hashlib.sha256(raw).hexdigest()!=registered['sha256']:
        raise ResourceIntegrityError('Resource no longer matches the delivery snapshot')
    return raw


def build_snapshots(root=ROOT):
    records = {}
    base=(root/'seed/community/skills').resolve()
    for row in json.loads((root/'seed/community/catalog.json').read_text(encoding='utf-8')):
        meta=row['metadata']
        package=(root/meta['package_path']).resolve()
        if not package.is_relative_to(base):raise ValueError('Package outside community root')
        files=[]
        for target in sorted(package.rglob('*')):
            relative=target.relative_to(package)
            if (any(part=='__pycache__' or part.startswith('.') for part in relative.parts)
                or target.suffix in {'.pyc','.pyo'}):
                continue
            if not target.is_file():continue
            if target.is_symlink() or not target.resolve().is_relative_to(package):
                raise ValueError('Linked resource is not supported')
            name=resource_path(relative.as_posix())
            if target.stat().st_size>MAX_FILE_BYTES:raise ValueError('Oversized resource')
            raw=target.read_bytes()
            files.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        skill_md=next(f for f in files if f['path']=='SKILL.md')
        if skill_md['sha256']!=meta['content_sha256']:raise ValueError('Skill source digest mismatch')
        record=dict(version=VERSION,name=row['name'],package_path=meta['package_path'],
            skill_md_sha256=meta['content_sha256'],repository=meta['repository'],commit=meta['commit'],
            source_url=meta['source_url'],license=row['license'],files=files,
            bytes=sum(f['bytes'] for f in files),execution_verified=False,
            verification='delivery_snapshot; each resource rehashed on read',
            usage='Read only; the host authorizes dependencies and execution separately')
        record['package_sha256']=digest(record)
        records[row['name']]=record
    return records
