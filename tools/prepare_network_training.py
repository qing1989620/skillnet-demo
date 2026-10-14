"""Freeze official Gym routing splits, public catalog text views and embeddings.

Only reads upstream text. Attached skills are package-level retrieval targets;
they are not assumed to be a minimal set or proven causal contributors.
"""
from __future__ import annotations
from pathlib import Path
import argparse,hashlib,json,re,sys,itertools
import numpy as np
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet.catalog import SkillLibrary
from skillnet.semantic import DenseIndex
from skillnet.learned_network import digest,neighbour_features
from skillnet.reward_gates import policy_sha256

def body_parts(text):
    text=text.replace('\r\n','\n').strip();meta={}
    m=re.match(r'\A---\s*\n(.*?)\n---\s*\n(.*)',text,re.S)
    if m:
        header,body=m.groups()
        if len(header)<12000 and header.count('&')<20 and header.count('*')<20:
            try:
                value=yaml.safe_load(header)
                if isinstance(value,dict):meta=value
            except yaml.YAMLError:pass
    else:body=text
    return meta,body.strip()

def main():
    p=argparse.ArgumentParser();p.add_argument('--gym-dir',required=True,type=Path);p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    if (out/'protocol.json').exists():raise SystemExit('Frozen protocol already exists; use a new experiment directory')
    manifest=json.loads((args.gym_dir/'download-manifest.json').read_text(encoding='utf-8'));assert not manifest['errors']
    for row in manifest['files']:
        path=args.gym_dir.joinpath(*Path(row['path']).parts)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'],row['path']
    nodes=[];by_sha={};aliases={};edges=[]
    def add(name,text,view,source,alias):
        _,body=body_parts(text);sha=hashlib.sha256(body.encode()).hexdigest()
        if sha not in by_sha:
            by_sha[sha]=len(nodes)
            nodes.append(dict(id=('local/'+name) if source=='local' else 'gym/'+sha[:20],name=name,body=body[:100000],view=view[:1800] or name,source=source,sha256=sha,aliases=[]))
        node=nodes[by_sha[sha]];node['aliases'].append(alias);aliases[alias]=node['id'];return node['id']
    lib=SkillLibrary.load()
    for s in lib.all():
        text=s.reference_body() or s.l2_text()
        add(s.name,text,' '.join([s.description,s.capability,*s.use_when]),'local','local/'+s.name)
    for edge in lib.relation_edges():
        a=aliases.get('local/'+edge['source']);b=aliases.get('local/'+edge['target'])
        if a and b:edges.append(dict(source=a,target=b,type=edge['type'],origin='catalog_declaration'))
    tasks=[]
    gym_root=next(args.gym_dir.glob('skillnet-gym*'))
    for folder in sorted(gym_root.glob('task-*')):
        files=sorted((folder/'environment/skills').glob('*/SKILL.md'))
        gold=[];families=[]
        for file in files:
            text=file.read_text(encoding='utf-8-sig');meta,body=body_parts(text)
            name=str(meta.get('name') or file.parent.name)
            view=str(meta.get('description') or body[:700])
            gold.append(add(name,text,view,'gym',folder.name+'/'+file.parent.name));families.append(name)
        instruction=(folder/'instruction.md').read_text(encoding='utf-8-sig').strip()
        assert instruction and gold,folder
        # Exact gold-package family stays together. Public skill documents may
        # appear across families, as in normal retrieval over a known catalog.
        family=digest(sorted(set(families)))
        bucket=int(family[:8],16)%100
        split='train' if bucket<65 else 'validation' if bucket<82 else 'test'
        tasks.append(dict(id=folder.name,query=instruction,gold=sorted(set(gold)),family=family,split=split,query_sha256=hashlib.sha256(instruction.encode()).hexdigest(),source='official_skillnet_gym_attached_packages'))
    # Duplicate questions must never leak across partitions.
    normalized={}
    for t in tasks:
        key=re.sub(r'\s+',' ',t['query']).strip().lower()
        if key in normalized:t['split']=normalized[key]
        else:normalized[key]=t['split']
    for t in tasks:
        if t['split']=='train':
            for a,b in itertools.permutations(t['gold'],2):edges.append(dict(source=a,target=b,type='co_use',origin='training_partition_attached_packages'))
    splits={s:[t['id'] for t in tasks if t['split']==s] for s in ['train','validation','test']}
    assert all(len(ids)>=10 for ids in splits.values()),splits
    corpus=dict(version='network-training-corpus-v1',nodes=nodes,tasks=tasks,edges=edges)
    protocol=dict(version='network-training-protocol-v1',frozen_before_embeddings_and_training=True,
        reward_policy_sha256=policy_sha256(),
        corpus_sha256=digest(corpus),upstream_manifest_sha256=digest(manifest),splits=splits,
        split_rule='stable SHA256 of attached skill-name set; duplicate question text co-located',
        seeds=[17,29],pretraining_epochs=8,finetuning_epochs=40,learning_rate=.003,
        selection_metric='validation mean Recall@5; choose earliest epoch on ties',
        metrics=['Recall@5','Precision@5','MRR','exact_set_at_gold_count'],
        controls=['frozen_full_body_e5','trained_text_adapter','trained_typed_graph_adapter'],
        test_rule='test labels must not affect optimization, checkpoint or hyperparameter selection; report once after validation selection',
        contamination_boundary='Public catalog documents are transductive unlabeled inputs. Only train task-skill membership creates co_use edges. Held-out task queries and labels never enter gradients.',
        limitations=['159 synthesized tasks, not human user preferences','attached packages are reference retrieval targets, not causal contribution evidence','original Gym dependency gold edges were not present in this ZIP subset; co_use is not a dependency','upstream skill content stays in local research storage; licenses are not assumed transferable'],
        encoder=dict(repository='Xenova/multilingual-e5-small',revision='761b726dd34fb83930e26aab4e9ac3899aa1fa78',frozen=True),
        admission='Twelve AND gates remain required for improvement rewards; model candidates are shadow only until separately admitted')
    (out/'corpus.json').write_text(json.dumps(corpus,ensure_ascii=False),encoding='utf-8')
    (out/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Frozen corpus:',len(nodes),'skills;',len(edges),'typed edges; splits',{k:len(v) for k,v in splits.items()},flush=True)
    encoder=DenseIndex(ROOT/'.models/multilingual-e5-small')
    def embed(texts,prefix,label):
        arrays=[]
        for start in range(0,len(texts),96):
            arrays.append(encoder.embed(texts[start:start+96],prefix));print(label,min(start+96,len(texts)),'/',len(texts),flush=True)
        return np.concatenate(arrays)
    texts=[]
    for n in nodes:
        b=n['body'];mid=max(0,len(b)//2-500);texts.extend([b[:1100],b[mid:mid+1100],b[-1100:]])
    parts=embed(texts,'passage: ','Skill body views').reshape(len(nodes),3,384)
    x=(parts*np.array([.55,.25,.20],np.float32)[None,:,None]).sum(axis=1);x/=np.maximum(np.linalg.norm(x,axis=1,keepdims=True),1e-8)
    views=embed([n['view'] for n in nodes],'query: ','Unlabeled skill views')
    q=embed([t['query'] for t in tasks],'query: ','Benchmark queries (frozen partitions)')
    g=neighbour_features(x,[n['id'] for n in nodes],edges)
    np.savez_compressed(out/'features.npz',skills=x,views=views,queries=q,neighbours=g)
    print('Frozen features ready',hashlib.sha256((out/'features.npz').read_bytes()).hexdigest(),flush=True)

if __name__=='__main__':main()
