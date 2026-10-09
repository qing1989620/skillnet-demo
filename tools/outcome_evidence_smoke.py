"""Actual HTTP/model execution, independent artifacts and unchanged serving policy.

Two runs cost at most 1.20 + 0.60 yuan. Existing IDs avoid repeated model calls.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import httpx
from skillnet import assessment, config, runtime
from skillnet.integration import ClientConfig, SkillNetClient
from skillnet.scenarios import scenarios, evaluate_artifacts
from skillnet.s1_identity import S1Context


def wait(client, rid):
    last=''
    for _ in range(330):
        run=client.get_run(rid)
        if last!=run['status']:
            print(rid,run['status'],flush=True)
            last=run['status']
        if run['status'] in runtime.TERMINAL:
            return run
        time.sleep(2)
    raise TimeoutError('Inspect the existing run before retrying')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--business-run')
    parser.add_argument('--unmeasured-run')
    parser.add_argument('--base-url',default='http://127.0.0.1:8848')
    args=parser.parse_args()
    token=os.environ.get('SKILLNET_TOKEN','')
    key=os.environ.get('SKILLNET_S1_SIGNING_KEY','')
    identity=S1Context(**{k:os.environ['SKILLNET_S1_'+k.upper()] for k in ('tenant','user','project')}) if key else None
    def policy():
        response=httpx.get(args.base_url+'/api/learning/policy',headers={'X-SkillNet-Token':token})
        response.raise_for_status()
        return response.json()
    before=policy()
    case=scenarios()[0]
    with SkillNetClient(ClientConfig(base_url=args.base_url,token=token),identity=identity,signing_key=key) as client:
        rid=args.business_run or client.create_run(case['task'],k=5,max_steps=3,max_cost_yuan=1.2,
            max_seconds=600,max_llm_calls=45)['run_id']
        business=wait(client,rid)
        quality=business['staged']['quality_assessment']
        assert business['status']=='COMPLETED',business.get('error')
        assert quality['scope_verdict']=='passed' and quality['overall_verdict']=='unconfirmed'
        assert quality['network']['applied'] is False
        prepared=next(e for e in business['events'] if e['type']=='evaluation.prepared')
        dag=next(e for e in business['events'] if e['type']=='dag.ready')
        assert prepared['seq']<dag['seq']
        assert all(not f['nudged'] and f['delta']==0 for f in business['feedback'])
        with tempfile.TemporaryDirectory() as directory:
            workspace=Path(directory)
            (workspace/'artifacts').mkdir()
            for artifact in business['artifacts']:
                raw=client.download_artifact(rid,artifact['name'],expected_sha256=artifact['sha256'])
                (workspace/'artifacts'/artifact['name']).write_bytes(raw)
            measured=evaluate_artifacts(case,runtime.RunStore._from_dict(business),workspace)
            assert measured['score']==1,measured
        task='只执行一步，不联网：生成 opinion.md，写一段你对未来企业 AI 助手设计的主观建议，明确它是建议而非已验证事实。没有标准答案，不要编造数据。'
        uid=args.unmeasured_run or client.create_run(task,k=3,max_steps=1,max_cost_yuan=.6,
            max_seconds=400,max_llm_calls=25)['run_id']
        unmeasured=wait(client,uid)
        unknown=unmeasured['staged']['quality_assessment']
        assert unmeasured['status']=='COMPLETED',unmeasured.get('error')
        assert unknown['scope_verdict']=='unknown' and unknown['overall_verdict']=='unconfirmed'
        assert not unknown['candidate_eligible'] and not unmeasured['evolution']['accepted']
        assert all(row['observed_score'] is None for row in unknown['observations'])
        after=policy()
        assert before['state_sha256']==after['state_sha256']
        assert before['updates']==after['updates']
        assert business['staged']['shadow_feedback']['policy_state_sha256']==before['state_sha256']
        assert unmeasured['staged']['shadow_feedback']['policy_state_sha256']==before['state_sha256']
        report=dict(protocol=assessment.VERSION,business_run_id=rid,unmeasured_run_id=uid,
            oracle=measured,policy_before=before,policy_after=after,serving_policy_unchanged=True,
            business_scoped_verdict=quality['scope_verdict'],overall_quality='unconfirmed',
            measured_steps=[dict(idx=r['idx'],skill=r['skill'],score=r['observed_score']) for r in quality['observations']],
            unmeasured_verdict=unknown['scope_verdict'],unmeasured_no_learning=True,
            contract_frozen_before_execution=True,cost_yuan=business['cost_yuan']+unmeasured['cost_yuan'],
            boundary='No causal attribution, cross-task gain or user satisfaction established; browser screenshot not part of this test')
        path=config.OUT_DIR/'outcome-evidence-smoke.json'
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
