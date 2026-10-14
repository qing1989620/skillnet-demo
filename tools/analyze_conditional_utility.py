"""Predeclare strong diagnostic baselines before unsealing, then analyze all arms.

This supplement does not alter the original frozen primary comparison. It is
deliberately recorded after training started and before sealed test execution.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet import conditional_utility as cu,utility_oracle
from tools.conditional_utility_lab import load,save,verify


def plan(work):
    protocol,cases=verify(work)
    if (work/'test-predictions-frozen.json').exists() or (work/'test-executions.json').exists():
        raise ValueError('supplement must be frozen before test starts')
    raw={'version':'conditional-utility-strong-baselines-v1','created_at_ns':time.time_ns(),
        'original_protocol_sha256':protocol['protocol_sha256'],
        'analysis_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'timing':'after training started, before sealed test prediction/outcome files; no primary protocol alteration',
        'baselines':{'none':'mask0, same common aggregator',
            'contract':'mask=sum of explicit true intent bits; reject unknown goal/schema',
            'contract_preflight':'contract plus reject bad test number, no test rows, all test values blank',
            'all':'mask7, original primary comparison'},
        'interpretation':'beating mask7 alone cannot establish learning is necessary or better than explicit contract rules'}
    raw['plan_sha256']=cu.digest(raw);save(work/'supplemental-baselines.json',raw)
    print(json.dumps(raw),flush=True)


def analyze(work):
    protocol,cases=verify(work);supp=load(work/'supplemental-baselines.json')
    if supp['analysis_code_sha256']!=hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise ValueError('supplementary analysis code changed')
    frozen=load(work/'test-predictions-frozen.json')
    if supp['created_at_ns']>=frozen['created_at_ns']:raise ValueError('baseline selected after test')
    records=load(work/'test-executions.json');lookup={(r['task_id'],r['repeat'],r['mask']):r for r in records}
    selected=[c for c in cases if c['split']=='sealed_test'];rows=[]
    for c in selected:
        pred=frozen['predictions'][c['id']];f=pred['observed'];flags=f['features']
        mask=sum((1<<j)*int(c['intent'][k]) for j,k in enumerate(cu.KEYS))
        supported=f['supported_contract']
        preflight=supported and not flags['has_bad_test_number'] and flags['has_test'] and not flags['all_test_blank']
        choices={'none':0,'all':7,'contract':mask if supported else None,
                 'contract_preflight':mask if preflight else None,'learned':pred['mask']}
        valid=utility_oracle.evaluate((work/c['path']).read_bytes(),c['intent'],None)['reference_valid']
        for strategy,m in choices.items():
            actual=lookup.get((c['id'],0,m)) if m is not None else None
            rows.append({'task_id':c['id'],'strategy':strategy,'reference_valid':valid,
                         'mask':m,'quality':actual['quality'] if actual else 0,
                         'abstain':m is None,'execution_failed':bool(actual and actual['execution_failure'])})
    metrics={}
    for strategy in ('none','all','contract','contract_preflight','learned'):
        part=[r for r in rows if r['strategy']==strategy];valid=[r for r in part if r['reference_valid']]
        metrics[strategy]={'valid_tasks':len(valid),'verified_delivery_rate':sum(r['quality'] for r in valid)/len(valid) if valid else 0,
            'invalid_tasks':len(part)-len(valid),'invalid_abstentions':sum(r['abstain'] for r in part if not r['reference_valid']),
            'invalid_execution_attempts':sum(not r['abstain'] for r in part if not r['reference_valid'])}
    # Selected concrete observations illustrate effect reversal; the complete
    # effect distribution is reported so examples do not stand in for evaluation.
    effects=[]
    for c in selected:
        q=[lookup[(c['id'],0,m)]['quality'] for m in range(8)]
        for j,k in enumerate(cu.KEYS):
            d=sum(q[m|(1<<j)]-q[m] for m in range(8) if not m&(1<<j))/4
            effects.append({'task_id':c['id'],'skill':k,'observed_marginal_gain':d,
                            'predicted_marginal_gain':frozen['predictions'][c['id']]['marginal'][j]['predicted_marginal_gain']})
    distributions={k:{'positive':sum(e['skill']==k and e['observed_marginal_gain']>0 for e in effects),
                       'negative':sum(e['skill']==k and e['observed_marginal_gain']<0 for e in effects),
                       'zero':sum(e['skill']==k and e['observed_marginal_gain']==0 for e in effects)} for k in cu.KEYS}
    result={'version':'conditional-utility-strong-baselines-v1','protocol_sha256':protocol['protocol_sha256'],
            'supplement_plan_sha256':supp['plan_sha256'],'metrics':metrics,'effects':effects,
            'effect_distribution':distributions,'rows':rows,
            'conclusion':supp['interpretation'],'reward_applied':False,'points':0}
    result['report_sha256']=cu.digest(result);save(work/'strong-baselines.json',result)
    print(json.dumps({'metrics':metrics,'effect_distribution':distributions},ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['plan','analyze'])
    p.add_argument('--work',type=Path,required=True);a=p.parse_args();globals()[a.stage](a.work.absolute())
