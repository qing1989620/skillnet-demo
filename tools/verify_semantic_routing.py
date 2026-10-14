"""Independently reconstruct outcome counts from bytes, not model self-scores.

Can verify a cold clone without API credentials or encoder inference. Does not
execute archived Python or trust the summary report when computing results.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet import semantic_routing as sr,utility_oracle,utility_ops,reward_gates


def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def audit(work):
    p=load(work/'protocol.json');cases=load(work/'cases.json');model=load(work/'model.json')
    selection=load(work/'selection.json');frozen=load(work/'prompts.json')
    assert p['protocol_sha256']==sr.digest({k:v for k,v in p.items() if k!='protocol_sha256'})
    assert sha((work/'cases.json').read_bytes())==p['cases_sha256']
    for path,h in p['code_sha256'].items():assert sha((ROOT/path).read_bytes())==h, path
    assert sha((work/'wine.data').read_bytes())==p['source']['data_sha256']
    assert sha((work/'wine.zip').read_bytes())==p['source']['zip_sha256']
    assert sr.digest(model)==selection['model_sha256']==frozen['model_sha256']
    assert model['protocol_sha256']==frozen['protocol_sha256']==p['protocol_sha256']
    assert p['created_at_ns']<model['trained_at_ns']<=selection['created_at_ns']<frozen['created_at_ns']
    assert model['training_ids']==[c['id'] for c in cases if c['split']=='train']
    assert len(set(model['training_ids']) & {c['id'] for c in cases if c['split']!='train'})==0
    assert len({sha(c['request'].encode()) for c in cases})==len(cases)
    assert len({c['input_sha256'] for c in cases})==len(cases)
    for c in cases:assert sha((work/c['path']).read_bytes())==c['input_sha256']
    tests={c['id']:c for c in cases if c['split']=='sealed_test'}
    jobs={(j['task_id'],j['arm'],j['repeat']):j for j in frozen['jobs']}
    assert len(jobs)==len(frozen['jobs'])==144
    # Confirm held-out labels are never inserted into any API user payload.
    for key,j in jobs.items():
        assert sr.digest(j['messages'])==j['prompt_sha256']
        payload=json.loads(j['messages'][1]['content']);c=tests[key[0]]
        assert set(payload)==({'request','input_csv'} | ({'development_examples'} if key[1]=='retrieved_examples' else {'advisory_trained_intent'} if key[1]=='trained_hint' else set()))
        assert payload['request']==c['request'] and payload['input_csv']==(work/c['path']).read_text(encoding='utf-8')
    records=[load(x) for x in sorted((work/'records').glob('*.json'))];assert len(records)==192
    keys={(r['task_id'],r['arm'],r['repeat']) for r in records};assert len(keys)==192
    for c in tests.values():
        assert {(c['id'],a,rep) for a in p['llm']['arms'] for rep in range(2)}<=keys
        assert {(c['id'],a,0) for a in ['offline_trained','nearest_one']}<=keys
    physical=0;files=0
    for r in records:
        c=tests[r['task_id']]
        if r['arm'] in p['llm']['arms']:
            j=jobs[(r['task_id'],r['arm'],r['repeat'])]
            assert r['prompt_sha256']==j['prompt_sha256'] and r['started_at_ns']>frozen['created_at_ns']
            if r['status']=='completed':assert sr.parse_action(r['response'])==r['action']
        ex=r.get('execution')
        if ex:
            folder=work/r['directory'];assert folder.resolve().is_relative_to((work/'executions').resolve())
            assert sha((folder/'main.py').read_bytes())==utility_ops.CODE_SHA==ex['code_sha256']
            assert ex['input_sha256']==c['input_sha256']==sha((folder/'input.csv').read_bytes())
            assert ex['mask']==r['action']['mask']
            assert ex['started_at_ns']>frozen['created_at_ns']
            for name,meta in ex['artifacts'].items():
                assert name in ('output.csv','summary.csv')
                raw=(folder/name).read_bytes();assert sha(raw)==meta['sha256'] and len(raw)==meta['bytes'];files+=1
            o=utility_oracle.evaluate((work/c['path']).read_bytes(),c['intent'],folder)
            assert o==r['oracle']
            q=int(not c['expect_reject'] and o['deliverable']);assert q==r['quality']
            assert r['correct']==bool(q);physical+=1
        else:
            assert r['quality']==0
            assert r['correct']==bool(r.get('action',{}).get('reject') and c['expect_reject'])
    metrics={}
    for arm in ['plain','retrieved_examples','trained_hint','offline_trained','nearest_one']:
        rows=[r for r in records if r['arm']==arm];valid=[r for r in rows if not tests[r['task_id']]['expect_reject']]
        bad=[r for r in rows if tests[r['task_id']]['expect_reject']]
        metrics[arm]={'valid_trials':len(valid),'valid_deliveries':sum(r['quality'] for r in valid),
            'delivery_rate':sum(r['quality'] for r in valid)/len(valid),'boundary_trials':len(bad),
            'boundary_refusals':sum(r['correct'] for r in bad),'unsafe_boundary_actions':sum(bool(r.get('action')) and not r['action']['reject'] for r in bad),
            'failed_calls':sum(r.get('status')=='failed' for r in rows),
            'prompt_tokens':sum(r.get('prompt_tokens',0) for r in rows),'completion_tokens':sum(r.get('completion_tokens',0) for r in rows)}
    pairs=[]
    for c in tests.values():
        if c['expect_reject']:continue
        for rep in range(2):
            rows={r['arm']:r for r in records if r['task_id']==c['id'] and r['repeat']==rep and r['arm'] in p['llm']['arms']}
            pairs.append({'task_id':c['id'],'repeat':rep,**{k:v['quality'] for k,v in rows.items()}})
    contrast={}
    for control in ['plain','retrieved_examples']:
        a,b=metrics['trained_hint'],metrics[control]
        contrast[control]={'mean_delivery_gain':a['delivery_rate']-b['delivery_rate'],
            'win_pairs':sum(r['trained_hint']>r[control] for r in pairs),
            'loss_pairs':sum(r['trained_hint']<r[control] for r in pairs),
            'tie_pairs':sum(r['trained_hint']==r[control] for r in pairs),
            'input_token_overhead':a['prompt_tokens']/b['prompt_tokens']-1 if b['prompt_tokens'] else None}
    report={'version':sr.VERSION,'protocol_sha256':p['protocol_sha256'],'model_sha256':sr.digest(model),
        'tasks':len(tests),'valid_tasks':16,'boundary_tasks':8,'api_requests':144,'records':len(records),
        'physical_executions':physical,'verified_output_files':files,'metrics':metrics,'paired_comparisons':contrast,
        'response_models':sorted({str(r.get('response_model')) for r in records if 'response_model' in r}),
        'artifact_audit':{'ok':True,'predictions_before_execution':True,'training_test_disjoint':True},
        'scope':p['scope'],'reward_applied':False,'formal_routing_deployed':False,'points':0,
        'limitations':['Manually authored semantic labels, not learned causal skill effects.',
            'One task family and one new measurement source; repeats and shared source rows are not independent samples.',
            'Provider model aliases are not immutable revisions; no cross-model or SOTA claim.',
            'Replays use recorded API decisions and new physical executions, not new API completions.']}
    a=reward_gates.Audit({'kind':'semantic-routing-research','protocol_sha256':p['protocol_sha256'],
                        'model_sha256':sr.digest(model),'scope':p['scope']})
    a.set('frozen','passed','任务、参数选择、调用预算、增益与开销门槛在新测试前冻结。')
    a.set('independent','passed','重读实际 CSV，独立逐行与 Decimal 验算；不用模型评分。')
    a.set('integrity','passed','全部原始调用、预测时序与物理产物 SHA 已复核。',physical_executions=physical)
    candidate=metrics['trained_hint']
    a.set('complete','passed' if not candidate['failed_calls'] else 'failed','严格保留非法 JSON 和失败调用，不用成功重试替换。',failed_calls=candidate['failed_calls'])
    a.set('version','unknown','数值头与程序版本精确绑定；提供方模型别名不是不可变修订版本。')
    fair=contrast['plain']['input_token_overhead']<=p['admission']['maximum_input_token_overhead']
    a.set('fair','passed' if fair else 'failed','同一动作、模型别名与输出预算；另要求训练提示相对独立模型的输入开销不超过预定 15%。',input_token_overhead=contrast['plain']['input_token_overhead'])
    a.set('heldout','passed','本轮训练、校准与测试请求及输入指纹不重叠；只证明本研究留出。')
    a.set('suite','passed','24 题、3 臂、2 次调用全部保留，包括拒绝与格式错误。')
    losses=sum(v['loss_pairs'] for v in contrast.values())
    a.set('regression','passed' if losses==0 else 'failed','逐个有效任务配对比较，任何退步阻止晋级。',loss_pairs=losses)
    gain=min(v['mean_delivery_gain'] for v in contrast.values())
    a.set('gain','passed' if gain>=p['admission']['minimum_delivery_gain_over_each_control'] else 'failed','必须同时超过独立模型和检索示例两种对照。',minimum_control_gain=gain)
    a.set('reliable','unknown','单一任务族与测量来源，重复和共享源记录不能算独立跨领域样本。')
    a.set('novel','unknown','没有正式候选版本提升证书，不发放一次性奖励。')
    report['admission']=a.result()
    report['report_sha256']=sr.digest(report)
    return report


def package(work,dest):
    r=audit(work)
    if (work/'report.json').exists():assert load(work/'report.json')==r
    else:write(work/'report.json',r)
    if dest.exists():raise ValueError('fresh publication directory required')
    dest.mkdir(parents=True)
    names=['protocol.json','cases.json','model.json','selection.json','prompts.json','report.json','wine.data','wine.zip']
    for name in names:shutil.copyfile(work/name,dest/name)
    shutil.copytree(work/'inputs',dest/'inputs');shutil.copytree(work/'records',dest/'records')
    # Full physical evidence archived; verification never runs these scripts.
    with zipfile.ZipFile(dest/'execution-evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted((work/'executions').rglob('*')):
            if path.is_file():z.write(path,path.relative_to(work).as_posix())
    (dest/'ATTRIBUTION.md').write_text('UCI Wine — Aeberhard, S. & Forina, M. (1991). DOI: 10.24432/C5PC7J. CC BY 4.0.\nhttps://archive.ics.uci.edu/dataset/109/wine\nOnly alcohol measurements retained. IDs, groups, splits and defects are declared controlled transforms.\n',encoding='utf-8',newline='\n')
    publication={'files':{x.relative_to(dest).as_posix():{'sha256':sha(x.read_bytes()),'bytes':x.stat().st_size}
                          for x in sorted(dest.rglob('*')) if x.is_file()},'report_sha256':r['report_sha256']}
    publication['digest']=sr.digest(publication);write(dest/'publication.json',publication)


def public_audit(base):
    pub=load(base/'publication.json');assert pub['digest']==sr.digest({k:v for k,v in pub.items() if k!='digest'})
    for name,meta in pub['files'].items():
        path=(base/name).resolve();assert path.is_relative_to(base.resolve()) and path.is_file()
        assert sha(path.read_bytes())==meta['sha256'] and path.stat().st_size==meta['bytes']
    with tempfile.TemporaryDirectory(prefix='semantic-evidence-') as tmp:
        work=Path(tmp)
        for path in base.rglob('*'):
            if path.is_file() and path.name!='execution-evidence.zip':
                target=work/path.relative_to(base);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        with zipfile.ZipFile(base/'execution-evidence.zip') as z:
            assert len(z.infolist())<3000 and sum(i.file_size for i in z.infolist())<32*1048576
            for i in z.infolist():
                assert not i.is_dir() and i.file_size<1048576
                target=(work/i.filename).resolve();assert target.is_relative_to((work/'executions').resolve())
                assert '\\' not in i.filename and ':' not in i.filename
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(i))
        r=audit(work);assert r==load(base/'report.json')
    return {'ok':True,'tasks':r['tasks'],'api_requests':r['api_requests'],'physical_executions':r['physical_executions'],
            'verified_output_files':r['verified_output_files'],'report_sha256':r['report_sha256']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path);p.add_argument('--publish',type=Path);p.add_argument('--public',type=Path);a=p.parse_args()
    if a.public:print(json.dumps(public_audit(a.public.absolute()),ensure_ascii=False));return
    if a.publish:package(a.work.absolute(),a.publish.absolute())
    r=audit(a.work.absolute());print(json.dumps(r,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
