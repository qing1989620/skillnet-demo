"""Continue v1 weights with multi-source supervision and explicit retention ablations."""
from __future__ import annotations

import argparse,copy,hashlib,json,sys,time
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet.learned_network import NetworkAdapter,VERSION,digest
from skillnet.routing_research import routing_metrics,paired_routing_comparison,binomial_risk_upper
from skillnet.reward_gates import policy_sha256


def stripped(metrics):return {k:v for k,v in metrics.items() if k!='rows'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--experiment',type=Path,required=True);a=p.parse_args();folder=a.experiment
    if (folder/'final-report.json').exists():raise SystemExit('Final test already reported; choose a new preregistered study')
    protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==protocol['training_script_sha256']
    assert hashlib.sha256((ROOT/'skillnet/routing_research.py').read_bytes()).hexdigest()==protocol['metric_code_sha256']
    assert protocol['reward_policy_sha256']==policy_sha256()
    protocol_sha=hashlib.sha256((folder/'protocol.json').read_bytes()).hexdigest()
    corpus=json.loads((folder/'corpus.json').read_text(encoding='utf-8'));assert digest(corpus)==protocol['corpus_sha256']
    audit=json.loads((folder/'data-audit.json').read_text(encoding='utf-8'))
    assert audit['features_sha256']==hashlib.sha256((folder/'features.npz').read_bytes()).hexdigest()
    with np.load(folder/'features.npz',allow_pickle=False) as z:x,q,g=z['skills'],z['queries'],z['neighbours']
    initial=NetworkAdapter.load(Path(protocol['initial_checkpoint']))
    assert initial.metadata['weights_sha256']==protocol['initial_weights_sha256']
    ids=[n['id'] for n in corpus['nodes']];tasks=corpus['tasks'];by={n:i for i,n in enumerate(ids)}
    partitions={s:[i for i,t in enumerate(tasks) if t['split']==s] for s in ['train','validation','calibration','test','external_test','legacy_test_diagnostic']}
    final_indices=partitions['test']+partitions['external_test'];validation=partitions['validation'];train=partitions['train']
    assert train and validation and final_indices and partitions['calibration']
    def evaluate(adapter,indices):
        score=adapter.query(q[indices])@adapter.skills(x,graph=False).T
        return routing_metrics(score,[tasks[i] for i in indices],ids,corpus['pools'])
    baseline_validation=routing_metrics(q[validation]@x.T,[tasks[i] for i in validation],ids,corpus['pools'])
    import torch
    from torch import nn
    from torch.nn import functional as F
    torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu'
    X=torch.tensor(x,device=device);Q=torch.tensor(q,device=device)
    pos=torch.zeros((len(tasks),len(ids)),dtype=torch.bool,device=device)
    for i in train:pos[i,[by[n] for n in tasks[i]['gold']]]=True
    counts=Counter(tasks[i]['source'] for i in train)
    weights=torch.tensor([len(train)/(len(counts)*counts[t['source']]) if t['source'] in counts else 0. for t in tasks],device=device)
    class Trainable(nn.Module):
        def __init__(self):
            super().__init__();self.w=nn.ParameterDict({k:nn.Parameter(torch.tensor(v,device=device),requires_grad=k.startswith(('q_','s_'))) for k,v in initial.weights.items()})
        def query(self,z):return F.normalize(z+.25*(torch.tanh(z@self.w['q_down'])@self.w['q_up']),dim=-1)
        def skills(self):return F.normalize(X+.25*(torch.tanh(X@self.w['s_down'])@self.w['s_up']),dim=-1)
        def portable(self):return NetworkAdapter({k:v.detach().cpu().numpy() for k,v in self.w.items()},{'version':VERSION})
    candidates=[];started=time.monotonic()
    for coefficient in protocol['retention_coefficients']:
      for seed in protocol['seeds']:
        torch.manual_seed(seed);rng=np.random.default_rng(seed);model=Trainable()
        optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=protocol['learning_rate'],weight_decay=.01)
        name=f'retention-{coefficient:g}-seed-{seed}';trace=[]
        best=evaluate(model.portable(),validation);best_epoch=0;best_weights=copy.deepcopy(model.state_dict())
        print('Continuing',name,'on',device,'validation',round(best['source_family_macro'],4),flush=True)
        for epoch in range(protocol['epochs']):
            losses=[];supervised=[];retained=[]
            for start in range(0,len(train),protocol['batch_size']):
                # One deterministic shuffled traversal per epoch.
                if start==0:order=rng.permutation(train)
                chunk=order[start:start+protocol['batch_size']];inds=torch.tensor(chunk,device=device)
                adapted_q=model.query(Q[inds]);adapted_s=model.skills();scores=adapted_q@adapted_s.T
                logits=scores/protocol['temperature']
                info=((torch.logsumexp(logits,1)-torch.logsumexp(logits.masked_fill(~pos[inds],float('-inf')),1))*weights[inds]).mean()
                teacher=(Q[inds]@X.T)/protocol['teacher_temperature']
                retention=(1-(adapted_q*Q[inds]).sum(1)).mean()+(1-(adapted_s*X).sum(1)).mean()
                retention=retention+F.kl_div(F.log_softmax(scores/protocol['teacher_temperature'],dim=1),F.softmax(teacher,dim=1),reduction='batchmean')
                loss=info+coefficient*retention
                if not torch.isfinite(loss):raise ValueError('Nonfinite continuation loss')
                optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
                losses.append(float(loss.detach()));supervised.append(float(info.detach()));retained.append(float(retention.detach()))
            metric=evaluate(model.portable(),validation)
            trace.append(dict(epoch=epoch+1,loss=float(np.mean(losses)),supervised_loss=float(np.mean(supervised)),retention_loss=float(np.mean(retained)),validation_source_family_macro=metric['source_family_macro']))
            if metric['source_family_macro']>best['source_family_macro']+1e-10:
                best=metric;best_epoch=epoch+1;best_weights=copy.deepcopy(model.state_dict())
            if (epoch+1)%5==0:print(name,'epoch',epoch+1,'loss',round(trace[-1]['loss'],4),'validation',round(metric['source_family_macro'],4),flush=True)
        model.load_state_dict(best_weights);adapter=model.portable();directory=folder/'models'/name
        delta=float(np.sqrt(sum(np.square(adapter.weights[k]-initial.weights[k]).sum() for k in adapter.weights)))
        meta=adapter.save(directory,stage='research_candidate_not_admitted',protocol_sha256=protocol_sha,
            corpus_sha256=protocol['corpus_sha256'],encoder=protocol['encoder'],seed=seed,graph=False,
            active_trainable_parameters=protocol['active_trainable_parameters'],retention_coefficient=coefficient,
            selected_epoch=best_epoch,parent_weights_sha256=protocol['initial_weights_sha256'],parameter_delta_l2=delta)
        (directory/'training-curve.json').write_text(json.dumps(trace,indent=2),encoding='utf-8',newline='\n')
        source_safe=all(best['per_source_family_macro'][s]>=base-1e-10 for s,base in baseline_validation['per_source_family_macro'].items())
        candidates.append(dict(name=name,path=str(directory),model_id=meta['model_id'],weights_sha256=meta['weights_sha256'],
            retention_coefficient=coefficient,seed=seed,selected_epoch=best_epoch,parameter_delta_from_v1=delta,
            validation=best,validation_sources_nonregressing=source_safe,curve=trace))
    selected=max(candidates,key=lambda c:c['validation']['source_family_macro'])
    selection=dict(version='continuation-selection-v2',model_id=selected['model_id'],name=selected['name'],
        weights_sha256=selected['weights_sha256'],protocol_sha256=protocol_sha,selected_using='validation only',
        final_test_used=False,calibration_used=False,candidate_order=[c['name'] for c in candidates])
    (folder/'selection-before-calibration-and-test.json').write_text(json.dumps(selection,indent=2),encoding='utf-8',newline='\n')
    champion=NetworkAdapter.load(Path(selected['path']))
    # Calibration uses a fixed grid declared in the original frozen protocol.
    ci=partitions['calibration'];ct=[tasks[i] for i in ci];base_cal=q[ci]@x.T;raw_cal=champion.query(q[ci])@champion.skills(x,graph=False).T
    bm=routing_metrics(base_cal,ct,ids,corpus['pools']);calibration=[];cp=protocol['calibration_policy'];chosen_alpha=0.;best_cal_gain=0.
    for alpha in cp['alphas']:
        cm=routing_metrics((1-alpha)*base_cal+alpha*raw_cal,ct,ids,corpus['pools']);comparison=paired_routing_comparison(bm,cm)
        bad=defaultdict(bool)
        for b,c in zip(bm['rows'],cm['rows']):bad[(b['source'],b['family'])]|=c['recall5']<b['recall5']-1e-10
        failures=sum(bad.values());bound=0. if alpha==0 else binomial_risk_upper(failures,len(bad),cp['delta']/(len(cp['alphas'])-1))
        passes=bool(alpha and bound<=cp['target_incremental_family_regret'] and comparison['task_losses']==0)
        row=dict(alpha=alpha,reference_families=len(bad),families_with_any_regression=failures,
            conditional_family_regret_upper=bound,calibration_no_query_regression=comparison['task_losses']==0,
            passes_declared_calibration_rule=passes,**comparison);calibration.append(row)
        if passes and comparison['source_family_macro_gain']>best_cal_gain+1e-10:
            chosen_alpha=alpha;best_cal_gain=comparison['source_family_macro_gain']
    strength=dict(selected_alpha=chosen_alpha,selection='frozen calibration grid only',automatic_deployment=False,
        scope='conditional incremental reference-family regret; not task correctness or capability reward',
        assumptions=cp['independence'],candidates=calibration)
    (folder/'calibration-before-final-test.json').write_text(json.dumps(strength,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    fi=final_indices;ft=[tasks[i] for i in fi];base=q[fi]@x.T
    baseline=routing_metrics(base,ft,ids,corpus['pools'])
    v1=routing_metrics(initial.query(q[fi])@initial.skills(x,graph=False).T,ft,ids,corpus['pools'])
    for row in candidates:
        adapter=NetworkAdapter.load(Path(row['path']));row['final_test']=evaluate(adapter,fi)
    raw=champion.query(q[fi])@champion.skills(x,graph=False).T
    controlled=routing_metrics((1-chosen_alpha)*base+chosen_alpha*raw,ft,ids,corpus['pools'])
    legacy_indices=partitions['legacy_test_diagnostic']
    legacy_base=routing_metrics(q[legacy_indices]@x.T,[tasks[i] for i in legacy_indices],ids,corpus['pools'])
    legacy=evaluate(champion,legacy_indices)
    result=dict(version='continual-routing-research-v2',scope='Frozen capped SRA routing probe with 1660 candidates; not full SRA or end-task execution',
        protocol_sha256=protocol_sha,features_sha256=audit['features_sha256'],parent_model_id=initial.metadata['model_id'],
        selected_by_validation=selected['name'],model_id=selected['model_id'],selected_validation=stripped(selected['validation']),
        source_splits=protocol['source_splits'],pools=protocol['pools'],baseline_test=baseline,v1_test=v1,
        selected_test=selected['final_test'],controlled_test=controlled,calibration=strength,
        comparison_raw=paired_routing_comparison(baseline,selected['final_test']),comparison_controlled=paired_routing_comparison(baseline,controlled),
        comparison_vs_v1=paired_routing_comparison(v1,selected['final_test']),
        legacy_test_diagnostic=dict(boundary=protocol['prior_test_boundary'],baseline=stripped(legacy_base),candidate=stripped(legacy),comparison=paired_routing_comparison(legacy_base,legacy)),
        experiments=candidates,training_seconds=round(time.monotonic()-started,3),device=device,
        serving_changed=False,capability_rewards=0,limitations=protocol['limitations'])
    (folder/'final-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    bundle=folder/'product-bundle';champion.save(bundle,stage='research_candidate_not_admitted',
        selected_by_validation=selected['name'],recommended_shadow_alpha=chosen_alpha)
    local=[];names=[];shas=[]
    for i,n in enumerate(corpus['nodes']):
        for alias in n.get('aliases',[]):
            if alias.startswith('local/'):local.append(i);names.append(alias[6:]);shas.append(n['sha256'])
    np.savez_compressed(bundle/'catalog.npz',features=x[local],neighbours=g[local])
    (bundle/'catalog.json').write_text(json.dumps(dict(names=names,body_sha256=shas,
        file_sha256=hashlib.sha256((bundle/'catalog.npz').read_bytes()).hexdigest()),ensure_ascii=False),encoding='utf-8',newline='\n')
    public={k:result[k] for k in ['version','scope','protocol_sha256','features_sha256','parent_model_id','selected_by_validation','model_id','source_splits','pools','comparison_raw','comparison_controlled','comparison_vs_v1','legacy_test_diagnostic','training_seconds','device','serving_changed','capability_rewards','limitations','calibration','selected_validation']}
    for key in ['baseline_test','v1_test','selected_test','controlled_test']:public[key]=stripped(result[key])
    public['experiments']=[dict(name=c['name'],retention_coefficient=c['retention_coefficient'],seed=c['seed'],selected_epoch=c['selected_epoch'],parameter_delta_from_v1=c['parameter_delta_from_v1'],validation=stripped(c['validation']),final_test=stripped(c['final_test']),validation_sources_nonregressing=c['validation_sources_nonregressing']) for c in candidates]
    public['selected_training_curve']=selected['curve'];public['report_sha256']=digest(public)
    (folder/'public-report.json').write_text(json.dumps(public,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    print('Frozen final results',json.dumps({k:public[k] for k in ['model_id','selected_by_validation','baseline_test','v1_test','selected_test','controlled_test','comparison_raw','comparison_controlled']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
