"""Do not turn a fluent answer or self-authored criteria into global rewards."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from skillnet import assessment, runtime
from skillnet.bandit import SharedLinUCB
from skillnet.catalog import SkillLibrary
from skillnet.governance import (validate_promotion_design, validate_evaluation_plan,
    evaluation_digest, evaluation_profile, quarantine, promote)
from skillnet.schema import Skill
from skillnet.scenarios import scenarios, oracle


def library():
    return SkillLibrary([Skill(name, 'method '+name, 'data', steps=['read','compute','verify'])
                         for name in ('clean','summary','report')])


def artifact(workspace, name, text):
    path = workspace/'artifacts'/name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return runtime.Artifact(name=name, logical_name=name, bytes=path.stat().st_size,
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def business_run(workspace, case=None):
    case = case or scenarios()[0]
    run = runtime.Run('assessment-test', case['task'], 'test')
    run.staged['evaluation_contract'] = assessment.prepare_contract(run.task)
    # Independent fixture assembled from the frozen source; no model calls.
    lines = ['month,revenue,cost,gross_profit,gross_margin,orders']
    fields = lines[0].split(',')[1:]
    for month, values in oracle(case).items():
        lines.append(','.join([month]+[str(values[k]) for k in fields]))
    summary = artifact(workspace, 'monthly_summary.csv', '\n'.join(lines)+'\n')
    figure = artifact(workspace, 'figure.svg', '<svg>'+(' '*150)+'</svg>')
    report = artifact(workspace, 'report.md', '公开模拟数据，不代表真实经营情况。')
    clean = artifact(workspace, 'clean.csv', 'order_id,month,revenue,cost\nA,2026-01,1,1\n')
    run.steps = [runtime.RunStep(i, 'action', skill=name, status='done',
        artifacts=files, checks=[runtime.ProgrammaticCheck('file readable', True)],
        verifications=[runtime.VerificationResult('model likes it', True)])
        for i, name, files in [(0,'clean',[clean]),(1,'summary',[summary]),(2,'report',[figure,report])]]
    run.artifacts = [clean,summary,figure,report]
    run.judge = dict(weighted=10, score_valid=True)
    return run


def test_only_measured_producer_receives_scoped_observation(tmp_path):
    run = business_run(tmp_path)
    result = assessment.assess(run, tmp_path, library())
    assert result['scope_verdict'] == 'passed'
    assert result['overall_verdict'] == 'unconfirmed'
    assert [r['observed_score'] for r in result['observations']] == [None,1,None]
    assert result['candidate_eligible']
    assert not result['network']['applied'] and not result['network']['causal_attribution']
    # The intentionally meaningless clean.csv does not get an arithmetic reward.
    assert result['observations'][0]['verdict'] == 'unconfirmed'


def test_reference_identity_agrees_with_http_task_whitespace_normalization(tmp_path):
    run = business_run(tmp_path)
    frozen = run.staged['evaluation_contract']
    run.task = run.task.strip()
    assert assessment.prepare_contract(run.task) == frozen
    assert frozen['task_sha256'] == scenarios()[0]['task_sha256']
    assert assessment.assess(run,tmp_path,library())['scope_verdict'] == 'passed'


def test_high_model_score_and_passing_self_checks_are_not_a_result_reference(tmp_path):
    run = business_run(tmp_path)
    run.task = '请写一份让领导满意的策略报告'
    run.staged['evaluation_contract'] = assessment.prepare_contract(run.task)
    result = assessment.assess(run, tmp_path, library())
    assert result['scope_verdict'] == 'unknown'
    assert all(r['observed_score'] is None for r in result['observations'])
    assert not result['candidate_eligible']


@pytest.mark.parametrize('corruption', ['missing','changed','outside','late_contract'])
def test_untrusted_evidence_abstains_instead_of_scoring_user_result_bad(tmp_path, corruption):
    run = business_run(tmp_path)
    if corruption == 'missing':
        (tmp_path/'artifacts/monthly_summary.csv').unlink()
    elif corruption == 'changed':
        (tmp_path/'artifacts/monthly_summary.csv').write_text('forged')
    elif corruption == 'outside':
        run.artifacts[0].name = '../external.csv'
    else:
        run.staged['evaluation_contract']['reference_sha256'] = 'changed after execution'
    result = assessment.assess(run, tmp_path, library())
    assert result['scope_verdict'] == 'unknown'
    assert result['issues'] and not result['candidate_eligible']
    assert all(r['observed_score'] is None for r in result['observations'])


def test_wrong_numeric_result_overrules_model_approval_without_blame_spreading(tmp_path):
    run = business_run(tmp_path)
    target = tmp_path/'artifacts/monthly_summary.csv'
    target.write_text(target.read_text().replace('3500.0','9999.0'),encoding='utf-8')
    run.steps[1].artifacts[0].sha256 = hashlib.sha256(target.read_bytes()).hexdigest()
    run.steps[2].status = 'skipped'
    result = assessment.assess(run, tmp_path, library())
    assert result['scope_verdict'] == 'failed'
    assert result['observations'][1]['observed_score'] < 1
    assert result['observations'][0]['observed_score'] is None
    assert result['observations'][2]['verdict'] == 'blocked'
    assert not result['candidate_eligible']


@pytest.mark.parametrize('gate', ['omitted','missing_checks','semantic_unknown'])
def test_scoped_success_does_not_admit_an_incomplete_trajectory(tmp_path, gate):
    run = business_run(tmp_path)
    if gate == 'omitted':run.staged['execution_scope'] = dict(omitted=[dict(action='not done')])
    if gate == 'missing_checks':run.steps[0].checks = []
    if gate == 'semantic_unknown':run.steps[2].verifications[0].passed = False
    result = assessment.assess(run, tmp_path, library())
    assert result['scope_verdict'] == 'passed' and not result['candidate_eligible']


def test_shadow_update_is_bounded_and_never_mutates_serving_state_or_skill_statistics(tmp_path):
    lib = library()
    policy = SharedLinUCB(lib)
    before = copy.deepcopy(policy.state_dict())
    stats = [copy.deepcopy(s.stats) for s in lib]
    result = assessment.assess(business_run(tmp_path), tmp_path, lib)
    shadow = assessment.shadow_feedback(policy, 'task', result)
    assert policy.state_dict() == before and [s.stats for s in lib] == stats
    assert shadow['applied'] is False and len(shadow['policy_state_sha256']) == 64
    measured = [r for r in shadow['rows'] if r['observed_score'] is not None]
    assert len(measured) == 1 and measured[0]['shadow_delta'] > 0
    assert sum(r['weight'] for r in shadow['rows']) == .25
    assert all(r['delta'] == 0 and not r['nudged'] for r in shadow['rows'])
    preview = policy.preview_feedback('task', {'clean':1.,'report':0.,'missing':1.,'summary':float('nan')})
    assert sum(r['weight'] for r in preview['rows']) == .25
    assert {r['name'] for r in preview['rows']} == {'clean','report'}
    assert policy.state_dict() == before and [s.stats for s in lib] == stats


def pairs(tasks=5, repeats=2, gain=.1):
    return [dict(task_sha256=f'task-{t}',before=.7,after=.7+gain)
            for t in range(tasks) for _ in range(repeats)]


def test_repeats_are_task_clusters_not_independent_improvement_samples():
    with pytest.raises(ValueError,match='five held-out'):
        validate_promotion_design(pairs(tasks=2,repeats=20),{})
    result = validate_promotion_design(pairs(),{})
    assert result['tasks'] == 5 and result['one_sided_sign_p'] == 1/32
    assert result['mean_gain'] == pytest.approx(.1)


@pytest.mark.parametrize('fault', ['training','ancestor_training','one_pair','tiny_gain','one_tie','regression'])
def test_promotion_design_rejects_leakage_weak_evidence_and_regression(fault):
    evidence = pairs()
    candidate = {}
    if fault == 'training':candidate = dict(skill=dict(metadata=dict(evidence_context=dict(origin_task_sha256='task-1'))))
    if fault == 'ancestor_training':candidate = dict(skill=dict(metadata=dict(evidence_context=dict(training_task_sha256=['task-1']))))
    if fault == 'one_pair':evidence.pop()
    if fault == 'tiny_gain':evidence = pairs(gain=.001)
    if fault == 'one_tie':
        for p in evidence[-2:]:p['after'] = p['before']
    if fault == 'regression':evidence[0]['after'] = .6
    with pytest.raises(ValueError):validate_promotion_design(evidence,candidate)


@pytest.mark.parametrize('fault', ['omission','duplicate','reference','profile'])
def test_preregistered_suite_prevents_selective_reporting_and_posthoc_standards(fault):
    frozen = {c['task_sha256']:c for c in scenarios()[1:]}
    plan = dict(protocol='heldout-task-cluster-v1',candidate_sha256='candidate',repeats=2,
        tasks={k:evaluation_digest(c) for k,c in frozen.items()},profile=evaluation_profile())
    evidence = [dict(task_sha256=k,repeat=i) for k in frozen for i in range(2)]
    validate_evaluation_plan(plan,evidence,'candidate',frozen)
    if fault == 'omission':evidence.pop()
    if fault == 'duplicate':evidence[-1] = evidence[0]
    if fault == 'reference':plan['tasks'][next(iter(frozen))] = 'changed'
    if fault == 'profile':plan['profile']['model'] = 'different-model'
    with pytest.raises(ValueError):validate_evaluation_plan(plan,evidence,'candidate',frozen)


@pytest.mark.parametrize('fault', [None,'budget','training','tampered','wrong_score','posthoc'])
def test_promotion_recomputes_all_twenty_runs_and_checks_experiment_fairness(tmp_path,monkeypatch,fault):
    from skillnet import config
    from skillnet.scenarios import evaluate_artifacts
    monkeypatch.setattr(config,'OUT_DIR',tmp_path)
    cases = scenarios()[1:]
    store = runtime.RunStore(tmp_path/'runs')
    origin = business_run(tmp_path/'runs/origin')
    origin.run_id='origin'
    store.save(origin)
    skill=Skill('candidate','independently evaluated method','data',steps=['read','compute','check'],
        metadata=dict(evidence_context=dict(origin_task_sha256=scenarios()[0]['task_sha256'])))
    quarantine(skill,tmp_path/'candidates',origin_run_id='origin')
    candidate_path=next((tmp_path/'candidates').glob('*.json'))
    candidate=json.loads(candidate_path.read_text(encoding='utf-8'))
    plan=dict(protocol='heldout-task-cluster-v1',candidate_sha256=candidate['sha256'],created_at_ms=0,
        tasks={c['task_sha256']:evaluation_digest(c) for c in cases},repeats=2,
        budget=runtime.Budget().to_dict(),profile=evaluation_profile())
    if fault == 'training':
        origin.task=cases[0]['task'];store.save(origin)
    sha=evaluation_digest(plan)
    directory=tmp_path/'evaluation_plans';directory.mkdir()
    (directory/(sha+'.json')).write_text(json.dumps(plan),encoding='utf-8')
    report=dict(candidate_sha256=candidate['sha256'],evaluation_kind='paired-real-execution',
        evaluation_plan_sha256=sha,pairs=[])
    for i,case in enumerate(cases):
        for repeat in range(2):
            pair=dict(task_sha256=case['task_sha256'],repeat=repeat,frozen=True)
            for arm in ('before','after'):
                rid=f'{arm}-{i}-{repeat}'
                workspace=tmp_path/'runs'/rid
                run=business_run(workspace,case)
                run.run_id=rid;run.status='COMPLETED';run.model=plan['profile']['model']
                run.staged.update(execution_mode='contract',evaluation_plan_sha256=sha,
                    evaluated_skill_sha256=candidate['sha256'] if arm=='after' else 'baseline')
                run.plan=dict(steps=[dict(action=s.action,skill=s.skill,depends_on=s.depends_on) for s in run.steps])
                if arm=='after':run.steps[1].skill='candidate'
                if arm=='before':
                    path=workspace/'artifacts/monthly_summary.csv'
                    path.write_text('month,revenue,cost,gross_profit,gross_margin,orders\n')
                    run.steps[1].artifacts[0].sha256=hashlib.sha256(path.read_bytes()).hexdigest()
                score=evaluate_artifacts(case,run,workspace)['score']
                pair[arm]=score;pair[arm+'_run_id']=rid
                if i==0 and repeat==0 and arm=='after':
                    if fault=='budget':run.budget.max_cost_yuan+=1
                    if fault=='posthoc':run.started_at_ms=-1
                    if fault=='tampered':(workspace/'artifacts/monthly_summary.csv').write_text('corrupt')
                    if fault=='wrong_score':pair[arm]-=.01
                store.save(run)
            report['pairs'].append(pair)
    report_path=tmp_path/'report.json';report_path.write_text(json.dumps(report),encoding='utf-8')
    target=SkillLibrary([])
    saves=[];monkeypatch.setattr(target,'save',lambda:saves.append(True))
    if fault:
        with pytest.raises(ValueError):promote(candidate_path,report_path,target)
        assert not saves and len(target)==0
        assert json.loads(candidate_path.read_text(encoding='utf-8'))['state']=='candidate'
    else:
        promoted=promote(candidate_path,report_path,target)
        assert promoted.name=='candidate' and saves==[True] and len(target)==1
        assert promoted.metadata['governance_status']=='promoted'
