"""One-shot evaluation of the validation-selected adapter on an unseen source."""
from pathlib import Path
import argparse,json,sys,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet.semantic import DenseIndex
from skillnet.learned_network import NetworkAdapter,digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--external',required=True,type=Path);p.add_argument('--model',required=True,type=Path);args=p.parse_args()
    out=args.external;assert not (out/'report.json').exists(),'External test is frozen and already reported'
    corpus=json.loads((out/'corpus.json').read_text(encoding='utf-8'));adapter=NetworkAdapter.load(args.model)
    selected=dict(model_id=adapter.metadata['model_id'],weights_sha256=adapter.metadata['weights_sha256'],external_corpus_sha256=digest(corpus),training_forbidden=True)
    (out/'selection-before-embeddings.json').write_text(json.dumps(selected,indent=2),encoding='utf-8')
    enc=DenseIndex(ROOT/'.models/multilingual-e5-small');skills=corpus['skills'];tasks=corpus['tasks'];texts=[]
    for s in skills:
        body=str(s.get('body') or s.get('description') or s['name']);mid=max(0,len(body)//2-500);texts.extend([body[:1100],body[mid:mid+1100],body[-1100:]])
    parts=[]
    for start in range(0,len(texts),96):
        parts.append(enc.embed(texts[start:start+96],'passage: '));print('Unseen skill-body views',min(start+96,len(texts)),'/',len(texts),flush=True)
    views=np.concatenate(parts).reshape(len(skills),3,384);x=(views*np.array([.55,.25,.2],np.float32)[None,:,None]).sum(1);x/=np.maximum(np.linalg.norm(x,axis=1,keepdims=True),1e-8)
    q=enc.embed([t['instruction_text'] for t in tasks],'query: ');base=q@x.T;trained=adapter.query(q)@adapter.skills(x,graph=False).T
    by={s['skill_id']:i for i,s in enumerate(skills)};rows=[]
    for t,b,c in zip(tasks,base,trained):
        gold={by[n] for n in corpus['relevance'][t['task_id']]['gt_skill_ids']}
        br=np.argsort(-b,kind='stable');cr=np.argsort(-c,kind='stable')
        rows.append(dict(id=t['task_id'],gold_count=len(gold),baseline_recall5=len(gold&set(br[:5]))/len(gold),trained_recall5=len(gold&set(cr[:5]))/len(gold),baseline_mrr=1/min(i+1 for i,n in enumerate(br) if n in gold),trained_mrr=1/min(i+1 for i,n in enumerate(cr) if n in gold)))
    br=float(np.mean([r['baseline_recall5'] for r in rows]));cr=float(np.mean([r['trained_recall5'] for r in rows]));d=[r['trained_recall5']-r['baseline_recall5'] for r in rows]
    result=dict(version='network-transfer-probe-v1',**selected,scope=corpus['protocol']['scope'],candidate_count=len(skills),tasks=len(tasks),baseline_recall5=br,trained_recall5=cr,mean_gain=cr-br,wins=sum(v>1e-10 for v in d),losses=sum(v < -1e-10 for v in d),ties=sum(abs(v)<=1e-10 for v in d),
        upstream_graded_relevance_boundary='Some graded degraded/* identifiers are absent from the released Hard pool. Only existing ground-truth IDs are used for Recall/MRR; no invented variants or nDCG claims.',
        model_retrained=False,served=False,reward=0,rows=rows)
    result['report_sha256']=digest(result);(out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Unseen-source transfer:',json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
