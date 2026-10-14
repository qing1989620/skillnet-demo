"""Fresh Iris sealing for the v1 group-boundary discovery; no test-label training."""
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
import numpy as np
from skillnet import conditional_boundary as cb,conditional_utility as cu,utility_ops,utility_oracle,reward_gates
from tools.conditional_utility_lab import save,load,verify as verify_prior,csv_bytes,contract,perturb


def prepare(work,prior):
    prior_protocol,prior_cases=verify_prior(prior)
    if work.exists():raise ValueError('boundary experiment needs fresh directory')
    work.mkdir(parents=True)
    url='https://archive.ics.uci.edu/static/public/53/iris.zip'
    with urllib.request.urlopen(url,timeout=30) as response:raw=response.read(100001)
    if len(raw)>100000:raise ValueError('source byte bound')
    (work/'iris.zip').write_bytes(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        info=z.getinfo('iris.data')
        if info.file_size>20000:raise ValueError('source expanded bound')
        data=z.read('iris.data')
    (work/'iris.data').write_bytes(data)
    original=[r for r in csv.reader(io.StringIO(data.decode())) if r]
    if len(original)!=150 or any(len(r)!=5 for r in original):raise ValueError('unexpected source shape')
    cases=[]
    for i in range(40):
        name=f'iris-sealed-{i:02d}'
        ids=sorted(range(150),key=lambda j:hashlib.sha256(f'{name}:{j}'.encode()).digest())[:24]
        rows=[[name+'-'+str(j),name+'-subject-'+str(j),'train' if n<4 else 'test',original[j][4],original[j][0]] for n,j in enumerate(ids)]
        intent=contract(i%8);kind='valid_measurements'
        if 10<=i<30:
            for g in range(1+i%3):
                rows.append([name+f'-blank-{g}',name+f'-blank-subject-{g}','test',f'new-empty-group-{g}',' '])
            intent=contract((i%4)|4 if i<20 else i%4)
            kind='blank_groups_removed_by_contract' if i<20 else 'blank_groups_must_be_preserved'
        elif 30<=i<34:
            rows[-1][4]=['7 cm','NaN','Infinity','bad'][i-30];kind='bad_numeric'
        elif 34<=i<38:
            for r in rows:r[2]='holdout'
            kind='unsupported_partition'
        elif i==38:intent['goal']='weighted_median';kind='unknown_goal'
        elif i==39:kind='unknown_schema'
        if i<10:rows=perturb(rows,i%8,name)
        blob=csv_bytes(rows,utility_ops.HEADER if i!=39 else ['sample_id','subject_id','split','category','value'])
        path='inputs/'+name+'.csv';(work/'inputs').mkdir(exist_ok=True);(work/path).write_bytes(blob)
        cases.append({'id':name,'path':path,'input_sha256':hashlib.sha256(blob).hexdigest(),'intent':intent,
            'kind':kind,'source_row_indices':ids,'source':'UCI Iris / sepal length in cm / controlled transformations'})
    save(work/'cases.json',cases)
    code=['skillnet/conditional_boundary.py','tools/conditional_boundary_lab.py']
    protocol={'version':'conditional-boundary-experiment-v2','created_at_ns':time.time_ns(),
        'discovery':'v1 sealed-boundary-new-empty-group; original v1 results remain unchanged',
        'prior_protocol_sha256':prior_protocol['protocol_sha256'],
        'training_source':'only prior train-executions.json; v1 discovery/test outcomes excluded',
        'training_records_sha256':hashlib.sha256((prior/'train-executions.json').read_bytes()).hexdigest(),
        'calibration_records_sha256':hashlib.sha256((prior/'calibration-executions.json').read_bytes()).hexdigest(),
        'source':{'url':url,'license':'CC BY 4.0','citation':'Fisher, R. (1936). Iris. UCI. doi:10.24432/C56C76',
                  'zip_sha256':hashlib.sha256(raw).hexdigest(),'data_sha256':hashlib.sha256(data).hexdigest(),
                  'note':'published measurements; authored missing groups/units/splits are experimental perturbations'},
        'cases_sha256':hashlib.sha256((work/'cases.json').read_bytes()).hexdigest(),
        'code_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in code},
        'reward_policy_sha256':reward_gates.policy_sha256(),'operator_code_sha256':utility_ops.CODE_SHA,
        'training':{'steps':1200,'learning_rate':.2,'l2':.002},'threshold_grid':[.1,.25,.5,.75],
        'selection':'no false refusals on prior calibration executable arms; maximum failure recall; ties highest threshold',
        'arms':['contract_preflight_v1','learned_boundary_v2','forced_contract_diagnostic'],
        'repeats':2,'order':'hash(task:repeat:arm) frozen before results',
        'primary':'invalid task refusal BEFORE executing; valid deliverable non-regression',
        'not_primary':'refusing an invalid task is not an improvement in valid-task output quality or an improvement reward',
        'limits':['one fresh public source','tasks share source measurements','human-designed feature repair',
                  'projected preconditions are not actual execution evidence','no generic network improvement or causal-calibration guarantee']}
    protocol['protocol_sha256']=cu.digest(protocol);save(work/'protocol.json',protocol)
    print(json.dumps({'protocol_sha256':protocol['protocol_sha256'],'fresh_tasks':40}),flush=True)


def checked(work,prior):
    p=load(work/'protocol.json');verify_prior(prior)
    if p['protocol_sha256']!=cu.digest({k:v for k,v in p.items() if k!='protocol_sha256'}):raise ValueError('protocol changed')
    for name,sha in p['code_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha:raise ValueError('frozen boundary code changed')
    for file,field in [('train-executions.json','training_records_sha256'),('calibration-executions.json','calibration_records_sha256')]:
        if hashlib.sha256((prior/file).read_bytes()).hexdigest()!=p[field]:raise ValueError('training/calibration records changed')
    if p['reward_policy_sha256']!=reward_gates.policy_sha256() or p['operator_code_sha256']!=utility_ops.CODE_SHA:
        raise ValueError('policy/program changed')
    cases=load(work/'cases.json')
    if hashlib.sha256((work/'cases.json').read_bytes()).hexdigest()!=p['cases_sha256']:raise ValueError('cases changed')
    for c in cases:
        if hashlib.sha256((work/c['path']).read_bytes()).hexdigest()!=c['input_sha256']:raise ValueError('input changed')
    return p,cases


def train(work,prior):
    p,cases=checked(work,prior);old={c['id']:c for c in load(prior/'cases.json')}
    records=load(prior/'train-executions.json');x=[];y=[]
    for r in records:
        case=old[r['task_id']]
        if case['split']!='train':raise ValueError('test row entered boundary training')
        o=cb.observe((prior/case['path']).read_bytes(),case['intent'],r['mask'])
        x.append(o['vector']);y.append(r['execution_failure'])
    model=cb.fit(x,y);model.update(protocol_sha256=p['protocol_sha256'],operator_code_sha256=utility_ops.CODE_SHA,
        training_records_sha256=p['training_records_sha256'])
    cb.validate(model);save(work/'model.json',model)
    cal=load(prior/'calibration-executions.json');comparisons=[]
    for threshold in p['threshold_grid']:
        false_refusals=correct_refusals=failures=0
        for r in cal:
            case=old[r['task_id']];raw=(prior/case['path']).read_bytes()
            pred=cb.predict(model,cb.observe(raw,case['intent'],r['mask']),threshold)
            failed=bool(r['execution_failure']);failures+=failed
            false_refusals+=int(pred['abstain'] and not failed);correct_refusals+=int(pred['abstain'] and failed)
        comparisons.append({'threshold':threshold,'false_refusals':false_refusals,'correct_refusals':correct_refusals,'failures':failures})
    good=[r for r in comparisons if r['false_refusals']==0]
    chosen=max(good,key=lambda r:(r['correct_refusals'],r['threshold']))['threshold'] if good else None
    save(work/'selection.json',{'created_at_ns':time.time_ns(),'model_sha256':cu.digest(model),'threshold':chosen,
                              'comparisons':comparisons,'statistical_certificate':False})
    print(json.dumps({'model_sha256':cu.digest(model),'coefficients':model['coefficients'],'threshold':chosen,'calibration':comparisons}),flush=True)


def test(work,prior):
    p,cases=checked(work,prior);model=load(work/'model.json');selection=load(work/'selection.json')
    if selection['model_sha256']!=cu.digest(model) or selection['threshold'] is None:raise ValueError('no calibrated candidate')
    predictions={}
    for c in cases:
        mask=sum(1<<j for j,k in enumerate(cu.KEYS) if c['intent'][k])
        raw=(work/c['path']).read_bytes();base=cu.features(raw,c['intent']);flags=base['features']
        before=base['supported_contract'] and not flags['has_bad_test_number'] and flags['has_test'] and not flags['all_test_blank']
        after=cb.predict(model,cb.observe(raw,c['intent'],mask),selection['threshold'])
        predictions[c['id']]={'mask':mask,'baseline_abstain':not before,'candidate':after}
    frozen={'created_at_ns':time.time_ns(),'predictions':predictions,'model_sha256':cu.digest(model)}
    save(work/'predictions-frozen.json',frozen)
    records=[]
    for c in cases:
        raw=(work/c['path']).read_bytes();pred=predictions[c['id']]
        for repeat in range(2):
            arms=sorted(p['arms'],key=lambda a:hashlib.sha256(f'{c["id"]}:{repeat}:{a}'.encode()).digest())
            for arm in arms:
                abstain=pred['baseline_abstain'] if arm=='contract_preflight_v1' else pred['candidate']['abstain'] if arm=='learned_boundary_v2' else False
                folder=work/'executions'/c['id']/f'r{repeat}-{arm}'
                execution=None
                if not abstain:execution=utility_ops.execute(pred['mask'],work/c['path'],folder)
                oracle=utility_oracle.evaluate(raw,c['intent'],folder if execution else None)
                records.append({'task_id':c['id'],'repeat':repeat,'arm':arm,'abstain':abstain,
                                'directory':folder.relative_to(work).as_posix() if execution else None,
                                'execution':execution,'oracle':oracle})
        if len(records)%60==0:print(f'boundary: {len(records)//6}/40 new tasks',flush=True)
    save(work/'executions.json',records)
    metrics={}
    for arm in p['arms']:
        rows=[r for r in records if r['arm']==arm];valid=[r for r in rows if r['oracle']['reference_valid']]
        metrics[arm]={'valid_tasks':len(valid)//2,'invalid_tasks':(len(rows)-len(valid))//2,
            'valid_deliveries':sum(r['oracle']['deliverable'] for r in valid)//2,
            'invalid_refusals':sum(r['abstain'] for r in rows if not r['oracle']['reference_valid'])//2,
            'invalid_execution_attempts':sum(not r['abstain'] for r in rows if not r['oracle']['reference_valid'])//2,
            'valid_false_refusals':sum(r['abstain'] for r in valid)//2,
            'subprocesses':sum(r['execution'] is not None for r in rows)}
    errors=[]
    for r in records:
        c=next(c for c in cases if c['id']==r['task_id']);folder=work/r['directory'] if r['directory'] else None
        if utility_oracle.evaluate((work/c['path']).read_bytes(),c['intent'],folder)!=r['oracle']:errors.append(r['task_id'])
        if r['execution']:
            if r['execution']['started_at_ns']<=frozen['created_at_ns']:errors.append('late prediction')
            for name,meta in r['execution']['artifacts'].items():
                blob=(folder/name).read_bytes()
                if hashlib.sha256(blob).hexdigest()!=meta['sha256']:errors.append('artifact changed')
    result={'version':cb.VERSION,'protocol_sha256':p['protocol_sha256'],'model_sha256':cu.digest(model),
        'metrics':metrics,'artifact_audit':{'ok':not errors,'errors':errors,'arms':len(records)},
        'training_execution_rows':len(load(prior/'train-executions.json')),
        'test_tasks':len(cases),'source':p['source'],'limitations':p['limits'],
        'reward_applied':False,'points':0,'formal_routing_deployed':False,
        'conclusion':'failure avoidance is separate from verified valid-task quality gain; no improvement reward'}
    result['report_sha256']=cu.digest(result);save(work/'report.json',result)
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('stage',choices=['prepare','train','test'])
    a.add_argument('--work',type=Path,required=True);a.add_argument('--prior',type=Path,required=True)
    args=a.parse_args();globals()[args.stage](args.work.absolute(),args.prior.absolute())
