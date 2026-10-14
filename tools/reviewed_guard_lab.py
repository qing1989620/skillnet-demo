"""Fresh Glass measurements validate a frozen feasibility guard, not learning.

Every proposed mask is force-executed in the isolated reviewed program, even
when the guard refuses, to measure false blocks and missed runtime failures.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import urllib.request
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet import reviewed_execution as re,utility_ops,utility_oracle,semantic_routing as sr
from tools.semantic_routing_lab import save,load,contract,sha
CODE=['skillnet/reviewed_execution.py','tools/reviewed_guard_lab.py','skillnet/conditional_boundary.py',
      'skillnet/conditional_utility.py','skillnet/utility_ops.py','skillnet/utility_oracle.py']


def prepare(work):
    if work.exists():raise ValueError('fresh study required')
    work.mkdir(parents=True)
    url='https://archive.ics.uci.edu/static/public/42/glass+identification.zip'
    data=urllib.request.urlopen(url,timeout=40).read(100001)
    if len(data)>100000:raise ValueError('source bound')
    (work/'glass.zip').write_bytes(data)
    with zipfile.ZipFile(io.BytesIO(data)) as z:raw=z.read('glass.data')
    (work/'glass.data').write_bytes(raw);original=list(csv.reader(io.StringIO(raw.decode())))
    cases=[]
    for j,kind in enumerate(['normal','normal','mixed_blank','cross_split','duplicate','blank_group',
                             'no_test','bad_number','nan','infinity','large_number','schema']):
        name=f'glass-sealed-{j:02d}'
        rows=[[name+'-'+str(i),name+'-p-'+str(i),'train' if i<2 else 'test',
               'G'+str(i%2),original[(j*13+i)%len(original)][1]] for i in range(10)]
        if kind=='mixed_blank':rows.append([name+'-blank',name+'-bp','test','G0',''])
        if kind=='cross_split':rows.append([name+'-cross',rows[0][1],'test','G0','1.5'])
        if kind=='duplicate':rows.append([*rows[-1][:-1],'7.5'])
        if kind=='blank_group':rows.append([name+'-blank',name+'-bp','test','EMPTY',''])
        if kind=='no_test':
            for r in rows:r[2]='train'
        invalid={'bad_number':'invalid','nan':'NaN','infinity':'Infinity','large_number':'1000000000001'}
        if kind in invalid:rows.append([name+'-bad',name+'-badp','test','G0',invalid[kind]])
        s=io.StringIO(newline='');w=csv.writer(s,lineterminator='\n');w.writerow(['wrong'] if kind=='schema' else utility_ops.HEADER);w.writerows(rows)
        value=s.getvalue().encode();path='inputs/'+name+'.csv';(work/'inputs').mkdir(exist_ok=True);(work/path).write_bytes(value)
        cases.append({'id':name,'kind':kind,'path':path,'input_sha256':sha(value)})
    save(work/'cases.json',cases)
    p={'version':re.VERSION,'created_at_ns':time.time_ns(),'cases_sha256':sha((work/'cases.json').read_bytes()),
       'code_sha256':{n:sha((ROOT/n).read_bytes()) for n in CODE},'masks':list(range(8)),
       'source':{'url':url,'page':'https://archive.ics.uci.edu/dataset/42/glass+identification','license':'CC BY 4.0',
                 'zip_sha256':sha(data),'data_sha256':sha(raw),'measurement':'RI (second column)',
                 'warning':'Groups, partitions, IDs and defects are controlled transforms; not natural defects in Glass.'},
       'acceptance':{'false_blocks':0,'missed_execution_failures':0,'oracle_mismatches':0},
       'scope':'Deterministic finite operator feasibility; not semantic intent, learned superiority, or reward eligibility.'}
    p['protocol_sha256']=sr.digest(p);save(work/'protocol.json',p);print(p['protocol_sha256'])


def run(work):
    p=load(work/'protocol.json');cases=load(work/'cases.json')
    assert p['protocol_sha256']==sr.digest({k:v for k,v in p.items() if k!='protocol_sha256'})
    for n,h in p['code_sha256'].items():assert sha((ROOT/n).read_bytes())==h
    assert sha((work/'cases.json').read_bytes())==p['cases_sha256']
    # All predictions are committed before any forced physical program.
    preds=[]
    for c in cases:
        raw=(work/c['path']).read_bytes();assert sha(raw)==c['input_sha256']
        for mask in p['masks']:preds.append({'case_id':c['id'],'mask':mask,'check':re.preflight(raw,mask)})
    save(work/'predictions.json',{'created_at_ns':time.time_ns(),'rows':preds})
    records=[]
    for c in cases:
        for mask in p['masks']:
            folder=work/'executions'/f'{c["id"]}-{mask}'
            ex=utility_ops.execute(mask,work/c['path'],folder)
            oracle=utility_oracle.evaluate((work/c['path']).read_bytes(),contract(mask),folder)
            r={'case_id':c['id'],'mask':mask,'execution':ex,'oracle':oracle,'directory':folder.relative_to(work).as_posix()}
            save(work/'records'/f'{c["id"]}-{mask}.json',r);records.append(r)
    print('96 forced execution records complete; independent audit required.')


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run']);p.add_argument('--work',type=Path,required=True);a=p.parse_args()
    {'prepare':prepare,'run':run}[a.stage](a.work.absolute())


if __name__=='__main__':main()
