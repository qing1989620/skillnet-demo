"""Real HTTP runs with twelve-gate evidence. Does not overwrite historic proof."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import httpx
from skillnet import config, runtime, reward_gates
from skillnet.integration import ClientConfig, SkillNetClient
from skillnet.s1_identity import S1Context
from skillnet.scenarios import scenarios, evaluate_artifacts
from outcome_evidence_smoke import wait


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--business-run')
    parser.add_argument('--unmeasured-run')
    parser.add_argument('--failed-run')
    parser.add_argument('--base-url',default='http://127.0.0.1:8848')
    args=parser.parse_args()
    token=os.environ.get('SKILLNET_TOKEN','')
    key=os.environ.get('SKILLNET_S1_SIGNING_KEY','')
    identity=S1Context(**{k:os.environ['SKILLNET_S1_'+k.upper()] for k in ('tenant','user','project')}) if key else None
    def get(path):
        response=httpx.get(args.base_url+path,headers={'X-SkillNet-Token':token},timeout=30)
        response.raise_for_status()
        return response.json()
    before=get('/api/learning/policy')
    rules=get('/api/learning/reward-policy')
    assert rules['sha256']==reward_gates.policy_sha256()
    case=scenarios()[0]
    with SkillNetClient(ClientConfig(base_url=args.base_url,token=token),identity=identity,signing_key=key) as client:
        rid=args.business_run or client.create_run(case['task'],k=5,max_steps=3,max_cost_yuan=1.2,
            max_seconds=600,max_llm_calls=45)['run_id']
        business=wait(client,rid)
        assert business['status']=='COMPLETED',business.get('error')
        task='只执行一步，不联网：生成 opinion.md，写一段你对未来企业 AI 助手设计的主观建议，明确它是建议而非已验证事实。没有标准答案，不要编造数据。'
        uid=args.unmeasured_run or client.create_run(task,k=3,max_steps=1,max_cost_yuan=.6,
            max_seconds=400,max_llm_calls=25)['run_id']
        unmeasured=wait(client,uid)
        assert unmeasured['status']=='COMPLETED',unmeasured.get('error')
        for run in (business,unmeasured):
            gates=run['staged']['reward_gates']
            assert gates['policy_sha256']==rules['sha256'] and len(gates['gates'])==12
            assert gates['operator']=='AND' and not gates['eligible'] and gates['points']==0
            assert not gates['reward_applied'] and not gates['ranking_weights_deployed']
            assert run['staged']['evaluation_contract']['reward_policy_sha256']==rules['sha256']
            assert not run['staged']['learning_gate']['reward_eligible']
            assert all(row['delta']==0 and not row['nudged'] for row in run['feedback'])
            prepared=next(e for e in run['events'] if e['type']=='evaluation.prepared')
            dag=next(e for e in run['events'] if e['type']=='dag.ready')
            assert prepared['seq']<dag['seq']
            final=next(e for e in reversed(run['events']) if e['type']=='evaluation.gates_updated')
            assert final['data']['reward_gates']==gates
        assert business['staged']['quality_assessment']['scope_verdict']=='passed'
        assert business['staged']['reward_gates']['passed']==4
        assert unmeasured['staged']['quality_assessment']['scope_verdict']=='unknown'
        independent=next(g for g in unmeasured['staged']['reward_gates']['gates'] if g['id']=='independent')
        assert independent['status']=='unknown'
        with tempfile.TemporaryDirectory() as directory:
            workspace=Path(directory)
            (workspace/'artifacts').mkdir()
            for artifact in business['artifacts']:
                raw=client.download_artifact(rid,artifact['name'],expected_sha256=artifact['sha256'])
                (workspace/'artifacts'/artifact['name']).write_bytes(raw)
            measured=evaluate_artifacts(case,runtime.RunStore._from_dict(business),workspace)
            assert measured['score']==1,measured
        after=get('/api/learning/policy')
        assert before['state_sha256']==after['state_sha256'] and before['updates']==after['updates']
        failed=wait(client,args.failed_run) if args.failed_run else None
        if failed:
            assert failed['status'] in ('PARTIAL','FAILED')
            assert not failed['staged']['reward_gates']['eligible']
            assert next(g for g in failed['staged']['reward_gates']['gates'] if g['id']=='complete')['status']=='failed'
        report=dict(protocol=reward_gates.VERSION,policy_sha256=rules['sha256'],
            business_run_id=rid,unmeasured_run_id=uid,business_gates=business['staged']['reward_gates'],
            failed_run_id=failed['run_id'] if failed else None,
            failed_gates=failed['staged']['reward_gates'] if failed else None,
            failed_judge_score=failed.get('judge',{}).get('weighted') if failed else None,
            unmeasured_gates=unmeasured['staged']['reward_gates'],oracle=measured,
            judge_scores=[business.get('judge',{}).get('weighted'),unmeasured.get('judge',{}).get('weighted')],
            model_scores_are_advisory=True,reward_points=0,serving_policy_unchanged=True,
            policy_before_sha256=before['state_sha256'],policy_after_sha256=after['state_sha256'],
            cost_yuan=business['cost_yuan']+unmeasured['cost_yuan']+(failed['cost_yuan'] if failed else 0),
            boundary='Real single-run evidence only; no paired improvement established; positive award path covered by deterministic tests, not represented as a real improvement')
        path=config.OUT_DIR/'reward-gates-smoke.json'
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(dict(business=rid,unmeasured=uid,passed=[business['staged']['reward_gates']['passed'],
            unmeasured['staged']['reward_gates']['passed']],points=0,cost_yuan=report['cost_yuan'],report=str(path)),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
