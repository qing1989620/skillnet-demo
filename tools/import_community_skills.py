"""Reproducible, non-executing import of pinned, attributed skill packages.

Run acquire_skill_sources.py first. Archives are read as data; no extractall,
symlinks, installers or upstream Python modules are executed.
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
import tarfile
import gzip
import shutil
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.audit-tmp-upgrade/sources'
DEST = ROOT / 'seed/community'
ALLOWED = ('MIT', 'Apache-2.0', 'BSD-3-Clause', 'BSD-2-Clause', 'CC0-1.0', 'MIT-0')
DOMAINS = {
    '数据分析': ('data', 'analytics', 'pandas', 'statistics', 'sql', 'spreadsheet'),
    '生命科学': ('biology', 'bioinformatics', 'genomics', 'genome', 'protein', 'molecular', 'clinical', 'medical', 'drug', 'health', 'biomedical'),
    '科研方法': ('scientific', 'research', 'paper', 'academic', 'physics', 'chemistry'),
    '产品与设计': ('design', 'ux', 'ui', 'product', 'figma', 'frontend', 'accessibility'),
    '工程与运维': ('devops', 'docker', 'kubernetes', 'backend', 'security', 'testing', 'api'),
    '业务与运营': ('business', 'marketing', 'sales', 'finance', 'strategy', 'hr', 'content'),
    '人工智能': ('agent', 'llm', 'ai', 'machine-learning', 'model', 'rag', 'prompt'),
}


def classify(name: str, description: str, original_path: str = '') -> str:
    # Whole terms: "ui" must not classify "build" as product design.
    def score(text, terms):
        return sum(bool(re.search(r'(?<![a-z0-9])' + re.escape(w) + r'(?![a-z0-9])', text.lower())) for w in terms)
    scores = {d: 4 * score(name, terms) + 2 * score(original_path, terms) + score(description, terms)
              for d, terms in DOMAINS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else '工程与运维'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def permitted(value: str) -> str | None:
    value = value.strip().strip('"\'')
    return next((lic for lic in sorted(ALLOWED, key=len, reverse=True)
                 if value.lower() in (lic.lower(), lic.lower() + ' license')), None)


def main() -> None:
    pins = json.loads((SOURCE / 'pinned.json').read_text(encoding='utf-8'))
    pins.sort(key=lambda p: ('scientific', 'claude', 'agentic').index(p['alias']))
    DEST.mkdir(parents=True, exist_ok=True)
    catalog, seen, skipped = [], set(), collections.Counter()
    notices = ['# Third-party skill packages', '',
               'Imported as reference data. Repository stars are not per-skill quality ratings.',
               'The importer treats upstream scripts as reference data. Project test discovery excludes these packages.',
               'Import does not certify execution; verification is tracked separately.', '']
    for pin in pins:
        archive = SOURCE / (pin['alias'] + '.tar.gz')
        if digest(archive.read_bytes()) != pin['archive_sha256']:
            raise ValueError('Archive hash mismatch: ' + pin['repository'])
        unpacked = archive.with_suffix('')
        if not unpacked.exists():
            print(f"Preparing seekable {pin['alias']} archive", flush=True)
            with gzip.open(archive, 'rb') as src, unpacked.open('wb') as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
        with tarfile.open(unpacked) as tar:
            members = {m.name: m for m in tar.getmembers() if m.isfile() and
                       not m.issym() and not m.islnk() and '..' not in PurePosixPath(m.name).parts}
            top = next(iter(members)).split('/')[0]
            root_licenses = [m for n, m in members.items() if n.rsplit('/', 1)[0] == top
                             and n.split('/')[-1].lower().startswith(('license', 'notice'))]
            for m in root_licenses:
                out = DEST / 'licenses' / pin['alias'] / PurePosixPath(m.name).name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(tar.extractfile(m).read())
            notices += [f"## {pin['repository']}", '',
                        f"Source: {pin['url']} / commit `{pin['commit']}` / "
                        f"{pin['stars']:,} repository stars checked {pin['checked_at']}.",
                        f"Root license: {pin['license']}; package overrides are recorded in catalog.json.", '']
            skills = sorted(n for n in members if n.endswith('/SKILL.md') and '/plugins/' not in n
                            and not any(x.startswith('.') for x in n.split('/')[1:]))
            for name in skills:
                raw = tar.extractfile(members[name]).read()
                text = raw.decode('utf-8-sig', 'replace').replace('\r\n', '\n')
                try:
                    match = re.match(r'\A---\s*\n(.*?)\n---\s*\n(.*)', text, re.S)
                    fm = yaml.safe_load(match[1]) if match else {}
                    body = match[2].strip() if match else text.strip()
                    if not isinstance(fm, dict):
                        raise ValueError('frontmatter must be mapping')
                except (yaml.YAMLError, ValueError):
                    skipped['invalid_frontmatter'] += 1
                    continue
                license_value = str(fm.get('license', pin['license']))
                # Source annotations can override a missing license (e.g. Apache originals).
                if 'license' not in fm:
                    annotated = re.search(r'\(([^()]+)\)', str(fm.get('source', '')))
                    if annotated and permitted(annotated[1]):
                        license_value = annotated[1]
                license_id = permitted(license_value)
                if not license_id:
                    skipped['unconfirmed_or_restricted_license'] += 1
                    continue
                if str(fm.get('risk', '')).lower() in ('offensive', 'critical', 'unsafe'):
                    skipped['unsafe_reference'] += 1
                    continue
                key = digest(re.sub(r'\s+', ' ', body).strip().encode())
                if key in seen or len(body) < 200:
                    skipped['duplicate_or_empty'] += 1
                    continue
                folder = name.rsplit('/', 1)[0] + '/'
                files = [m for n, m in members.items() if n.startswith(folder)
                         and not any(x.startswith('.') for x in n[len(folder):].split('/'))]
                package_licenses = [m for m in files if PurePosixPath(m.name).name.lower().startswith('license')]
                restricted = False
                for m in package_licenses:
                    license_text = tar.extractfile(m).read(4000).decode('utf-8', 'replace').lower()
                    if any(term in license_text for term in ('polyform', 'noncommercial', 'non-commercial',
                           'all rights reserved', 'gnu general public license', 'gnu affero', 'proprietary')) and not (
                           'permission is hereby granted, free of charge' in license_text or 'apache license' in license_text):
                        restricted = True
                if restricted:
                    skipped['restricted_package_license'] += 1
                    continue
                if any(m.size > 2_000_000 for m in files) or sum(m.size for m in files) > 5_000_000:
                    skipped['oversized_package'] += 1
                    continue
                slug = re.sub(r'[^a-z0-9]+', '-', str(fm.get('name') or folder.split('/')[-2]).lower()).strip('-')
                slug = f"gh-{pin['alias']}-{slug[:43].rstrip('-')}-{key[:6]}"
                package = DEST / 'skills' / slug
                for m in files:
                    rel = PurePosixPath(m.name[len(folder):])
                    target = package.joinpath(*rel.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(tar.extractfile(m).read())
                # Preserve any intermediate directory license alongside the package.
                license_files = []
                for parent in PurePosixPath(folder.rstrip('/')).parents:
                    if str(parent) == '.':
                        continue
                    for n, m in members.items():
                        if n.rsplit('/', 1)[0] == str(parent) and PurePosixPath(n).name.lower().startswith(('license', 'notice')):
                            destination = package / 'attribution' / (digest(n.encode())[:6] + '-' + PurePosixPath(n).name)
                            destination.parent.mkdir(exist_ok=True)
                            destination.write_bytes(tar.extractfile(m).read())
                            license_files.append(str(destination.relative_to(ROOT)).replace('\\', '/'))
                domain = classify(str(fm.get('name', '')), str(fm.get('description', '')), name)
                headings = re.findall(r'^#{1,3}\s+(.+)', body, re.M)
                row = dict(name=slug, description=str(fm.get('description') or (headings[0] if headings else slug))[:1024],
                           domain=domain, tags=[domain, pin['alias'], '社区技能'], capability=str(fm.get('description', ''))[:1024],
                           steps=headings[:10], source='github', license=license_id,
                           compatibility=str(fm.get('compatibility', '参见原始技能与配套资源；导入未经执行验证'))[:500],
                           metadata=dict(repository=pin['repository'], commit=pin['commit'],
                               stars=str(pin['stars']), checked_at=pin['checked_at'], original_path=name[len(top)+1:],
                               source_url=f"{pin['url']}/blob/{pin['commit']}/{name[len(top)+1:]}",
                               package_path=str(package.relative_to(ROOT)).replace('\\', '/'),
                               content_sha256=digest(raw), body_sha256=key, resource_count=str(len(files)),
                               import_status='indexed-reference', execution_verified='false',
                               attribution_files=json.dumps(license_files)))
                catalog.append(row)
                seen.add(key)
        print(f"{pin['alias']}: {len(catalog)} unique packages imported", flush=True)
    if len(catalog) < 1000:
        raise ValueError(f'Only {len(catalog)} unique permitted packages; minimum is 1000')
    # Similarity is explicitly inferred, never a fabricated execution dependency.
    groups = collections.defaultdict(list)
    for row in catalog:
        groups[row['domain']].append(row)
    for rows in groups.values():
        tokens = [set(re.findall(r'[a-z]{3,}', r['name'] + ' ' + r['description'].lower())) -
                  {'the', 'and', 'for', 'with', 'skill', 'this', 'github', 'claude', 'agentic', 'scientific'} for r in rows]
        for i, row in enumerate(rows):
            scores = [(len(tokens[i] & t) / max(1, len(tokens[i] | t)), j) for j, t in enumerate(tokens) if j != i]
            row['relations'] = [['similar_to', rows[j]['name']] for score, j in sorted(scores, reverse=True)[:2] if score >= .12]
            row['metadata']['relation_origin'] = 'inferred lexical similarity; not execution dependency'
    (DEST / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    report = dict(imported=len(catalog), unique_bodies=len(seen), sources=pins,
                  skipped=dict(skipped), domains={k: len(v) for k, v in groups.items()},
                  execution_verified=0, relation_semantics='inferred similar_to only')
    (ROOT / 'config/skill_sources.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'THIRD_PARTY_NOTICES.md').write_text('\n'.join(notices), encoding='utf-8')
    print(json.dumps(report | {'sources': len(pins)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
