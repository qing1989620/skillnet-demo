"""Serve hash-bound public research and replay recorded decisions explicitly."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import tempfile
import time
from . import semantic_routing as sr,utility_ops,utility_oracle,reviewed_execution

ALLOWED_CODE={'skillnet/semantic_routing.py','tools/semantic_routing_lab.py','skillnet/utility_ops.py',
    'skillnet/utility_oracle.py','skillnet/semantic.py','skillnet/reviewed_execution.py',
    'tools/reviewed_guard_lab.py','skillnet/conditional_boundary.py','skillnet/conditional_utility.py'}


class UnknownCase(LookupError):pass


def bundle(root,version='v1'):
    if version not in ('v1','guard-v1'):raise ValueError('unknown study')
    from .utility_api import _read
    base=Path(root)/'assets/semantic-routing'/version
    pub=json.loads(_read(base/'publication.json',1048576))
    if pub.get('digest')!=sr.digest({k:v for k,v in pub.items() if k!='digest'}):raise ValueError('study publication changed')
    required={'protocol.json','cases.json','report.json','execution-evidence.zip'}
    if not required<=pub.get('files',{}).keys() or len(pub['files'])>1000:raise ValueError('incomplete study')
    data={'base':base}
    for name,meta in pub['files'].items():
        if not re.fullmatch(r'(?:inputs|records)/[a-z0-9_-]+\.(?:csv|json)|[a-zA-Z0-9-]+\.(?:json|data|zip|md)',name):raise ValueError('invalid published path')
        raw=_read(base/name,16*1048576)
        if hashlib.sha256(raw).hexdigest()!=meta['sha256'] or len(raw)!=meta['bytes']:raise ValueError('study bytes changed')
        if '/' not in name and name.endswith('.json'):data[name[:-5]]=json.loads(raw)
    p,r=data['protocol'],data['report']
    if p['protocol_sha256']!=sr.digest({k:v for k,v in p.items() if k!='protocol_sha256'}):raise ValueError('study protocol changed')
    if r['report_sha256']!=sr.digest({k:v for k,v in r.items() if k!='report_sha256'}):raise ValueError('study report changed')
    if r['protocol_sha256']!=p['protocol_sha256'] or r['report_sha256']!=pub['report_sha256']:raise ValueError('study report binding changed')
    if hashlib.sha256(_read(base/'cases.json',1048576)).hexdigest()!=p['cases_sha256']:raise ValueError('study cases changed')
    for name,h in p['code_sha256'].items():
        if name not in ALLOWED_CODE or hashlib.sha256(_read(Path(root)/name,1048576)).hexdigest()!=h:raise ValueError('study program version changed')
    if version=='v1':
        if sr.digest(data['model'])!=r['model_sha256'] or data['selection']['model_sha256']!=r['model_sha256']:raise ValueError('study model changed')
        if data['prompts']['model_sha256']!=r['model_sha256']:raise ValueError('study prediction binding changed')
    return data


def replay(data,case_id,out,repeat=0):
    from .utility_api import _read,public_evidence
    if type(repeat) is not int or repeat not in (0,1):raise ValueError('invalid repeat')
    cases=[c for c in data['cases'] if c['split']=='sealed_test' and c['id']==case_id]
    if len(cases)!=1:raise UnknownCase('unknown public semantic task')
    c=cases[0]
    if not re.fullmatch(r'wine-(?:sealed-[0-7]-[01]|boundary-[0-7])',case_id) or c['path']!='inputs/'+case_id+'.csv':
        raise ValueError('unregistered case path')
    raw=_read(data['base']/c['path'],65536)
    if hashlib.sha256(raw).hexdigest()!=c['input_sha256']:raise ValueError('case changed')
    decisions={a:json.loads(_read(data['base']/'records'/f'{case_id}-{a}-{repeat}.json',65536)) for a in ('plain','retrieved_examples','trained_hint')}
    out=Path(out);out.mkdir(parents=True,exist_ok=True);results={}
    with tempfile.TemporaryDirectory(prefix='semantic-replay-',dir=out) as tmp:
        root=Path(tmp);source=root/'source.csv';source.write_bytes(raw)
        for arm in ('plain','retrieved_examples','trained_hint','guarded_plain'):
            old=decisions['plain' if arm=='guarded_plain' else arm];act=old.get('action')
            r={'recorded_action':act,'recorded_status':old['status'],'artifacts':{}}
            if not act:r['state']='invalid_recorded_action'
            elif act['reject']:r['state']='recorded_refusal'
            else:
                if arm=='guarded_plain':
                    guarded=reviewed_execution.execute(raw,act['mask'],root/arm)
                    r['preflight']=guarded['preflight'];ex=guarded['execution']
                    folder=Path(guarded['directory']) if ex else None
                else:
                    folder=root/arm;ex=utility_ops.execute(act['mask'],source,folder)
                if ex:
                    oracle=utility_oracle.evaluate(raw,c['intent'],folder)
                    r.update(execution=ex,oracle=oracle,state='verified' if oracle['deliverable'] and not c['expect_reject'] else 'rejected')
                    r['artifacts']={name:{**meta,'text':_read(folder/name,65536).decode('utf-8-sig')} for name,meta in ex['artifacts'].items()}
                else:r['state']='preflight_rejected'
            results[arm]=r
    value={'case':{k:c[k] for k in ('id','request','kind')},'input_csv':raw.decode('utf-8-sig'),
           'results':public_evidence(results),'created_at_ns':time.time_ns(),'recorded_api_decisions':True,'recorded_repeat':repeat,
           'new_api_calls':0,'reward_applied':False,'formal_library_changed':False,'points':0,
           'warning':'Recorded API choices, freshly executed fixed programs. The feasibility guard cannot resolve ambiguous intent.'}
    value['report_sha256']=sr.digest(value);return value
