"""One bounded paid research run, rechecked against the independent reference."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from skillnet import config,research,runtime
from skillnet.integration import ClientConfig,SkillNetClient


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',help='Recheck an existing run without a paid call')
    parser.add_argument('--output-prefix', default='state-kernel', choices=['state-kernel', 'frontier-live'],
                        help='Preserve earlier evidence when validating a new research iteration')
    args=parser.parse_args()
    with SkillNetClient(ClientConfig(base_url='http://127.0.0.1:8848',token=os.environ.get('SKILLNET_TOKEN',''))) as client:
        before=client._json('GET','api/learning/policy')['state_sha256']
        run_id=args.run or client.create_run(research.research_scenario()['task'],max_steps=3,
            max_cost_yuan=1.2,max_seconds=420,max_llm_calls=40)['run_id']
        print('run_id='+run_id,flush=True)
        deadline=time.monotonic()+480
        while time.monotonic()<deadline:
            run=client.get_run(run_id)
            if run['status'] in runtime.TERMINAL:break
            time.sleep(2)
        else:raise RuntimeError('Still active; inspect this run before starting another')
        capsule=client.get_evidence(run_id)
        capabilities=client._json('GET','api/runs/'+run_id+'/capabilities')
        after=client._json('GET','api/learning/policy')['state_sha256']
    local=runtime.RunStore(config.OUT_DIR/'runs').get(run_id)
    workspace=config.OUT_DIR/'runs'/run_id
    oracle=research.evaluate_artifacts(local,workspace)
    states=[dict(idx=s['idx'],skill=s['skill'],status=s['status'],state_evidence=s.get('state_evidence'),
        n_attempts=s['n_attempts']) for s in run['steps']]
    events=run.get('events',[])
    event_types=[e['type'] for e in events]
    report=dict(kind='real-api-state-contract-execution',run_id=run_id,status=run['status'],
        model=run['model'],cost_yuan=run['cost_yuan'],llm_calls=run['llm_calls'],
        independent_reference=oracle,state_policy=run['staged'].get('state_policy'),
        declared_composition=run['staged'].get('state_composition'),steps=states,
        state_event_counts={t:event_types.count(t) for t in ('state.planned','state.admission','state.effects')},
        policy_unchanged=before==after,policy_before_sha256=before,policy_after_sha256=after,
        policy_check_scope='read_only_recheck' if args.run else 'execution',
        reward_applied=run['staged'].get('reward_gates',{}).get('reward_applied'),
        gates_passed=run['staged'].get('reward_gates',{}).get('passed'),
        capsule_sha256=capsule['capsule_sha256'],handoff_ready=capsule['handoff_ready'],
        capabilities_sha256=capabilities['report_sha256'],
        limits=['一个公开模拟科研任务不证明跨任务质量提升、因果技能模型或全局最优选择',
            '输入和效果条件由有限词表检验；算法正确性仍由独立参考复算，图表只检查存在性'])
    if run['staged'].get('capability_frontier'):
        report['capability_frontier'] = run['staged']['capability_frontier']
        report['frontier_event_count'] = event_types.count('capability.frontier')
    output=ROOT/'docs/evidence'/f'{args.output_prefix}-run.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    for name,data in [(f'{args.output_prefix}-capsule.json',capsule),(f'{args.output_prefix}-capabilities.json',capabilities)]:
        (output.parent/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    paths=[output,output.parent/f'{args.output_prefix}-capsule.json',output.parent/f'{args.output_prefix}-capabilities.json',
        config.OUT_DIR/'runs'/f'{run_id}.json',*[workspace/'artifacts'/a['name'] for a in run['artifacts']]]
    manifest=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]
    (output.parent/f'{args.output_prefix}-files.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps(dict(run_id=run_id,status=run['status'],score=oracle['score'],
        cost_yuan=run['cost_yuan'],policy_unchanged=before==after,reward_applied=report['reward_applied']),ensure_ascii=False),flush=True)
    if not (run['status']=='COMPLETED' and oracle['score']==1 and report['state_policy']
            and all(s['state_evidence'] and s['state_evidence'].get('pre',{}).get('admitted') is True
                and s['state_evidence'].get('post',{}).get('state')=='passed' for s in states)
            and before==after and report['reward_applied'] is False and capsule['handoff_ready']):
        raise SystemExit('Evidence preserved; inspect failure before delivery')


if __name__=='__main__':main()
