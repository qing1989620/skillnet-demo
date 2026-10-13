"""One paid synthetic research Run, or recheck a recorded Run via the real SDK."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from skillnet import config, research, runtime
from skillnet.integration import ClientConfig, SkillNetClient


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', help='Recheck an existing run without a new LLM call')
    parser.add_argument('--base-url',default='http://127.0.0.1:8848')
    args=parser.parse_args()
    with SkillNetClient(ClientConfig(base_url=args.base_url,token=os.environ.get('SKILLNET_TOKEN',''))) as client:
        before=client._json('GET','api/learning/policy')
        run_id=args.run
        if not run_id:
            created=client.create_run(research.research_scenario()['task'],max_steps=3,
                max_cost_yuan=1.2,max_seconds=420,max_llm_calls=40)
            run_id=created['run_id']
            print('run_id='+run_id,flush=True)
        deadline=time.monotonic()+480
        while time.monotonic()<deadline:
            data=client.get_run(run_id)
            if data['status'] in runtime.TERMINAL:break
            time.sleep(2)
        else:raise RuntimeError('Run remains active; inspect it before creating another')
        capsule=client.get_evidence(run_id)
        downloads=[]
        for item in capsule['files']:
            content=client.download_artifact(run_id,item['name'],expected_sha256=item['sha256'])
            downloads.append(dict(name=item['name'],sha256=hashlib.sha256(content).hexdigest(),bytes=len(content)))
        after=client._json('GET','api/learning/policy')
    local=runtime.RunStore(config.OUT_DIR/'runs').get(run_id)
    oracle=research.evaluate_artifacts(local,config.OUT_DIR/'runs'/run_id)
    proof=dict(kind='real-model-synthetic-research-ecosystem',run_id=run_id,status=data['status'],
        scenario_id=research.research_scenario()['id'],task_sha256=research.research_scenario()['task_sha256'],
        model=data['model'],cost_yuan=data['cost_yuan'],step_stats=data['step_stats'],
        independent_reference=oracle,downloaded_files=downloads,
        capsule_sha256=capsule['capsule_sha256'],handoff_ready=capsule['handoff_ready'],
        scope_verified=capsule['scope_verified'],reward_gates=data['staged'].get('reward_gates'),
        policy_before_sha256=before['state_sha256'],policy_after_sha256=after['state_sha256'],
        policy_unchanged=before['state_sha256']==after['state_sha256'],
        production_connection_verified=False,
        limits=['公开模拟预测数据；未训练模型；不代表临床有效性','单次任务未证明技能贡献或网络增益'])
    target=ROOT/'out/research-ecosystem-smoke.json'
    target.write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    capsule_path=ROOT/'docs/evidence/research-ecosystem-capsule.json'
    capsule_path.write_text(json.dumps(capsule,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    files=[target,capsule_path,config.OUT_DIR/'runs'/f'{run_id}.json',
        *[config.OUT_DIR/'runs'/run_id/'artifacts'/a['name'] for a in downloads]]
    for path in (config.OUT_DIR/'candidates').glob('*.json'):
        record=json.loads(path.read_text(encoding='utf-8'))
        if record.get('origin_run_id')==run_id:
            public=ROOT/'docs/evidence/candidates/research-reproducibility.json'
            public.write_bytes(path.read_bytes())
            files.append(public)
            break
    manifest=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
    (ROOT/'docs/evidence/research-ecosystem-files.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps(dict(run_id=run_id,status=data['status'],score=oracle['score'],
        checks=len(oracle['checks']),cost_yuan=data['cost_yuan'],handoff_ready=capsule['handoff_ready'],
        policy_unchanged=proof['policy_unchanged']),ensure_ascii=False),flush=True)
    if not (data['status']=='COMPLETED' and oracle['score']==1 and capsule['scope_verified']
        and capsule['handoff_ready'] and proof['policy_unchanged']
        and proof['reward_gates']['reward_applied'] is False):
        raise SystemExit('Evidence retained; research acceptance failed. Inspect the recorded run.')


if __name__=='__main__':main()
