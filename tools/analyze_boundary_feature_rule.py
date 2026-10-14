"""Explicitly POST-HOC diagnostic: is the new observation sufficient as a rule?

Never presented as preregistered performance or as proof learning is necessary.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet import conditional_utility as cu,conditional_boundary as cb


def analyze(work):
    load=lambda n:json.loads((work/n).read_text(encoding='utf-8'))
    cases=load('cases.json');frozen=load('predictions-frozen.json');records=load('executions.json');rows=[]
    for c in cases:
        prior=frozen['predictions'][c['id']];mask=prior['mask']
        f=cb.observe((work/c['path']).read_bytes(),c['intent'],mask)
        stop=not f['supported'] or any(f['vector'] or [])
        forced=next(r for r in records if r['task_id']==c['id'] and r['repeat']==0 and r['arm']=='forced_contract_diagnostic')
        rows.append({'task_id':c['id'],'reference_valid':forced['oracle']['reference_valid'],
                     'abstain':stop,'quality':int(not stop and forced['oracle']['deliverable'])})
    valid=[r for r in rows if r['reference_valid']]
    report={'version':'boundary-feature-rule-diagnostic-v1','defined_after_test':True,'created_at_ns':time.time_ns(),
        'source_report_sha256':load('report.json')['report_sha256'],
        'analysis_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'rule':'reject unsupported contract OR any of the three projected failure conditions; otherwise use the same explicit contract mask',
        'metrics':{'valid_tasks':len(valid),'valid_deliveries':sum(r['quality'] for r in valid),
                   'invalid_tasks':len(rows)-len(valid),'invalid_refusals':sum(r['abstain'] for r in rows if not r['reference_valid']),
                   'valid_false_refusals':sum(r['abstain'] for r in valid)},'rows':rows,
        'conclusion':'the finer observation also works as a direct rule; no demonstrated advantage of the learned head over a feature-matched rule',
        'reward_applied':False,'points':0}
    report['report_sha256']=cu.digest(report)
    path=work/'feature-rule-diagnostic.json'
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'defined_after_test':True,'metrics':report['metrics']}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);a=p.parse_args();analyze(a.work)
