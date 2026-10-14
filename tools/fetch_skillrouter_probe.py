"""Unseen SkillRouter transfer probe, explicitly a reduced pool, never its 80K benchmark."""
from pathlib import Path
import json,urllib.request,hashlib,gzip,concurrent.futures,heapq,time
import argparse
_parser=argparse.ArgumentParser();_parser.add_argument('--output',type=Path,required=True);_args=_parser.parse_args()
ROOT=_args.output.resolve();ROOT.mkdir(parents=True,exist_ok=True);S=ROOT/'sources';OUT=ROOT/'external-test';OUT.mkdir(exist_ok=True)
S.mkdir(exist_ok=True)
revision='20a03920e7f08d76b67af367350d25ef4468198e'
for name in ['manifest.json','tasks.jsonl','relevance.json']:
    file=S/('SkillRouter-'+name)
    if not file.exists():
        url=f'https://huggingface.co/datasets/pipizhao/SkillRouter-Eval-Core/resolve/{revision}/{name}'
        file.write_bytes(urllib.request.urlopen(url,timeout=60).read())
manifest=json.loads((S/'SkillRouter-manifest.json').read_text())
tasks=[json.loads(x) for x in (S/'SkillRouter-tasks.jsonl').read_text(encoding='utf-8').splitlines()]
relevance=json.loads((S/'SkillRouter-relevance.json').read_text(encoding='utf-8'))
tasks=[t for t in tasks if relevance[t['task_id']]['task_type']!='generic_only']
assert len(tasks)==75
required={skill for t in tasks for skill in relevance[t['task_id']]['gt_skill_ids']}
protocol={'source_revision':revision,'model_selection':'must be frozen by evaluate_network_transfer.py before inference',
    'training_forbidden':True,'tasks':75,'pool_rule':'all benchmark ground-truth and released distractor variants plus 1024 registry distractors with smallest SHA256(skill_id)',
    'scope':'Reduced-pool transfer probe only. Not the published 79,141-skill Hard benchmark.',
    'query_text_not_used_to_choose_distractors':True,'full_skillrouter_reproduction':False}
(OUT/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
def download(part):
    name=part['path'];p=OUT/Path(name).name
    if p.exists():return p
    url=f'https://huggingface.co/datasets/pipizhao/SkillRouter-Eval-Core/resolve/{revision}/{name}'
    for attempt in range(3):
        try:
            tmp=p.with_suffix('.partial');count=0
            with urllib.request.urlopen(url,timeout=90) as response,tmp.open('wb') as f:
                while chunk:=response.read(1024*1024):
                    count+=len(chunk);assert count<80*1024*1024,'Unexpected shard size';f.write(chunk)
            tmp.replace(p);print('External shard',p.name,count,'bytes',flush=True);return p
        except Exception:
            if attempt==2:raise
            time.sleep(1)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:files=list(pool.map(download,manifest['hard']['parts']))
selected={};sample=[];seen=set()
for p in files:
    with gzip.open(p,'rt',encoding='utf-8') as stream:
        for line in stream:
            row=json.loads(line);key=row['skill_id']
            if key in seen:continue
            seen.add(key)
            if key in required or row.get('source')=='distractor':selected[key]=row
            elif row.get('source')=='pool':
                score=int(hashlib.sha256(key.encode()).hexdigest(),16)
                if len(sample)<1024:heapq.heappush(sample,(-score,key,row))
                elif score< -sample[0][0]:heapq.heapreplace(sample,(-score,key,row))
selected.update({key:row for _,key,row in sample})
assert required.issubset(selected),required-set(selected)
corpus={'version':'external-skillrouter-reduced-v1','protocol':protocol,'tasks':tasks,'relevance':{t['task_id']:relevance[t['task_id']] for t in tasks},'skills':sorted(selected.values(),key=lambda r:r['skill_id']),
    'shards':[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files]}
(OUT/'corpus.json').write_text(json.dumps(corpus,ensure_ascii=False),encoding='utf-8')
print('External frozen pool ready',len(selected),'skills; 75 unseen tasks; full benchmark not claimed',flush=True)
