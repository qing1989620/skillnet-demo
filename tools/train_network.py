"""Real gradient training and preregistered ablations for the skill network."""
from __future__ import annotations
import argparse,copy,hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet.learned_network import NetworkAdapter,VERSION,digest

def metrics(scores,tasks,by):
    rows=[]
    for values,t in zip(scores,tasks):
        order=np.argsort(-values,kind='stable');gold={by[x] for x in t['gold']};head=set(order[:5]);positions=[i+1 for i,x in enumerate(order) if x in gold]
        rows.append(dict(id=t['id'],family=t['family'],query_sha256=t['query_sha256'],
            recall5=len(gold&head)/len(gold),precision5=len(gold&head)/5,mrr=1/min(positions),
            exact_set=float(set(order[:len(gold)])==gold),top5=[list(by)[i] for i in order[:5]]))
    return dict(recall5=float(np.mean([r['recall5'] for r in rows])),precision5=float(np.mean([r['precision5'] for r in rows])),
        mrr=float(np.mean([r['mrr'] for r in rows])),exact_set=float(np.mean([r['exact_set'] for r in rows])),tasks=len(rows),rows=rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--experiment',type=Path,required=True);args=p.parse_args();folder=args.experiment
    protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'));corpus=json.loads((folder/'corpus.json').read_text(encoding='utf-8'))
    assert digest(corpus)==protocol['corpus_sha256']
    protocol_sha=hashlib.sha256((folder/'protocol.json').read_bytes()).hexdigest()
    assert not (folder/'final-report.json').exists(),'Frozen test already reported; do not tune on it'
    with np.load(folder/'features.npz',allow_pickle=False) as f:data={k:f[k] for k in f.files}
    import torch
    from torch import nn
    from torch.nn import functional as F
    torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu'
    ids=[n['id'] for n in corpus['nodes']];by={n:i for i,n in enumerate(ids)};tasks=corpus['tasks']
    splits={s:[i for i,t in enumerate(tasks) if t['split']==s] for s in ['train','validation','test']}
    X=torch.tensor(data['skills'],device=device);V=torch.tensor(data['views'],device=device);G=torch.tensor(data['neighbours'],device=device);Q=torch.tensor(data['queries'],device=device)
    pos=torch.zeros((len(tasks),len(ids)),dtype=torch.bool,device=device)
    for i,t in enumerate(tasks):pos[i,[by[n] for n in t['gold']]]=True
    class Trainable(nn.Module):
        def __init__(self,seed,graph):
            super().__init__();base=NetworkAdapter.identity(seed);self.w=nn.ParameterDict({k:nn.Parameter(torch.tensor(v,device=device)) for k,v in base.weights.items()});self.graph=graph
        def query(self,x):return F.normalize(x+.25*(torch.tanh(x@self.w['q_down'])@self.w['q_up']),dim=-1)
        def skills(self):
            y=X+.25*(torch.tanh(X@self.w['s_down'])@self.w['s_up'])
            if self.graph:
                g=(G*torch.softmax(self.w['relation_logits'],0)[None,:,None]).sum(1);y=y+.15*(torch.tanh(g@self.w['g_down'])@self.w['g_up'])
            return F.normalize(y,dim=-1)
        def portable(self):return NetworkAdapter({k:v.detach().cpu().numpy() for k,v in self.w.items()},{'version':VERSION})
    def evaluate(model,split):
        with torch.no_grad():score=(model.query(Q[splits[split]])@model.skills().T).cpu().numpy()
        return metrics(score,[tasks[i] for i in splits[split]],by)
    baseline={}
    for split in ['validation']:
        score=data['queries'][splits[split]]@data['skills'].T;baseline[split]=metrics(score,[tasks[i] for i in splits[split]],by)
    experiments=[];started=time.monotonic()
    for graph in [False,True]:
      for seed in protocol['seeds']:
        torch.manual_seed(seed);rng=np.random.default_rng(seed);model=Trainable(seed,graph);opt=torch.optim.AdamW(model.parameters(),lr=protocol['learning_rate'],weight_decay=.01)
        trace=[];name=('graph' if graph else 'text')+'-'+str(seed);print('Training',name,'on',device,flush=True)
        for epoch in range(protocol['pretraining_epochs']):
            losses=[]
            for chunk in np.array_split(rng.permutation(len(ids)),math.ceil(len(ids)/128)):
                inds=torch.tensor(chunk,device=device);scores=model.query(V[inds])@model.skills().T/.07
                loss=F.cross_entropy(scores,inds);opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);opt.step();losses.append(float(loss.detach()))
            trace.append(dict(phase='public_document_pretraining',epoch=epoch+1,loss=float(np.mean(losses))))
            print(name,'pretrain',epoch+1,'loss',round(trace[-1]['loss'],4),flush=True)
        pretrain_meta=model.portable().save(folder/'models'/name/'pretrained',stage='pretrained_candidate',protocol_sha256=protocol_sha,seed=seed,graph=graph)
        # Every candidate starts its task fine-tuning from the pretrained network.
        best=evaluate(model,'validation');best_weights=copy.deepcopy(model.state_dict());best_epoch=0
        for epoch in range(protocol['finetuning_epochs']):
            losses=[]
            for chunk in np.array_split(rng.permutation(splits['train']),math.ceil(len(splits['train'])/24)):
                inds=torch.tensor(chunk,device=device);q=model.query(Q[inds]);s=model.skills();logits=q@s.T/.07
                loss=(torch.logsumexp(logits,1)-torch.logsumexp(logits.masked_fill(~pos[inds],float('-inf')),1)).mean()
                loss=loss+.04*((q-Q[inds]).square().mean()+(s-X).square().mean())
                opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);opt.step();losses.append(float(loss.detach()))
            validation=evaluate(model,'validation');trace.append(dict(phase='train_partition_finetuning',epoch=epoch+1,loss=float(np.mean(losses)),validation_recall5=validation['recall5']))
            if validation['recall5']>best['recall5']+1e-10:best=validation;best_weights=copy.deepcopy(model.state_dict());best_epoch=epoch+1
            if (epoch+1)%5==0:print(name,'finetune',epoch+1,'loss',round(trace[-1]['loss'],4),'validation Recall@5',round(validation['recall5'],4),flush=True)
        model.load_state_dict(best_weights);adapter=model.portable();directory=folder/'models'/name/'selected'
        delta=sum(float(np.square(adapter.weights[k]-NetworkAdapter.identity(seed).weights[k]).sum()) for k in adapter.weights)
        meta=adapter.save(directory,stage='research_candidate_not_admitted',protocol_sha256=protocol_sha,corpus_sha256=protocol['corpus_sha256'],encoder=protocol['encoder'],seed=seed,graph=graph,selected_epoch=best_epoch,parameter_delta_l2=math.sqrt(delta),training_examples=len(splits['train']),document_pretraining_examples=len(ids))
        (directory/'training-curve.json').write_text(json.dumps(trace,indent=2),encoding='utf-8')
        experiments.append(dict(name=name,graph=graph,seed=seed,path=str(directory),model_id=meta['model_id'],selected_epoch=best_epoch,validation=best,parameter_delta_l2=math.sqrt(delta),curve=trace))
        print('Selected',name,'epoch',best_epoch,'validation',round(best['recall5'],4),flush=True)
    # Selection is frozen before reading any test score; no test-based retries.
    selected=max(experiments,key=lambda r:r['validation']['recall5'])['name']
    selection={'selected_by_validation':selected,'protocol_sha256':protocol_sha,'candidate_order':[r['name'] for r in experiments]}
    (folder/'selection-before-test.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
    baseline['test']=metrics(data['queries'][splits['test']]@data['skills'].T,[tasks[i] for i in splits['test']],by)
    for row in experiments:
        adapter=NetworkAdapter.load(Path(row['path']));score=adapter.query(data['queries'][splits['test']])@adapter.skills(data['skills'],data['neighbours'],graph=row['graph']).T
        row['test']=metrics(score,[tasks[i] for i in splits['test']],by)
    champion=next(r for r in experiments if r['name']==selected)
    differences=[a['recall5']-b['recall5'] for a,b in zip(champion['test']['rows'],baseline['test']['rows'])]
    wins=sum(x>1e-10 for x in differences);losses=sum(x< -1e-10 for x in differences);n=wins+losses
    sign_p=sum(math.comb(n,k) for k in range(wins,n+1))/2**n if n else 1.
    result=dict(version='skill-network-research-report-v1',protocol_sha256=protocol_sha,
        features_sha256=hashlib.sha256((folder/'features.npz').read_bytes()).hexdigest(),selected_by_validation=selected,
        scope='Official SkillNet-Gym attached-skill retrieval in a frozen local mixed catalog; not execution success or the full SkillRouter benchmark',
        corpus=dict(skills=len(ids),edges=len(corpus['edges']),tasks=len(tasks),splits={k:len(v) for k,v in splits.items()}),
        baseline=baseline,experiments=experiments,comparison=dict(mean_recall5_gain=float(np.mean(differences)),wins=wins,losses=losses,ties=len(differences)-n,sign_p=sign_p,all_tasks_non_regressing=losses==0),
        training_seconds=round(time.monotonic()-started,3),device=device,torch_version=torch.__version__,
        status='research_candidate_not_admitted',serving_changed=False,rewards_applied=0,
        limitations=protocol['limitations']+['A routing relevance gain does not establish downstream task improvement','No user data or artificial model scores enter this training run'])
    (folder/'final-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    # Save a local, verifiable inference bundle for the current product catalog.
    directory=folder/'product-bundle';adapter=NetworkAdapter.load(Path(champion['path']));adapter.save(directory,stage='research_candidate_not_admitted',protocol_sha256=protocol_sha,encoder=protocol['encoder'],selected_by_validation=selected)
    local=[(i,n) for i,n in enumerate(corpus['nodes']) if any(a.startswith('local/') for a in n['aliases'])]
    names=[];indices=[];content_sha=[]
    for i,node in local:
        for alias in node['aliases']:
            if alias.startswith('local/'):names.append(alias[6:]);indices.append(i);content_sha.append(node['sha256'])
    np.savez_compressed(directory/'catalog.npz',features=data['skills'][indices],neighbours=data['neighbours'][indices])
    catalog=dict(names=names,body_sha256=content_sha,file_sha256=hashlib.sha256((directory/'catalog.npz').read_bytes()).hexdigest())
    (directory/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf-8')
    public={k:result[k] for k in ['version','scope','protocol_sha256','features_sha256','selected_by_validation','corpus','comparison','training_seconds','device','torch_version','status','serving_changed','rewards_applied','limitations']}
    public['baseline_test']={k:v for k,v in baseline['test'].items() if k!='rows'};public['selected_test']={k:v for k,v in champion['test'].items() if k!='rows'}
    public['ablations']=[dict(name=e['name'],seed=e['seed'],graph=e['graph'],validation_recall5=e['validation']['recall5'],test_recall5=e['test']['recall5'],selected_epoch=e['selected_epoch'],parameter_delta_l2=e['parameter_delta_l2']) for e in experiments]
    public['report_sha256']=digest(public);(folder/'public-report.json').write_text(json.dumps(public,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Final frozen test',json.dumps(public,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
