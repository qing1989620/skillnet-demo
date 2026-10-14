"""Cold-clone audit of the new Glass validation, including refused actions."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet import semantic_routing as sr,utility_ops,utility_oracle
from tools.verify_semantic_routing import load,write,sha


def audit(work):
    p=load(work/'protocol.json');cases=load(work/'cases.json');pred=load(work/'predictions.json')
    assert p['protocol_sha256']==sr.digest({k:v for k,v in p.items() if k!='protocol_sha256'})
    for n,h in p['code_sha256'].items():assert sha((ROOT/n).read_bytes())==h
    assert sha((work/'cases.json').read_bytes())==p['cases_sha256']
    for n in ['glass.zip','glass.data']:assert sha((work/n).read_bytes())==p['source']['zip_sha256' if n.endswith('zip') else 'data_sha256']
    assert p['created_at_ns']<pred['created_at_ns']
    predictions={(x['case_id'],x['mask']):x['check'] for x in pred['rows']};assert len(predictions)==96
    counters={'valid_actions':0,'invalid_actions':0,'false_blocks':0,'missed_execution_failures':0,'oracle_mismatches':0}
    for c in cases:
        raw=(work/c['path']).read_bytes();assert sha(raw)==c['input_sha256']
        for mask in range(8):
            r=load(work/'records'/f'{c["id"]}-{mask}.json');ex=r['execution'];folder=work/r['directory']
            assert folder.resolve().is_relative_to((work/'executions').resolve())
            assert sha((folder/'main.py').read_bytes())==ex['code_sha256']==utility_ops.CODE_SHA
            assert sha((folder/'input.csv').read_bytes())==c['input_sha256']==ex['input_sha256']
            assert ex['started_at_ns']>pred['created_at_ns']
            for name,meta in ex['artifacts'].items():
                assert name in ('output.csv','summary.csv')
                b=(folder/name).read_bytes();assert sha(b)==meta['sha256'] and len(b)==meta['bytes']
            intent={k:bool(mask & (1<<j)) for j,k in enumerate(utility_oracle.KEYS)};intent['goal']='group_mean'
            o=utility_oracle.evaluate(raw,intent,folder);assert o==r['oracle']
            valid=o['deliverable'];allowed=predictions[(c['id'],mask)]['allowed']
            assert predictions[(c['id'],mask)]['input_sha256']==c['input_sha256']
            assert not predictions[(c['id'],mask)]['semantic_scope_validated']
            counters['valid_actions' if valid else 'invalid_actions']+=1
            counters['false_blocks']+=int(valid and not allowed)
            counters['missed_execution_failures']+=int(not valid and allowed)
            counters['oracle_mismatches']+=int(valid!=(ex['status']=='completed'))
    r={'version':p['version'],'protocol_sha256':p['protocol_sha256'],'tasks':12,'physical_executions':96,
       'metrics':counters,'artifact_audit':{'ok':True},
       'accepted':all(counters[k]<=v for k,v in p['acceptance'].items()),
       'scope':p['scope'],'reward_applied':False,'points':0}
    r['report_sha256']=sr.digest(r);return r


def package(work,dest):
    r=audit(work);assert r['accepted']
    if (work/'report.json').exists():assert load(work/'report.json')==r
    else:write(work/'report.json',r)
    dest.mkdir(parents=True,exist_ok=False)
    for name in ['protocol.json','cases.json','predictions.json','report.json','glass.data','glass.zip']:shutil.copyfile(work/name,dest/name)
    for folder in ['inputs','records']:shutil.copytree(work/folder,dest/folder)
    with zipfile.ZipFile(dest/'execution-evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted((work/'executions').rglob('*')):
            if path.is_file():z.write(path,path.relative_to(work).as_posix())
    (dest/'ATTRIBUTION.md').write_text('German, B. (1987). Glass Identification. UCI. DOI 10.24432/C5WW2P. CC BY 4.0.\nhttps://archive.ics.uci.edu/dataset/42/glass+identification\nOnly RI measurements used; controlled synthetic IDs, groups, partitions and defects.\n',encoding='utf-8',newline='\n')
    pub={'files':{x.relative_to(dest).as_posix():{'bytes':x.stat().st_size,'sha256':sha(x.read_bytes())} for x in sorted(dest.rglob('*')) if x.is_file()},'report_sha256':r['report_sha256']}
    pub['digest']=sr.digest(pub);write(dest/'publication.json',pub)


def public_audit(base):
    pub=load(base/'publication.json');assert pub['digest']==sr.digest({k:v for k,v in pub.items() if k!='digest'})
    for name,meta in pub['files'].items():
        path=(base/name).resolve();assert path.is_relative_to(base.resolve())
        b=path.read_bytes();assert sha(b)==meta['sha256'] and len(b)==meta['bytes']
    with tempfile.TemporaryDirectory(prefix='guard-audit-') as tmp:
        work=Path(tmp)
        for path in base.rglob('*'):
            if path.is_file() and path.name!='execution-evidence.zip':
                target=work/path.relative_to(base);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        with zipfile.ZipFile(base/'execution-evidence.zip') as z:
            assert len(z.infolist())<1000 and sum(i.file_size for i in z.infolist())<16*1048576
            for i in z.infolist():
                target=(work/i.filename).resolve();assert target.is_relative_to((work/'executions').resolve())
                assert not i.is_dir() and i.file_size<1048576 and ':' not in i.filename and '\\' not in i.filename
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(i))
        r=audit(work);assert r==load(base/'report.json')
    return {'ok':True,**r['metrics'],'physical_executions':96}


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path);p.add_argument('--publish',type=Path);p.add_argument('--public',type=Path);a=p.parse_args()
    if a.public:print(json.dumps(public_audit(a.public.absolute())));return
    if a.publish:package(a.work.absolute(),a.publish.absolute())
    print(json.dumps(audit(a.work.absolute()),indent=2))


if __name__=='__main__':main()
