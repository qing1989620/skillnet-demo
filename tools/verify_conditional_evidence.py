"""Cold-clone verification: inspect ZIP bytes, never run code from an archive."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path,PurePosixPath
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet import conditional_utility as cu,utility_ops,utility_oracle
from skillnet.utility_api import bundle,boundary_bundle


def contents(path):
    result={};expanded=0
    with zipfile.ZipFile(path) as z:
        infos=z.infolist()
        if len(infos)>20000:raise ValueError('too many evidence files')
        for item in infos:
            name=item.filename;p=PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or ':' in name or '\\' in name or name in result or item.is_dir():
                raise ValueError('invalid or duplicate archive path')
            expanded+=item.file_size
            if expanded>128*1048576 or item.file_size>8*1048576:raise ValueError('expanded evidence exceeds bound')
            # ZipFile also validates each entry CRC; archive SHA was checked above.
            result[name]=z.read(item)
    return result


def verify(root):
    b=bundle(root);v2=boundary_bundle(root);errors=[];counts={};archives={}
    for name,data in [('v1',b),('v2',v2)]:
        archive=contents(data['base']/'execution-evidence.zip');archives[name]=archive
        for file in ('model.json','protocol.json','report.json','selection.json','cases.json'):
            if archive[file]!=(data['base']/file).read_bytes():errors.append([name,file,'public/archive mismatch'])
    def readj(archive,name):return json.loads(archive[name])
    with tempfile.TemporaryDirectory(prefix='conditional-evidence-audit-') as folder:
        tmp=Path(folder);index=0
        for version,archive in archives.items():
            cases={c['id']:c for c in readj(archive,'cases.json')}
            if version=='v1':
                records=sum([readj(archive,f'{stage}-executions.json') for stage in ('train','calibration','test')],[])
                lr=readj(archive,'llm-report.json')
                records += [r for r in lr['records'] if r.get('execution')]
                frozen=readj(archive,'test-predictions-frozen.json')['created_at_ns']
            else:
                records=[r for r in readj(archive,'executions.json') if r.get('execution')]
                frozen=readj(archive,'predictions-frozen.json')['created_at_ns']
            counts[version]=len(records)
            for r in records:
                index+=1;case=cases[r['task_id']];raw=archive[case['path']];record=r['execution']
                if hashlib.sha256(raw).hexdigest()!=record['input_sha256']:errors.append([version,r['task_id'],'source'])
                prefix=r['directory']+'/'
                if hashlib.sha256(archive[prefix+'main.py']).hexdigest()!=utility_ops.CODE_SHA:
                    errors.append([version,r['task_id'],'program'])
                work=tmp/str(index);work.mkdir()
                for filename in ('output.csv','summary.csv'):
                    key=prefix+filename
                    if key in archive:(work/filename).write_bytes(archive[key])
                for filename,meta in record['artifacts'].items():
                    value=archive[prefix+filename]
                    if hashlib.sha256(value).hexdigest()!=meta['sha256'] or len(value)!=meta['bytes']:
                        errors.append([version,r['task_id'],'artifact'])
                if utility_oracle.evaluate(raw,case['intent'],work)!=r['oracle']:errors.append([version,r['task_id'],'oracle'])
                if version=='v2' or case.get('split')=='sealed_test':
                    if record['started_at_ns']<=frozen:errors.append([version,r['task_id'],'late prediction'])
    parent_sha=hashlib.sha256(archives['v1']['train-executions.json']).hexdigest()
    if v2['model']['training_records_sha256']!=parent_sha:errors.append(['v2','training lineage'])
    for c in json.loads(archives['v1']['cases.json']):
        # A source identity cannot be used as a feature to manufacture transfer.
        if c['split']=='train' and c['kind'].startswith('public'):errors.append(['v1','source leak'])
    result={'ok':not errors,'errors':errors,'physical_programs_reverified':counts,
            'llm_calls':b['llm-report']['requested_calls'],'model_sha256':b['model_sha256'],
            'boundary_model_sha256':cu.digest(v2['model']),'scope':'all saved outputs independently recalculated; archived programs never executed'}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--output',type=Path)
    a=p.parse_args();r=verify(a.root)
    if a.output:a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(r),flush=True)
    if not r['ok']:raise SystemExit(1)
