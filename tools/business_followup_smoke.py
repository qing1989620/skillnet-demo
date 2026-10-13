"""Live business workflow and exact cross-turn file handoff through the service client.

Without existing IDs this calls the configured LLM: budgets 1.20 + 0.80 yuan.
Existing IDs verify downloaded bytes without creating another paid execution.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skillnet import config, runtime
from skillnet.integration import ClientConfig, SkillNetClient
from skillnet.s1_identity import S1Context
from skillnet.scenarios import scenarios, evaluate_artifacts

TERMINAL = {'COMPLETED','PARTIAL','FAILED','CANCELLED','INTERRUPTED','BUDGET_EXCEEDED'}


def wait(client, run_id):
    deadline = time.monotonic() + 650
    last = ''
    while time.monotonic() < deadline:
        run = client.get_run(run_id)
        if run['status'] != last:
            print(run_id, run['status'], flush=True)
            last = run['status']
        if run['status'] in TERMINAL:
            assert run['status'] == 'COMPLETED', run.get('error')
            assert run['staged']['acceptance']['state'] == 'passed', run['staged']['acceptance']
            return run
        time.sleep(2)
    raise TimeoutError('Run has not terminated; inspect it before creating another execution')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8848')
    parser.add_argument('--business-run')
    parser.add_argument('--followup-run')
    parser.add_argument('--report', type=Path, default=config.OUT_DIR/'business-followup-evidence.json')
    args = parser.parse_args()
    key = os.environ.get('SKILLNET_S1_SIGNING_KEY', '')
    identity = S1Context(**{k:os.environ['SKILLNET_S1_'+k.upper()] for k in ('tenant','user','project')}) if key else None
    case = scenarios()[0]
    with SkillNetClient(ClientConfig(base_url=args.base_url, token=os.environ.get('SKILLNET_TOKEN','')),
                        identity=identity, signing_key=key) as client:
        rid = args.business_run or client.create_run(case['task'], k=5, max_steps=3, max_cost_yuan=1.2,
                                                     max_seconds=600, max_llm_calls=45)['run_id']
        business = wait(client, rid)
        with tempfile.TemporaryDirectory(prefix='skillnet-business-') as directory:
            workspace = Path(directory)
            artifacts = workspace/'artifacts'
            artifacts.mkdir()
            for artifact in business['artifacts']:
                content = client.download_artifact(rid, artifact['name'], expected_sha256=artifact['sha256'])
                (artifacts/artifact['name']).write_bytes(content)
            result = evaluate_artifacts(case, runtime.RunStore._from_dict(business), workspace)
            assert result['score'] == 1.0, result
            source = next(a for a in business['artifacts'] if a['name'].endswith('monthly_summary.csv'))
            source_rows = list(csv.DictReader((artifacts/source['name']).read_text(encoding='utf-8-sig').splitlines()))
            task = '继续核对上一轮文件：直接读取 monthly_summary.csv，禁止重新生成数据。只执行一步，生成 risk.csv，列名 month,gross_margin，按毛利率从低到高排序；毛利率保留原始精度，不做四舍五入，绝对误差不超过 1e-9；打印收入合计、最低毛利率月份，明确模拟数据。'
            fid = args.followup_run or client.create_run(task, k=3, max_steps=1, max_cost_yuan=.8,
                    max_seconds=400, max_llm_calls=30,
                    history=[dict(q=case['task'],a='已完成模拟经营月报；继续使用实际月度汇总文件。',run_id=rid)],
                    artifact_refs=[dict(run_id=rid,name=source['name'],sha256=source['sha256'])])['run_id']
            followup = wait(client, fid)
            assert any(a.get('source_run_id') == rid and a['sha256'] == source['sha256']
                       and a['kind'] == '跨轮输入' for a in followup['artifacts'])
            risk = next(a for a in followup['artifacts'] if a['name'].endswith('risk.csv'))
            raw = client.download_artifact(fid, risk['name'], expected_sha256=risk['sha256'])
            reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
            actual = list(reader)
            assert reader.fieldnames == ['month','gross_margin']
            expected = sorted(source_rows, key=lambda row:float(row['gross_margin']))
            assert len(actual) == len(expected)
            assert all(a['month'] == b['month'] and abs(float(a['gross_margin'])-float(b['gross_margin'])) <= 1e-9
                       for a,b in zip(actual,expected))
            assert any('monthly_summary.csv' in step['inputs'] for step in followup['steps'])
            report = dict(business_run_id=rid,followup_run_id=fid,oracle=result,
                    business_acceptance=business['staged']['acceptance'],followup_acceptance=followup['staged']['acceptance'],
                    input_sha256=source['sha256'],actual_file_version_carried=True,
                    followup_values_and_order_verified=True,followup_artifact_sha256=risk['sha256'],
                    cost_yuan=business['cost_yuan']+followup['cost_yuan'],
                    boundary='Actual SkillNet HTTP client and artifacts; target S1 SSO/deployment not exercised')
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()
