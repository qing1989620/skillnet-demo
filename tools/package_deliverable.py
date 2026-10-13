"""Package the verified file manifest, including backend, assets and evidence."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import zipfile
from verify_delivery import ROOT, MANIFEST, RELEASE, safe_path, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT.parent / 'SkillNet-S1-Demo.zip')
    args = parser.parse_args()
    result = verify(strict_runtime=True)
    if not result['ok']:
        raise SystemExit('Delivery changed; inspect verify_delivery.py before packaging')
    manifest = json.loads((ROOT / MANIFEST).read_text(encoding='utf-8'))
    names = [row['path'] for row in manifest['files']] + [MANIFEST, RELEASE]
    destination = args.output.resolve()
    if destination == ROOT or destination in [safe_path(ROOT, n) for n in names]:
        raise SystemExit('Output must not overwrite a delivery file')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in names:
            archive.write(safe_path(ROOT, name), 'skillnet-demo/' + name)
    print(json.dumps({'output': str(destination), 'files': len(names), 'bytes': destination.stat().st_size,
                      'release': result['release'], 'source_tree_sha256': result['source_tree_sha256']},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
