"""Opt-in real public-network check; no model calls or formal-library writes."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skillnet import web_fetch, web_research  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', action='store_true', help='explicitly contact public search and source servers')
    parser.add_argument('--discover', action='store_true', help='also discover quarantined GitHub skill references')
    args = parser.parse_args()
    if not args.network:
        parser.error('real network access requires --network; no requests were sent')
    workspace = ROOT/'.audit-tmp-upgrade'/f'web-network-{time.time_ns()}'
    report = web_research.collect(
        'Open https://www.crossref.org/documentation/retrieve-metadata/rest-api/ and verify its API documentation.',
        workspace, mode='on', discover_missing=args.discover)
    usable = [s for s in report['sources'] if s['state'] in ('fetched','extracted') and len(s.get('text',''))>=12]
    ledger = workspace/'claims.csv'
    with ledger.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['source_id','evidence_url','claim','quote'])
        writer.writeheader()
        for source in usable:
            writer.writerow(dict(source_id=source['source_id'],evidence_url=source['url'],
                claim='仅检查原文摘录出处，不测事实蕴含',quote=source['text'][:180]))
    audit = web_research.audit_files([ledger], report, workspace)
    blocked = web_fetch.fetch_url('http://127.0.0.1/')
    value = dict(observed_at=datetime.now(timezone.utc).isoformat(), sources=[
        {k:v for k,v in source.items() if k!='text'} for source in report['sources']],
        state=report['state'], attempts=report['attempts'], citation_audit={
            k:v for k,v in audit.items() if k!='items'},
        private_address_blocked=blocked['state']=='blocked', model_calls=0,
        workspace=str(workspace), formal_library_written=False,
        discovery={k:v for k,v in report['discovery'].items() if k!='candidates'},
        candidates=[{k:v for k,v in c.items() if k!='body'} for c in report['discovery'].get('candidates',[])],
        boundary='Actual public requests; quote presence and SSRF refusal only, no model quality or identity claim.')
    destination=workspace/'smoke.json'
    destination.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(state=value['state'],sources=len(usable),audit=audit['state'],
        private_address_blocked=value['private_address_blocked'],model_calls=0,report=str(destination)),ensure_ascii=False))
    return 0 if usable and audit['state']=='verified' and value['private_address_blocked'] else 1


if __name__=='__main__':
    raise SystemExit(main())
