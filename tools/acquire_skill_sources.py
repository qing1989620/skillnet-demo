"""Download pinned public skill archives as data; never execute upstream code."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / '.audit-tmp-upgrade' / 'sources'
SOURCES = (
    ('agentic', 'sickn33/agentic-awesome-skills'),
    ('claude', 'alirezarezvani/claude-skills'),
    ('scientific', 'K-Dense-AI/scientific-agent-skills'),
)


def github(path: str) -> dict:
    result = subprocess.run(['gh', 'api', path], capture_output=True, text=True,
                            encoding='utf-8', check=True, timeout=60)
    return json.loads(result.stdout)


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = []
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        for alias, repository in SOURCES:
            meta = github('repos/' + repository)
            if meta['stargazers_count'] < 1000 or meta.get('license', {}).get('spdx_id') != 'MIT':
                raise ValueError('Source does not meet import criteria: ' + repository)
            commit = github(f"repos/{meta['full_name']}/commits/{meta['default_branch']}")['sha']
            target = DEST / (alias + '.tar.gz')
            url = f"https://codeload.github.com/{meta['full_name']}/tar.gz/{commit}"
            print(f"Downloading {meta['full_name']} @ {commit[:12]}", flush=True)
            with client.stream('GET', url) as response:
                response.raise_for_status()
                size = 0
                with target.open('wb') as stream:
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 350_000_000:
                            raise ValueError('Archive exceeds 350 MB limit')
                        stream.write(chunk)
            row = dict(alias=alias, repository=meta['full_name'], stars=meta['stargazers_count'],
                       license=meta['license']['spdx_id'], commit=commit,
                       url=meta['html_url'], archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                       archive_bytes=size, checked_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
            manifest.append(row)
            (DEST / 'pinned.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"Saved {alias}: {size / 1_000_000:.1f} MB / {row['stars']} stars", flush=True)


if __name__ == '__main__':
    main()
