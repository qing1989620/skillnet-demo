"""Freeze a multi-source continuation study before embeddings or gradients."""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import hashlib,json,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet.learned_network import digest,normalize
from skillnet.routing_research import grouped_source_split,query_fingerprint
from skillnet.reward_gates import policy_sha256
from skillnet.semantic import DenseIndex

SOURCES=('bigcodebench','champ','logicbench','medcalcbench','theoremqa','toolqa')
PIN='277fd8d2bbd7d3b81a5cf4ffa6e87e18c7906e4f'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sra-data',type=Path,required=True)
    parser.add_argument('--prior-experiment',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--prior-external-questions',type=Path,required=True)
    parser.add_argument('--initial-model',type=Path,default=ROOT/'data/network-model',help='Fixed delivered v1 weights; do not require a hardware-identical retraining')
    a=parser.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=True)
    if (out/'protocol.json').exists():raise SystemExit('Frozen experiment exists; use a new output directory')
    manifest=json.loads((a.sra_data/'manifest.json').read_text(encoding='utf-8'));assert manifest['commit']==PIN
    for row in manifest['files']:
        assert hashlib.sha256((a.sra_data/row['local_name']).read_bytes()).hexdigest()==row['sha256']
    old=json.loads((a.prior_experiment/'corpus.json').read_text(encoding='utf-8'))
    prior_protocol=json.loads((a.prior_experiment/'protocol.json').read_text(encoding='utf-8'))
    assert digest(old)==prior_protocol['corpus_sha256']
    checkpoint=a.initial_model
    initial_sha=hashlib.sha256((checkpoint/'model.npz').read_bytes()).hexdigest()
    assert initial_sha=='b9e7622390ddc71633586f71bce15960940801808693eea2189d2835c267f3f5'
    previous_queries={query_fingerprint(t['query']) for t in old['tasks']}
    for line in a.prior_external_questions.read_text(encoding='utf-8').splitlines():
        t=json.loads(line);previous_queries.add(query_fingerprint(t['instruction_text']))
    # Both inspected schema rows are excluded from the new study.
    excluded=set(manifest.get('schema_preview_ids',[]));sra=[];removed=[]
    for source in SOURCES:
        for t in json.loads((a.sra_data/(source+'.json')).read_text(encoding='utf-8')):
            if t['instance_id'] in excluded or query_fingerprint(t['question']) in previous_queries:
                removed.append(t['instance_id']);continue
            sra.append(dict(id='sra/'+t['instance_id'],source=source,query=t['question'],
                gold=['sra/'+n for n in sorted(set(t['skill_annotations']))],pool='sra'))
    assignments=grouped_source_split(sra)
    by_bucket=defaultdict(list)
    for t in sra:
        t['split'],t['family']=assignments[t['id']];by_bucket[(t['source'],t['split'])].append(t)
    caps=dict(train=200,validation=80,calibration=80,test=100,external_test=150)
    selected=[]
    for (source,split),rows in sorted(by_bucket.items()):
        selected.extend(sorted(rows,key=lambda t:hashlib.sha256(t['id'].encode()).hexdigest())[:caps[split]])
    # Skill documents are public transductive data. No final query or answer is
    # used to select registry distractors or update the model.
    full=json.loads((a.sra_data/'corpus.json').read_text(encoding='utf-8'))
    gold={n[4:] for t in sra for n in t['gold']}
    assert len(gold)==636
    pool_gold=[s for s in full if s['skill_id'] in gold]
    distractors=sorted((s for s in full if s['skill_id'] not in gold),
        key=lambda s:hashlib.sha256(s['skill_id'].encode()).hexdigest())[:1024]
    nodes=list(old['nodes']);old_count=len(nodes)
    for s in sorted(pool_gold+distractors,key=lambda s:s['skill_id']):
        body=str(s['content']).replace('\r\n','\n').strip()
        nodes.append(dict(id='sra/'+s['skill_id'],name=s['name'],body=body,
            view=s['description'] or s['name'],source='sra',sha256=hashlib.sha256(body.encode()).hexdigest(),aliases=[]))
    del full
    tasks=[]
    for t in old['tasks']:
        row=dict(t);row['id']='gymv1/'+t['id'];row['source']='gymv1';row['pool']='gymv1'
        if row['split']=='test':row['split']='legacy_test_diagnostic'
        tasks.append(row)
    tasks.extend(sorted(selected,key=lambda t:t['id']))
    seen={};query_cross=[];family_cross=[]
    for t in tasks:
        q=query_fingerprint(t['query'])
        if q in seen and seen[q]!=t['split']:query_cross.append(t['id'])
        seen[q]=t['split']
    for source in SOURCES:
        groups=defaultdict(set)
        for t in tasks:
            if t['source']==source:groups[t['family']].add(t['split'])
        family_cross.extend(k for k,v in groups.items() if len(v)>1)
    assert not query_cross and not family_cross
    pools=dict(gymv1=list(range(old_count)),sra=list(range(old_count,len(nodes))))
    corpus=dict(version='continual-routing-corpus-v2',nodes=nodes,tasks=tasks,pools=pools,
        upstream_commit=PIN,excluded_inspected_or_overlapping=removed)
    (out/'corpus.json').write_text(json.dumps(corpus,ensure_ascii=False),encoding='utf-8',newline='\n')
    protocol=dict(version='continual-routing-protocol-v2',frozen_before_embeddings_and_training=True,
        reward_policy_sha256=policy_sha256(),corpus_sha256=digest(corpus),
        upstream_commit=PIN,upstream_manifest_sha256=hashlib.sha256((a.sra_data/'manifest.json').read_bytes()).hexdigest(),
        initial_weights_sha256=initial_sha,initial_checkpoint=str(checkpoint.resolve()),
        encoder=prior_protocol['encoder'],seeds=[17,29],retention_coefficients=[0.,1.,4.],epochs=40,
        learning_rate=.001,batch_size=32,temperature=.07,teacher_temperature=.2,
        loss='source-balanced multi-positive InfoNCE + coefficient*(query cosine drift + skill cosine drift + KL(frozen E5 teacher || candidate))',
        graph_messages=False,active_trainable_parameters=73728,architecture_parameters=110596,
        selection='highest validation source/family-macro Recall@5; ties retain earlier epoch, then lower retention coefficient and seed; no final test used',
        validation_feasibility='report source-wise non-regression; no validation metric grants twelve-gate approval',
        pools={k:len(v) for k,v in pools.items()},caps=caps,
        splits=dict(Counter(t['split'] for t in tasks)),
        source_splits={s:dict(Counter(t['split'] for t in tasks if t['source']==s)) for s in ['gymv1',*SOURCES]},
        split_rule='same query and exact reference set form connected components; hash-order components per source; 20/20/20/40 test/validation/calibration/train; theoremqa and bigcodebench only external',
        prior_test_boundary='Gym test was exposed in v1 and is only a legacy regression diagnostic',
        reference_boundary='Attached/annotated skill IDs are retrieval references, not necessarily minimal or causally necessary skills',
        statistics='Report all paired query and component outcomes. Reference-family sign statistic is descriptive under independence assumptions; deterministic rechecks do not increase N.',
        calibration_use='Never gradient training. Reserved for declared safety-policy analysis after checkpoint selection, before final evaluation.',
        calibration_policy=dict(alphas=[0.,.25,.5,.75,1.],target_incremental_family_regret=.1,delta=.05,
            correction='Bonferroni over four nonzero strengths; validation selects one checkpoint independently of calibration',
            selection='highest calibration source/family-macro gain among nonzero strengths with no observed query regressions and risk upper <= .1; otherwise exact frozen-E5 fallback alpha=0',
            independence='Binomial bounds require independent exchangeable reference-family units; this assumption is not established by the benchmark and is not an anytime-valid certificate'),
        prior_external_questions_sha256=hashlib.sha256(a.prior_external_questions.read_bytes()).hexdigest(),
        deployment='No automatic production promotion or capability rewards from routing recall alone',
        training_script_sha256=hashlib.sha256((ROOT/'tools/train_continual_routing.py').read_bytes()).hexdigest(),
        metric_code_sha256=hashlib.sha256((ROOT/'skillnet/routing_research.py').read_bytes()).hexdigest(),
        limitations=['Reduced SRA pool of 1660, not full 26262 benchmark','Capped hash-selected task sample, not full 5400 task execution','Public skill documents are transductive inputs','No end-task execution or causal capability claim','Source and reference-family dependence can invalidate iid interpretation'])
    (out/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    print('Frozen study',json.dumps({k:protocol[k] for k in ['splits','source_splits','pools']},ensure_ascii=False),flush=True)
    with np.load(a.prior_experiment/'features.npz',allow_pickle=False) as z:
        old_x,old_q=z['skills'],z['queries'];old_g=z['neighbours']
    enc=DenseIndex(ROOT/'.models/multilingual-e5-small')
    assert enc.status['revision']==protocol['encoder']['revision']
    texts=[]
    for n in nodes[old_count:]:
        body=n['body'];middle=max(0,len(body)//2-500);texts.extend([body[:1100],body[middle:middle+1100],body[-1100:]])
    parts=[]
    for start in range(0,len(texts),96):
        parts.append(enc.embed(texts[start:start+96],'passage: '));print('New public skill views',min(start+96,len(texts)),'/',len(texts),flush=True)
    views=np.concatenate(parts).reshape(len(nodes)-old_count,3,384)
    new_x=normalize((views*np.array([.55,.25,.2],np.float32)[None,:,None]).sum(1))
    x=np.concatenate([old_x,new_x]);qparts=[old_q]
    new_tasks=tasks[len(old['tasks']):]
    for start in range(0,len(new_tasks),96):
        qparts.append(enc.embed([t['query'] for t in new_tasks[start:start+96]],'query: '));print('New questions',min(start+96,len(new_tasks)),'/',len(new_tasks),flush=True)
    q=np.concatenate(qparts);g=np.concatenate([old_g,np.zeros((len(new_x),4,384),np.float32)])
    np.savez_compressed(out/'features.npz',skills=x,queries=q,neighbours=g)
    audit=dict(query_overlap_across_splits=query_cross,reference_component_overlap_across_splits=family_cross,
        final_questions_used_for_gradient=False,source_splits=protocol['source_splits'],
        protocol_sha256=hashlib.sha256((out/'protocol.json').read_bytes()).hexdigest(),
        features_sha256=hashlib.sha256((out/'features.npz').read_bytes()).hexdigest())
    (out/'data-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    print('Frozen continuation data ready',json.dumps(audit,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
