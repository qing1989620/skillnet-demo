"""Freeze resource bytes after importing pinned, attributed community packages."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from skillnet.resources import build_snapshots


def main():
    rows=build_snapshots()
    target=ROOT/'seed/community/packages.json'
    target.write_text(json.dumps(rows,ensure_ascii=False,separators=(',',':')),encoding='utf-8',newline='\n')
    print(json.dumps(dict(packages=len(rows),files=sum(len(r['files']) for r in rows.values()),
        manifest_bytes=target.stat().st_size)))


if __name__=='__main__':main()
