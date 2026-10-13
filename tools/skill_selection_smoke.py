"""Bounded real API routing audit plus one research run; never changes ranking policy."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skillnet import config, research, runtime
from skillnet.integration import ClientConfig, SkillNetClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', help='Reuse a recorded run; skip paid search probes as well')
    parser.add_argument('--base-url', default='http://127.0.0.1:8848')
    args = parser.parse_args()
    target = ROOT/'out/skill-selection-smoke.json'
    probes = json.loads(target.read_text(encoding='utf-8'))['probes'] if args.run and target.exists() else []
    with SkillNetClient(ClientConfig(base_url=args.base_url, token=os.environ.get('SKILLNET_TOKEN', ''))) as client:
        before = client._json('GET', 'api/learning/policy')['state_sha256']
        if not args.run:
            for name, query in [
                ('focused-csv', '对 CSV 去重并统计缺失值，只交付清洗后的表格与缺失统计，不训练模型、不写报告。'),
                ('community-rdkit', 'Use RDKit to compute molecular weight and logP for a list of SMILES. Only deliver a CSV of descriptors; no docking, training or literature review.'),
                ('no-skill-needed', '你好，只说一句晚安就好，不做研究、不生成文件。'),
            ]:
                result = client.search(query, k=5, mode='fabric')
                probes.append(dict(name=name, query=query, result=result))
                print(json.dumps(dict(probe=name, selected=result['selected'], selection=result.get('selection'), cost_yuan=result.get('cost_yuan')), ensure_ascii=False), flush=True)
            target.write_text(json.dumps(dict(probes=probes), ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
        if not args.run:
            run_id = client.create_run(research.research_scenario()['task'], max_steps=3,
                max_cost_yuan=1.2, max_seconds=420, max_llm_calls=40)['run_id']
        else:
            run_id = args.run
        print('run_id='+run_id, flush=True)
        deadline = time.monotonic()+480
        while time.monotonic() < deadline:
            run = client.get_run(run_id)
            if run['status'] in runtime.TERMINAL:
                break
            time.sleep(2)
        else:
            raise RuntimeError('Run still active; inspect before launching another')
        capsule = client.get_evidence(run_id)
        after = client._json('GET', 'api/learning/policy')['state_sha256']
    local = runtime.RunStore(config.OUT_DIR/'runs').get(run_id)
    workspace = config.OUT_DIR/'runs'/run_id
    oracle = research.evaluate_artifacts(local, workspace)
    fabric = run['retrieval']['fabric']
    pool = [c['name'] for c in fabric['candidates'][:20]]
    report = dict(kind='real-api-task-utility-selection', run_id=run_id, probes=probes,
        model=run['model'], cost_yuan=run['cost_yuan'], status=run['status'],
        retrieval=fabric, orchestration=run['staged']['orchestration'],
        steps=[dict(idx=s['idx'], skill=s['skill'], action=s['action'], status=s['status']) for s in run['steps']],
        independent_reference=oracle, same_candidate_pool=pool==run['staged']['orchestration']['candidate_names'],
        policy_unchanged=before==after, policy_before_sha256=before, policy_after_sha256=after,
        policy_check_scope='read_only_recheck' if args.run else 'search_and_execution',
        reward_applied=run['staged']['reward_gates']['reward_applied'],
        capsule_sha256=capsule['capsule_sha256'], handoff_ready=capsule['handoff_ready'],
        limits=[f'{len(probes)} 个检索探针与一项模拟科研任务，不能推断全库最优组合或总体检索准确率',
                '模型选择理由是建议，实际参与不证明因果贡献或质量增益',
                '浏览器工具不可用；未完成真实滚动截图验收'])
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    capsule_path = ROOT/'docs/evidence/skill-selection-capsule.json'
    capsule_path.write_text(json.dumps(capsule, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    files = [target, capsule_path, config.OUT_DIR/'runs'/f'{run_id}.json',
             *[workspace/'artifacts'/a['name'] for a in run['artifacts'] if a.get('role')!='input']]
    manifest = [dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size,
                     sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
    (ROOT/'docs/evidence/skill-selection-files.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    print(json.dumps(dict(run_id=run_id, status=run['status'], score=oracle['score'],
        same_candidate_pool=report['same_candidate_pool'], policy_unchanged=report['policy_unchanged'], cost_yuan=run['cost_yuan']), ensure_ascii=False), flush=True)
    if not (run['status']=='COMPLETED' and oracle['score']==1 and report['same_candidate_pool']
            and report['policy_unchanged'] and report['reward_applied'] is False and capsule['handoff_ready']):
        raise SystemExit('Evidence retained; inspect the failed acceptance before delivery')


if __name__ == '__main__':
    main()
