"""Prepare -> freeze -> train -> calibrate -> sealed real execution, in that order.

All artifacts are local, publicly reproducible, and outside customer run state.
The optional LLM contrast is a separate, budgeted study over reviewed actions.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import random
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from skillnet import conditional_utility as cu, reward_gates, utility_ops, utility_oracle

VERSION = 'conditional-utility-experiment-v1'
SOURCE_COMMIT = '8957207b78d6ccd1b4654a9dd9c9041b657478ab'
SOURCE_ROOT = f'https://raw.githubusercontent.com/allisonhorst/palmerpenguins/{SOURCE_COMMIT}/'
CODE_FILES = ['skillnet/conditional_utility.py', 'skillnet/utility_ops.py',
              'skillnet/utility_oracle.py', 'tools/conditional_utility_lab.py',
              'tools/conditional_llm_contrast.py']
REPEATS = 2


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Completed stage records cannot be silently replaced or tuned after test.
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def csv_bytes(rows, header=utility_ops.HEADER):
    f = io.StringIO(newline='')
    w = csv.writer(f, lineterminator='\n'); w.writerow(header); w.writerows(rows)
    return f.getvalue().encode('utf-8')


def synthetic_rows(seed: str):
    rng = random.Random(seed)
    return [[f'{seed}-{i}', f'{seed}-entity-{i}', 'train' if i < 4 else 'test',
             'A' if i % 2 else 'B', f'{rng.randrange(100,900)/10:.1f}'] for i in range(16)]


def perturb(rows, mask, tag):
    rows = [list(r) for r in rows]
    if mask & 1:
        duplicate = list(rows[-1]); duplicate[4] = '123.40'; rows.append(duplicate)
    if mask & 2:
        leak = list(rows[0]); leak[0] = tag + '-leak'; leak[2] = 'test'; rows.append(leak)
    if mask & 4:
        missing = list(rows[-2]); missing[0] = tag + '-blank'; missing[1] = tag + '-blank-person'
        missing[2] = 'test'; missing[4] = ''; rows.append(missing)
    return rows


def contract(mask):
    return {**{k: bool(mask & (1 << j)) for j,k in enumerate(cu.KEYS)}, 'goal': 'group_mean'}


def prepare(work: Path):
    if work.exists():
        raise ValueError('prepare needs a fresh experiment directory')
    work.mkdir(parents=True)
    sources = {}
    for name, rel in [('penguins.csv','inst/extdata/penguins.csv'), ('LICENSE.md','LICENSE.md')]:
        with urllib.request.urlopen(SOURCE_ROOT + rel, timeout=30) as response:
            raw = response.read(100001)
        if len(raw) > 100000:
            raise ValueError('public source exceeds declared bound')
        (work / name).write_bytes(raw)
        sources[name] = {'url': SOURCE_ROOT + rel, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    original = list(csv.DictReader(io.StringIO((work/'penguins.csv').read_text(encoding='utf-8'))))
    cases = []
    def add(name, split, rows, intent, kind, **meta):
        raw = csv_bytes(rows)
        path = 'inputs/' + name + '.csv'
        (work / 'inputs').mkdir(exist_ok=True)
        (work / path).write_bytes(raw)
        cases.append({'id': name, 'split': split, 'path': path,
                      'input_sha256': hashlib.sha256(raw).hexdigest(), 'intent': intent,
                      'task': f'{name}: 对 test 分组求计数、有效数、和、均值。清洗策略为 {json.dumps(intent,sort_keys=True)}；保留原单元格。',
                      'kind': kind, **meta})
    for split, copies in [('train',2),('calibration',1)]:
        for policy, defects, copy in itertools.product(range(8), range(8), range(copies)):
            name = f'{split}-p{policy}-d{defects}-v{copy}'
            add(name, split, perturb(synthetic_rows(name), defects, name), contract(policy), 'synthetic_control',
                condition_cell=f'p{policy}-d{defects}')
    # Boundaries are learned from executed failure outcomes, never from names.
    for split, policies in [('train', range(8)), ('calibration', [0])]:
        for mode, policy in itertools.product(('no-test','all-blank','bad-number','nonfinite'), policies):
            name = f'{split}-{mode}-p{policy}'
            rows = synthetic_rows(name)
            if mode == 'no-test':
                for r in rows: r[2] = 'train'
            elif mode == 'all-blank':
                for r in rows:
                    if r[2] == 'test': r[4] = ''
            else:
                rows[-1][4] = 'not-a-number' if mode == 'bad-number' else 'NaN'
            add(name, split, rows, contract(policy), 'synthetic_boundary', boundary=mode)
    # Entire new public source is excluded from both training and calibration.
    # These are engineering transformations of real measurements, not a claim
    # that injected duplicates/splits were defects in the original scientific data.
    for i in range(32):
        name = f'sealed-penguins-{i:02d}'
        pool = sorted(range(len(original)), key=lambda j: hashlib.sha256(f'{name}:{j}'.encode()).digest())[:28]
        rows = []
        for j, index in enumerate(pool):
            row = original[index]
            rows.append([name + '-' + str(index), name + '-subject-' + str(index),
                         'train' if j < 4 else 'test', row['species'],
                         '' if row['bill_length_mm'] == 'NA' else row['bill_length_mm']])
        defects = (i // 8 * 3 + i % 8) % 8
        add(name, 'sealed_test', perturb(rows, defects, name), contract(i % 8), 'public_measurements_with_controlled_perturbations',
            source='palmerpenguins', source_row_indices=pool, injected_defects_mask=defects,
            condition_cell=f'p{i%8}-d{defects}')
    for i, mode in enumerate(('no-test','all-blank','bad-number','nonfinite','unknown-goal','bad-schema','new-unit','new-empty-group')):
        name = 'sealed-boundary-' + mode
        rows, intent = synthetic_rows(name), contract(i % 8)
        if mode == 'no-test':
            for r in rows: r[2] = 'validation'
        elif mode == 'all-blank':
            for r in rows:
                if r[2] == 'test': r[4] = '  '
        elif mode in ('bad-number','nonfinite','new-unit'):
            rows[-1][4] = {'bad-number':'broken42','nonfinite':'Infinity','new-unit':'42 mm'}[mode]
        elif mode == 'unknown-goal': intent['goal'] = 'weighted_median'
        elif mode == 'new-empty-group':
            rows.append([name+'-x',name+'-e','test','unseen-group',''])
            intent = contract(0)
        add(name,'sealed_test',rows,intent,'synthetic_boundary',boundary=mode)
        if mode == 'bad-schema':
            path = work / cases[-1]['path']; raw = csv_bytes(rows, ['sample_id','subject_id','partition','group','value'])
            path.write_bytes(raw); cases[-1]['input_sha256'] = hashlib.sha256(raw).hexdigest()
    hashes = [c['input_sha256'] for c in cases]
    if len(set(hashes)) != len(hashes):
        raise ValueError('cross-split input duplicate')
    save(work/'cases.json', cases)
    from skillnet import config
    protocol = {'version': VERSION, 'created_at_ns': time.time_ns(), 'sources': sources,
        'cases_sha256': hashlib.sha256((work/'cases.json').read_bytes()).hexdigest(),
        'splits': {s:[c['id'] for c in cases if c['split']==s] for s in ('train','calibration','sealed_test')},
        'code_sha256': {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in CODE_FILES},
        'operator_code_sha256': utility_ops.CODE_SHA, 'oracle_version': utility_oracle.VERSION,
        'reward_policy_sha256': reward_gates.policy_sha256(), 'model': {'type':'multioutput_binary_CART','max_depth':8,'min_leaf':2},
        'calibration_threshold_grid':[.5,.75,1.0], 'calibration_rule':'zero observed deliverable regressions vs mask7, then maximum valid delivery; ties highest threshold',
        'test_repeats':REPEATS, 'all_masks':list(range(8)), 'baseline_mask':7,
        'paired_order':'sha256(task:repeat:mask), no outcome-dependent ordering',
        'primary':'verified deliverable rate on reference-valid tasks; every original cell and summary field checked',
        'secondary':['marginal utility MAE','failure Brier score','support coverage','all regressions','abstention on invalid tasks'],
        'statistical_units':'task means; repeats are deterministic stability checks, not additional independent samples; one real public source',
        'llm':{'model_alias':config.MODEL,'temperature':.2,'max_tokens':256,'retries':1,
               'task_ids':[c['id'] for c in cases if c['split']=='sealed_test' and
                    (c['id'].startswith('sealed-penguins-') and int(c['id'][-2:]) < 8 or c.get('boundary') in ('no-test','bad-number','unknown-goal','new-empty-group'))],
               'repeats':2,'arms':['plain','evidence'],'arm_order':'plain,evidence on repeat0; evidence,plain on repeat1',
               'actions':'mask integer 0..7 or reject; same reviewed executor and independent oracle',
               'max_requests':48, 'max_total_estimated_yuan':20},
        'limitations':['controlled defects are authored','public-source tasks share measurements','no proof of LLM pretraining independence',
                       'finite registry of three skills, not all 1881 skills','no production promotion based on this research report']}
    protocol['protocol_sha256'] = cu.digest(protocol)
    save(work/'protocol.json',protocol)
    print(json.dumps({'prepared':str(work),'splits':{k:len(v) for k,v in protocol['splits'].items()},'protocol_sha256':protocol['protocol_sha256']}),flush=True)


def verify(work):
    protocol = load(work/'protocol.json')
    if protocol['protocol_sha256'] != cu.digest({k:v for k,v in protocol.items() if k!='protocol_sha256'}):
        raise ValueError('protocol digest changed')
    if protocol['reward_policy_sha256'] != reward_gates.policy_sha256():
        raise ValueError('reward policy changed')
    for path, sha in protocol['code_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != sha:
            raise ValueError('frozen code changed: ' + path)
    if hashlib.sha256((work/'cases.json').read_bytes()).hexdigest() != protocol['cases_sha256']:
        raise ValueError('cases changed')
    cases = load(work/'cases.json')
    for c in cases:
        if hashlib.sha256((work/c['path']).read_bytes()).hexdigest() != c['input_sha256']:
            raise ValueError('input changed: ' + c['id'])
    return protocol, cases


def trial(work, case, repeat, mask, namespace):
    directory = work/'executions'/namespace/case['id']/f'r{repeat}-m{mask}'
    execution = utility_ops.execute(mask,work/case['path'],directory)
    checked = utility_oracle.evaluate((work/case['path']).read_bytes(),case['intent'],directory)
    row = {'task_id':case['id'],'repeat':repeat,'mask':mask,'directory':directory.relative_to(work).as_posix(),
           'execution':execution,'oracle':checked,'quality':int(checked['deliverable']),
           'execution_failure':int(execution['status']!='completed')}
    return row


def matrix(work, cases, namespace, repeats=1):
    records = []
    for index, case in enumerate(cases):
        for repeat in range(repeats):
            order = sorted(range(8),key=lambda m:hashlib.sha256(f'{case["id"]}:{repeat}:{m}'.encode()).digest())
            records.extend(trial(work,case,repeat,m,namespace) for m in order)
        if (index+1) % 16 == 0 or index == len(cases)-1:
            print(f'{namespace}: {index+1}/{len(cases)} tasks, {len(records)} actual subprocesses',flush=True)
    save(work/(namespace+'-executions.json'),records)
    return records


def targets(cases, records):
    by_id = {c['id']:{} for c in cases}
    for r in records: by_id[r['task_id']][r['mask']] = r
    return np.asarray([[by_id[c['id']][m]['quality'] for m in range(8)]+
                       [by_id[c['id']][m]['execution_failure'] for m in range(8)] for c in cases],float)


def train(work):
    protocol,cases = verify(work)
    if (work/'model.json').exists() or (work/'test-executions.json').exists():
        raise ValueError('training stage already completed or test unsealed')
    train_cases = [c for c in cases if c['split']=='train']
    records = matrix(work,train_cases,'train')
    x = np.array([cu.features((work/c['path']).read_bytes(),c['intent'])['vector'] for c in train_cases],float)
    model = cu.fit_tree(x,targets(train_cases,records),depth=8,min_leaf=2)
    model.update(protocol_sha256=protocol['protocol_sha256'], operator_code_sha256=utility_ops.CODE_SHA,
                 training_record_sha256=hashlib.sha256((work/'train-executions.json').read_bytes()).hexdigest())
    cu.validate_model(model); save(work/'model.json',model)
    cal = [c for c in cases if c['split']=='calibration']
    predicted = {c['id']:cu.predict(model,cu.features((work/c['path']).read_bytes(),c['intent']),minimum_quality=.5) for c in cal}
    save(work/'calibration-predictions.json',{'created_at_ns':time.time_ns(),'predictions':predicted})
    cal_records = matrix(work,cal,'calibration')
    y = targets(cal,cal_records)
    comparisons = []
    for threshold in protocol['calibration_threshold_grid']:
        chosen = [cu.predict(model,cu.features((work/c['path']).read_bytes(),c['intent']),minimum_quality=threshold) for c in cal]
        reference_valid = [utility_oracle.evaluate((work/c['path']).read_bytes(),c['intent'],None)['reference_valid'] for c in cal]
        qualities = [int(y[i,p['mask']]) if p['mask'] is not None else 0 for i,p in enumerate(chosen)]
        valid = [i for i,v in enumerate(reference_valid) if v]
        regressions = [cal[i]['id'] for i in valid if qualities[i]<y[i,7]]
        comparisons.append({'threshold':threshold,'regressions':regressions,
            'valid_deliveries':sum(qualities[i] for i in valid),'reference_valid_tasks':len(valid),
            'invalid_abstentions':sum(p['abstain'] and not reference_valid[i] for i,p in enumerate(chosen)),
            'eligible':not regressions})
    passing = [c for c in comparisons if c['eligible']]
    selected = max(passing,key=lambda c:(c['valid_deliveries'],c['threshold']))['threshold'] if passing else None
    save(work/'selection.json',{'frozen_at_ns':time.time_ns(),'protocol_sha256':protocol['protocol_sha256'],
        'model_sha256':cu.digest(model),'minimum_quality':selected,'fallback_to_baseline':selected is None,
        'comparisons':comparisons,'formal_routing_deployed':False,
        'warning':'calibration is empirical selection, not a statistical safety certificate'})
    print(json.dumps({'model_sha256':cu.digest(model),'minimum_quality':selected,'calibration':comparisons}),flush=True)


def summary(work,cases,records,predictions):
    by_id = {c['id']:{} for c in cases}
    for row in records: by_id[row['task_id']][(row['repeat'],row['mask'])]=row
    rows, utility_errors, briers = [], [], []
    for case in cases:
        arms, pred = by_id[case['id']], predictions[case['id']]
        ref_valid = utility_oracle.evaluate((work/case['path']).read_bytes(),case['intent'],None)['reference_valid']
        for repeat in range(REPEATS):
            baseline = arms[(repeat,7)]['quality']
            after = arms[(repeat,pred['mask'])]['quality'] if pred['mask'] is not None else 0
            rows.append({'task_id':case['id'],'repeat':repeat,'reference_valid':ref_valid,
                         'baseline':baseline,'after':after,'abstain':pred['abstain'],
                         'kind':case['kind'],'delta':after-baseline})
        # Repeats are not additional training or metric observations.
        observed = [arms[(0,m)]['quality'] for m in range(8)]
        actual_marginal = [sum(observed[m | (1<<j)]-observed[m] for m in range(8) if not m&(1<<j))/4 for j in range(3)]
        if pred['reason'] != 'outside_training_support':
            utility_errors.extend(abs(a-b['predicted_marginal_gain']) for a,b in zip(actual_marginal,pred['marginal']))
            briers.extend((pred['mask_execution_failure'][m]-arms[(0,m)]['execution_failure'])**2 for m in range(8))
    valid = [r for r in rows if r['reference_valid']]
    gain = sum(r['delta'] for r in valid)/len(valid) if valid else 0
    wins = sum(sum(r['delta'] for r in valid if r['task_id']==c['id'])>0 for c in cases)
    losses = sum(sum(r['delta'] for r in valid if r['task_id']==c['id'])<0 for c in cases)
    n = wins+losses
    sign_p = sum(math.comb(n,i) for i in range(wins,n+1))/2**n if n else 1
    return {'tasks':len(cases),'reference_valid_tasks':len(valid)//REPEATS,'repeats':REPEATS,
        'actual_subprocesses':len(records),'baseline_delivery_rate':sum(r['baseline'] for r in valid)/len(valid) if valid else 0,
        'conditional_delivery_rate':sum(r['after'] for r in valid)/len(valid) if valid else 0,
        'mean_gain':gain,'wins':wins,'losses':losses,'ties':len(valid)//REPEATS-wins-losses,
        'regression_pairs':[{'task_id':r['task_id'],'repeat':r['repeat']} for r in valid if r['delta']<0],
        'invalid_tasks':len(cases)-len(valid)//REPEATS,
        'invalid_abstentions':sum(r['abstain'] for r in rows if not r['reference_valid'])//REPEATS,
        'supported_utility_mae':float(np.mean(utility_errors)) if utility_errors else None,
        'supported_failure_brier':float(np.mean(briers)) if briers else None,
        'supported_tasks':sum(p['reason']!='outside_training_support' for p in predictions.values()),
        'descriptive_task_sign_p':sign_p,'independent_public_source_clusters':1,
        'inference_warning':'shared source and authored conditions invalidate treating task sign-p as generalization proof',
        'pairs':rows}


def test(work):
    protocol,cases = verify(work)
    model, selection = load(work/'model.json'),load(work/'selection.json')
    if cu.digest(model) != selection['model_sha256']:
        raise ValueError('model changed after calibration')
    selected = [c for c in cases if c['split']=='sealed_test']
    threshold = selection['minimum_quality'] if selection['minimum_quality'] is not None else .75
    predictions = {c['id']:cu.predict(model,cu.features((work/c['path']).read_bytes(),c['intent']),minimum_quality=threshold) for c in selected}
    if selection['fallback_to_baseline']:
        for p in predictions.values(): p.update(mask=7,abstain=False,reason='calibration_kept_baseline')
    save(work/'test-predictions-frozen.json',{'created_at_ns':time.time_ns(),'selection_sha256':cu.digest(selection),
                                            'model_sha256':cu.digest(model),'predictions':predictions})
    records = matrix(work,selected,'test',REPEATS)
    result = summary(work,selected,records,predictions)
    report = {'version':VERSION,'protocol_sha256':protocol['protocol_sha256'],'model_sha256':cu.digest(model),
        'summary':result,'training_tasks':len(protocol['splits']['train']),'calibration':selection,
        'scope':'three reviewed tabular interventions; public penguin measurements with declared perturbations plus synthetic boundaries',
        'formal_routing_deployed':False,'reward_applied':False,'points':0,'limitations':protocol['limitations']}
    report['report_sha256']=cu.digest(report)
    save(work/'report.json',report)
    print(json.dumps({k:v for k,v in result.items() if k!='pairs'},ensure_ascii=False),flush=True)


def audit(work):
    protocol,cases=verify(work)
    records=[]
    for stage in ('train','calibration','test'):
        records.extend(load(work/(stage+'-executions.json')))
    by_id={c['id']:c for c in cases}
    predictions=load(work/'test-predictions-frozen.json')
    errors=[]
    for r in records:
        case=by_id[r['task_id']]; folder=work/r['directory']
        recalculated=utility_oracle.evaluate((work/case['path']).read_bytes(),case['intent'],folder)
        if recalculated!=r['oracle']:errors.append([r['task_id'],r['mask'],'oracle'])
        for name,meta in r['execution']['artifacts'].items():
            raw=(folder/name).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=meta['sha256'] or len(raw)!=meta['bytes']:
                errors.append([r['task_id'],r['mask'],'artifact'])
        if r['execution']['code_sha256']!=protocol['operator_code_sha256']:errors.append([r['task_id'],'code'])
        if case['split']=='sealed_test' and r['execution']['started_at_ns']<=predictions['created_at_ns']:
            errors.append([r['task_id'],'prediction_after_execution'])
    report=load(work/'report.json')
    if report['report_sha256']!=cu.digest({k:v for k,v in report.items() if k!='report_sha256'}):errors.append(['report_digest'])
    result={'version':'conditional-utility-artifact-audit-v1','ok':not errors,'errors':errors,
        'checked_subprocesses':len(records),'protocol_sha256':protocol['protocol_sha256'],
        'independent_recomputation':'same standalone reference re-read all actual artifacts; not external blinded review'}
    save(work/'artifact-audit.json',result);print(json.dumps(result),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['prepare','train','test','audit'])
    p.add_argument('--work',type=Path,required=True)
    args=p.parse_args();globals()[args.stage](args.work.absolute())


if __name__=='__main__':main()
