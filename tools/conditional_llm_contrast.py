"""Paired real API execution: same model/actions/budget, with/without evidence.

The model selects reviewed programs, never writes or executes arbitrary code.
Every arm, including malformed responses and transport failures, is retained.
Frozen test outcomes are not provided in either prompt.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import httpx
from skillnet import conditional_utility as cu, config, llm, utility_oracle
from tools.conditional_utility_lab import verify,save,load,trial

SYSTEM = '''你是表格任务的技能选择器。只能选择登记程序，不可编造结果。
共同执行器：按 mask 顺序做清洗，最后按 group 汇总 split=test 的 n_rows、n_numeric、sum、mean。
bit1 / deduplicate: 同 sample_id 只保留首次，其他单元格不改。
bit2 / exclude_cross_split: 在前一步结果中删除出现在多个 split 中的 subject 的全部记录。
bit4 / drop_missing: 删除 value 为空白的行。
mask 为这些 bit 之和，0 表示直接汇总。用户 intent=false 的操作必须不做。
汇总会忽略空 value，但 n_rows 仍包括空行。每个保留的 test group 必须有有限数值，且不能有非数值。
没有 test 行、不能满足任务要求、未知 goal 或结构不支持时拒绝。只支持 goal=group_mean。
只输出 JSON，恰好两个字段：{"mask":0到7的整数,"reject":false}；或 {"mask":null,"reject":true}。
所有统计须来自执行产物。本轮不需解释。'''


def parse_action(text):
    value=json.loads(text)
    if type(value) is not dict or set(value)!={'mask','reject'} or type(value['reject']) is not bool:
        raise ValueError('invalid action schema')
    if value['reject']:
        if value['mask'] is not None:raise ValueError('reject needs null mask')
    elif type(value['mask']) is not int or not 0<=value['mask']<=7:
        raise ValueError('invalid registered mask')
    return value


def messages(case,raw,prediction,arm):
    payload={'task':case['task'],'intent':case['intent'],'input_csv':raw.decode('utf-8-sig'),
             'observed':prediction['observed']}
    if arm=='evidence':
        payload['execution_training_evidence']={k:prediction[k] for k in (
            'model_sha256','mask','abstain','reason','mask_quality','mask_execution_failure',
            'marginal','conditions','training_leaf_tasks','uncertainty')}
        payload['evidence_warning']='这些是训练样本的条件预测，不是本题执行结果；不得覆盖用户要求或忽略文件内容。'
    return [{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--workers',type=int,default=3,choices=range(1,5));a=p.parse_args();work=a.work.absolute()
    protocol,cases=verify(work)
    if not config.API_KEY:raise ValueError('configured API key is missing; no request sent')
    settings=protocol['llm']
    if config.MODEL!=settings['model_alias']:raise ValueError('model alias differs from frozen protocol')
    predictions=load(work/'test-predictions-frozen.json')
    selection=load(work/'selection.json');model=load(work/'model.json')
    if predictions['model_sha256']!=cu.digest(model) or selection['model_sha256']!=cu.digest(model):
        raise ValueError('model binding mismatch')
    selected=[c for c in cases if c['id'] in settings['task_ids']]
    jobs=[]
    for c in selected:
        raw=(work/c['path']).read_bytes();pred=predictions['predictions'][c['id']]
        for repeat in range(2):
            for arm in (['plain','evidence'] if repeat==0 else ['evidence','plain']):
                msg=messages(c,raw,pred,arm)
                jobs.append({'task_id':c['id'],'repeat':repeat,'arm':arm,'messages':msg,
                             'prompt_sha256':cu.digest(msg),'input_sha256':c['input_sha256']})
    if len(jobs)>settings['max_requests']:raise ValueError('request count exceeds protocol')
    save(work/'llm-prompts-frozen.json',{'created_at_ns':time.time_ns(),
        'protocol_sha256':protocol['protocol_sha256'],'selection_sha256':cu.digest(selection),'jobs':jobs})
    ledger=llm.UsageLedger();lock=threading.Lock();counter=0
    by_id={c['id']:c for c in selected}
    results=[]
    def group(task_id):
        nonlocal counter
        output=[]
        with httpx.Client(base_url=config.BASE_URL,timeout=httpx.Timeout(90,connect=15),
                          headers={'Authorization':'Bearer '+config.API_KEY}) as client:
            for job in [j for j in jobs if j['task_id']==task_id]:
                record={k:v for k,v in job.items() if k!='messages'}
                record.update(started_at_ns=time.time_ns(),status='failed',quality=0,action=None)
                case=by_id[task_id];raw=(work/case['path']).read_bytes()
                record['reference_valid']=utility_oracle.evaluate(raw,case['intent'],None)['reference_valid']
                try:
                    with lock:
                        if counter>=settings['max_requests'] or ledger.cost_yuan>=settings['max_total_estimated_yuan']:
                            raise ValueError('frozen request/cost budget exhausted')
                        counter+=1
                    response=client.post('/chat/completions',json={
                        'model':settings['model_alias'],'messages':job['messages'],
                        'temperature':settings['temperature'],'max_tokens':settings['max_tokens'],'stream':False})
                    record['http_status']=response.status_code
                    if response.status_code!=200:raise ValueError('upstream HTTP '+str(response.status_code))
                    data=response.json();usage=data.get('usage',{})
                    pt,ct=int(usage.get('prompt_tokens',0)),int(usage.get('completion_tokens',0))
                    ledger.record('conditional-'+job['arm'],pt,ct)
                    record.update(response_model=data.get('model'),system_fingerprint=data.get('system_fingerprint'),
                                  prompt_tokens=pt,completion_tokens=ct)
                    text=data['choices'][0]['message']['content'];record['response']=text[:10000]
                    record['finish_reason']=data['choices'][0].get('finish_reason')
                    action=parse_action(text);record.update(action=action,status='completed')
                    if not action['reject']:
                        row=trial(work,case,job['repeat'],action['mask'],'llm-'+job['arm'])
                        record.update(execution=row['execution'],oracle=row['oracle'],directory=row['directory'],quality=row['quality'])
                    record['correct_boundary_rejection']=bool(action['reject'] and not record['reference_valid'])
                except Exception as exc:
                    # Do not print upstream bodies, authorization, environment or URLs.
                    record['error_kind']=type(exc).__name__
                record['finished_at_ns']=time.time_ns()
                path=work/'llm-records'/f'{task_id}-r{job["repeat"]}-{job["arm"]}.json'
                save(path,record);output.append(record)
                with lock: print(f'LLM {len(list((work/"llm-records").glob("*.json")))}/{len(jobs)}: {task_id} r{job["repeat"]} {job["arm"]} {record["status"]}',flush=True)
        return output
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for output in pool.map(group,[c['id'] for c in selected]):results.extend(output)
    pairs=[]
    for c in selected:
        for repeat in range(2):
            row={r['arm']:r for r in results if r['task_id']==c['id'] and r['repeat']==repeat}
            pairs.append({'task_id':c['id'],'repeat':repeat,'reference_valid':row['plain']['reference_valid'],
                          'before':row['plain']['quality'],'after':row['evidence']['quality'],
                          'plain_rejected':row['plain'].get('correct_boundary_rejection',False),
                          'evidence_rejected':row['evidence'].get('correct_boundary_rejection',False)})
    valid=[r for r in pairs if r['reference_valid']]
    report={'version':'conditional-llm-execution-v1','protocol_sha256':protocol['protocol_sha256'],
        'model_sha256':cu.digest(model),'requested_calls':counter,'records':results,'pairs':pairs,
        'summary':{'tasks':len(selected),'valid_tasks':len(valid)//2,'pairs':len(pairs),
           'plain_delivery_rate':sum(r['before'] for r in valid)/len(valid) if valid else 0,
           'evidence_delivery_rate':sum(r['after'] for r in valid)/len(valid) if valid else 0,
           'regression_pairs':[r for r in valid if r['after']<r['before']],
           'failed_or_malformed_calls':sum(r['status']!='completed' for r in results),
           'response_models':sorted({str(r.get('response_model')) for r in results}),
           'invalid_plain_rejections':sum(r['plain_rejected'] for r in pairs if not r['reference_valid']),
           'invalid_evidence_rejections':sum(r['evidence_rejected'] for r in pairs if not r['reference_valid'])},
        'usage':ledger.snapshot(),'cost_warning':'cost uses configured input/output prices; token counts are actual, invoice may differ',
        'causal_scope':'paired skill-evidence prompt intervention on one API alias; not per-skill Shapley attribution or generic network improvement',
        'reward_applied':False,'points':0,'formal_routing_deployed':False}
    report['report_sha256']=cu.digest(report);save(work/'llm-report.json',report)
    print(json.dumps({'summary':report['summary'],'usage':report['usage']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
