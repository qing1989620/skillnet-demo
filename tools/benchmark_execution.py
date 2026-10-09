"""Paired real execution benchmark. Calls the configured model; never plan-only scoring.

Same frozen task, step graph, numeric oracle and budget across context modes.
No mutation of the production library or feedback policy.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from skillnet import assessment, config, llm, pipeline, runtime
from skillnet.catalog import SkillLibrary
from skillnet.scenarios import scenarios, evaluate_artifacts
from skillnet.schema import Skill


def plan(skill_name):
    return {'steps':[
        dict(skill=skill_name,action='按给定订单规则清洗公开模拟 CSV，打印重复和缺失数量，写 clean.csv',
             depends_on=[],input_files=[],output_files=['clean.csv'],verification=['记录重复数与缺失数，明确标注模拟数据']),
        dict(skill=skill_name,action='直接读取 clean.csv 按 month 汇总收入成本、毛利毛利率及 orders；写 monthly_summary.csv；不得重新生成原始数据',
             depends_on=[0],input_files=['clean.csv'],output_files=['monthly_summary.csv'],
             verification=['按月汇总之和等于清洗明细合计；毛利率为总毛利除以总收入']),
        dict(skill=skill_name,action='读取 monthly_summary.csv 绘制 figure.svg，写 report.md 包含经营结果、模拟数据标记、元单位、风险与行动建议',
             depends_on=[1],input_files=['monthly_summary.csv'],output_files=['figure.svg','report.md'],
             verification=['矢量图与报告均存在并明确说明数据为模拟数据'])]}


def execute(case, library, mode, skill_name, budget, evaluation_plan_sha256=''):
    run = runtime.Run(run_id=runtime.new_run_id(runtime.task_fingerprint(case['task'])),task=case['task'],task_fp=runtime.task_fingerprint(case['task']),model=config.MODEL)
    run.budget=runtime.Budget(max_cost_yuan=budget,max_seconds=600,max_llm_calls=40)
    run.staged['execution_mode']=mode
    run.staged['evaluation_contract']=assessment.prepare_contract(case['task'])
    run.staged['evaluation_plan_sha256']=evaluation_plan_sha256
    if library.get(skill_name):
        from skillnet.governance import fingerprint
        run.staged['evaluated_skill_sha256']=fingerprint(library.get(skill_name))
    run.plan=plan(skill_name)
    # In-flight CLI evaluations must not be swept by API restart recovery.
    workspace=config.OUT_DIR/'evaluation_runs'/run.run_id
    store=runtime.RunStore(config.OUT_DIR/'evaluation_runs')
    run._checkpoint_writer=lambda:store.save(run)
    ledger=llm.UsageLedger()
    def guard():
        pipeline.sync_usage(run,ledger)
        runtime.check_budget(run)
    with llm.ledger_scope(ledger),llm.guard_scope(guard):
        pipeline.execute_run(run,library,workspace,run.plan,max_steps=3,workflow=None)
    pipeline.sync_usage(run,ledger)
    pipeline.finalize_status(run)
    result=evaluate_artifacts(case,run,workspace)
    run.staged['independent_evaluation']=result
    run.staged['quality_assessment']=assessment.assess(run,workspace,library)
    run.staged['learning_gate']={'eligible':False,'skip_reason':'冻结评测任务不更新生产反馈与技能库'}
    store.save(run)
    published=config.OUT_DIR/'runs'
    published.mkdir(parents=True,exist_ok=True)
    shutil.copytree(workspace/'artifacts',published/run.run_id/'artifacts',dirs_exist_ok=True)
    runtime.RunStore(published).save(run)  # Publish the terminal record atomically, after its files.
    return dict(run_id=run.run_id,score=result['score'],oracle=result,cost_yuan=run.cost_yuan,
                status=run.status,acceptance=run.staged['acceptance'])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repeats',type=int,default=None,choices=range(1,6))
    parser.add_argument('--case',default='operating-review')
    parser.add_argument('--budget-per-run',type=float,default=1.5)
    parser.add_argument('--candidate',type=Path)
    args=parser.parse_args()
    repeats=args.repeats or (2 if args.candidate else 1)
    library=SkillLibrary.load()
    selected=scenarios() if args.candidate else [r for r in scenarios() if r['id']==args.case]
    if not selected:raise ValueError('Unknown case')
    report=dict(evaluation_kind='paired-real-execution',protocol='heldout-task-cluster-v1',created_at=time.time(),repeats=repeats,
                oracle_scope='numeric correctness, schema, SVG presence, simulation label; does not grade managerial insight',
                pairs=[],cases=[])
    candidate=None
    evaluation_plan_sha256=''
    if args.candidate:
        candidate=json.loads(args.candidate.read_text(encoding='utf-8'))
        from skillnet.governance import fingerprint
        skill=Skill.from_dict(candidate['skill'])
        if candidate.get('state')!='candidate' or fingerprint(skill)!=candidate.get('sha256'):
            raise ValueError('Candidate state or content has changed; no model calls made')
        library.add(skill)
        report['candidate_sha256']=candidate['sha256']
        origin_hash=(skill.metadata.get('evidence_context') or {}).get('origin_task_sha256')
        if candidate.get('origin_run_id'):
            origin=runtime.RunStore(config.OUT_DIR/'runs').load(candidate['origin_run_id'])
            if origin is None:raise ValueError('Missing candidate origin; no model calls made')
            origin_hash=hashlib.sha256(origin.task.strip().encode()).hexdigest()
        if not origin_hash:raise ValueError('Unknown training task; no model calls made')
        excluded=set((skill.metadata.get('evidence_context') or {}).get('training_task_sha256') or []) | {origin_hash}
        selected=[c for c in selected if c['task_sha256'] not in excluded]
        if len(selected)<5 or repeats<2:raise ValueError('Need five held-out tasks and two repeats; no model calls made')
        report['excluded_training_task_sha256']=origin_hash
        report['excluded_known_training_tasks']=sorted(excluded)
        from skillnet.governance import evaluation_digest, evaluation_profile
        frozen_plan=dict(protocol='heldout-task-cluster-v1',candidate_sha256=candidate['sha256'],
            created_at_ms=runtime.now_ms(),tasks={c['task_sha256']:evaluation_digest(c) for c in selected},
            repeats=repeats,budget=runtime.Budget(max_cost_yuan=args.budget_per_run,max_seconds=600,max_llm_calls=40).to_dict(),
            profile=evaluation_profile(),arm_order='alternating_before_after')
        evaluation_plan_sha256=evaluation_digest(frozen_plan)
        directory=config.OUT_DIR/'evaluation_plans'
        directory.mkdir(parents=True,exist_ok=True)
        (directory/(evaluation_plan_sha256+'.json')).write_text(json.dumps(frozen_plan,ensure_ascii=False,indent=2),encoding='utf-8')
        report['evaluation_plan_sha256']=evaluation_plan_sha256
    for case in selected:
        for repeat in range(repeats):
            modes=(['before','after'] if repeat%2==0 else ['after','before']) if candidate else ['none','prompt','contract']
            results={}
            for mode in modes:
                name=skill.name if mode=='after' else 'business-metrics-audit'
                results[mode]=execute(case,library,'contract' if candidate else mode,name,args.budget_per_run,evaluation_plan_sha256)
                print(case['id'],repeat,mode,json.dumps(results[mode],ensure_ascii=False),flush=True)
                # Write after every arm: interruption preserves completed evidence and cost.
                report['cases'].append(dict(id=case['id'],task_sha256=case['task_sha256'],repeat=repeat,mode=mode,**results[mode]))
                (config.OUT_DIR/'execution-benchmark.current.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            if candidate:
                report['pairs'].append(dict(task_sha256=case['task_sha256'],repeat=repeat,frozen=True,
                    before_run_id=results['before']['run_id'],after_run_id=results['after']['run_id'],
                    before=results['before']['score'],after=results['after']['score']))
    path=config.OUT_DIR/('execution-benchmark-'+str(int(time.time()))+'.json')
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved',path)


if __name__=='__main__':main()
