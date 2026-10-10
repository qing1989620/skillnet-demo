"""Do not turn a fluent answer or self-authored criteria into global rewards."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from skillnet import assessment, runtime, reward_gates
from skillnet.promotion import inspect_promotion
from skillnet.bandit import SharedLinUCB
from skillnet.catalog import SkillLibrary
from skillnet.governance import (validate_promotion_design, validate_evaluation_plan,
    evaluation_digest, evaluation_profile, fingerprint, quarantine, promote)
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
    run.model = run.staged['evaluation_contract']['profile']['model']
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


@pytest.mark.parametrize('fault', ['omission','duplicate','reference','profile','baseline'])
def test_preregistered_suite_prevents_selective_reporting_and_posthoc_standards(fault):
    frozen = {c['task_sha256']:c for c in scenarios()[1:]}
    plan = dict(protocol='heldout-task-cluster-v1',candidate_sha256='candidate',repeats=2,
        tasks={k:evaluation_digest(c) for k,c in frozen.items()},profile=evaluation_profile(),
        baseline_skill=dict(name='baseline',sha256='a'*64),arm_order='alternating_before_after')
    evidence = [dict(task_sha256=k,repeat=i) for k in frozen for i in range(2)]
    validate_evaluation_plan(plan,evidence,'candidate',frozen)
    if fault == 'omission':evidence.pop()
    if fault == 'duplicate':evidence[-1] = evidence[0]
    if fault == 'reference':plan['tasks'][next(iter(frozen))] = 'changed'
    if fault == 'profile':plan['profile']['model'] = 'different-model'
    if fault == 'baseline':del plan['baseline_skill']
    with pytest.raises(ValueError):validate_evaluation_plan(plan,evidence,'candidate',frozen)


@pytest.mark.parametrize('fault', [None,'budget','training','tampered','wrong_score','posthoc','baseline_swap','baseline_changed','arm_order',
    'rules','cancelled','omitted','necessary','semantic','partial_result','cost','calls','time','replay','duplicate_award','save_failure','secondary_write'])
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
        source='distill',
        metadata=dict(evidence_context=dict(origin_task_sha256=scenarios()[0]['task_sha256'])))
    quarantine(skill,tmp_path/'candidates',origin_run_id='origin')
    candidate_path=next((tmp_path/'candidates').glob('*.json'))
    candidate=json.loads(candidate_path.read_text(encoding='utf-8'))
    baseline=Skill('baseline','serving method','data',steps=['read','compute','verify'])
    baseline_sha=fingerprint(baseline)
    plan=dict(protocol='heldout-task-cluster-v1',candidate_sha256=candidate['sha256'],created_at_ms=0,
        reward_policy_sha256=reward_gates.policy_sha256(),
        candidate_record_sha256=evaluation_digest(candidate),known_training_task_sha256=[scenarios()[0]['task_sha256']],
        tasks={c['task_sha256']:evaluation_digest(c) for c in cases},repeats=2,
        budget=runtime.Budget().to_dict(),profile=evaluation_profile(),
        baseline_skill=dict(name='baseline',sha256=baseline_sha),arm_order='alternating_before_after')
    if fault=='rules':plan['reward_policy_sha256']='post-hoc-rules'
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
            for arm in (('before','after') if repeat%2==0 else ('after','before')):
                rid=f'{arm}-{i}-{repeat}'
                workspace=tmp_path/'runs'/rid
                run=business_run(workspace,case)
                run.run_id=rid;run.status='COMPLETED';run.model=plan['profile']['model']
                run.ended_at_ms=run.started_at_ms
                run.staged.update(execution_mode='contract',evaluation_plan_sha256=sha,
                    evaluated_skill_sha256=candidate['sha256'] if arm=='after' else baseline_sha)
                for step in run.steps:step.skill='candidate' if arm=='after' else 'baseline'
                run.plan=dict(steps=[dict(action=s.action,skill=s.skill,depends_on=s.depends_on) for s in run.steps])
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
                    if fault=='arm_order':run.started_at_ms=1
                    if fault=='cancelled':run.cancel_requested=True
                    if fault=='omitted':run.staged['execution_scope']=dict(omitted=[dict(action='unfinished')])
                    if fault=='necessary':run.steps[0].checks[0].passed=False
                    if fault=='semantic':run.steps[0].verifications[0].passed=False
                    if fault=='cost':run.cost_yuan=run.budget.max_cost_yuan+.1
                    if fault=='calls':run.llm_calls=run.budget.max_llm_calls+1
                    if fault=='time':run.ended_at_ms+=run.budget.max_seconds*1000+1
                    if fault=='partial_result':
                        path=workspace/'artifacts/report.md';path.write_text('no simulation label')
                        run.steps[2].artifacts[1].sha256=hashlib.sha256(path.read_bytes()).hexdigest()
                        pair[arm]=evaluate_artifacts(case,run,workspace)['score']
                if i==0 and repeat==0 and arm=='before' and fault=='baseline_swap':run.steps[0].skill='unrelated-bad-baseline'
                store.save(run)
            report['pairs'].append(pair)
    if fault=='replay':report['pairs'][-1]=report['pairs'][0]
    report_path=tmp_path/'report.json';report_path.write_text(json.dumps(report),encoding='utf-8')
    if fault=='baseline_changed':baseline.steps.append('new implementation')
    target=SkillLibrary([baseline])
    if fault=='duplicate_award':
        previous=Skill('already-awarded','previous receipt','data')
        previous.stats['verified_improvement_receipt']=dict(candidate_sha256=candidate['sha256'])
        target.add(previous)
    initial=len(target)
    saves=[];monkeypatch.setattr(target,'save',lambda:saves.append(True))
    if fault=='secondary_write':
        import os
        with monkeypatch.context() as patch:
            def fail_replace(*args):raise OSError('candidate state write unavailable')
            patch.setattr(os,'replace',fail_replace)
            with pytest.raises(OSError):promote(candidate_path,report_path,target)
        assert saves==[True] and target.get('candidate').stats['verified_improvement_receipt']
        assert json.loads(candidate_path.read_text(encoding='utf-8'))['state']=='candidate'
        with pytest.raises(ValueError,match='already rewarded'):promote(candidate_path,report_path,target)
        assert saves==[True]
    elif fault=='save_failure':
        def fail_save():raise OSError('disk unavailable')
        monkeypatch.setattr(target,'save',fail_save)
        with pytest.raises(OSError):promote(candidate_path,report_path,target)
        assert target.get('candidate') is None
        assert json.loads(candidate_path.read_text(encoding='utf-8'))['state']=='candidate'
    elif fault:
        decision=inspect_promotion(candidate_path,report_path,target)
        assert len(decision['gates'])==12 and not decision['eligible']
        assert decision['blockers'] and not decision['reward_applied']
        with pytest.raises(ValueError):promote(candidate_path,report_path,target)
        assert not saves and len(target)==initial
        assert json.loads(candidate_path.read_text(encoding='utf-8'))['state']=='candidate'
    else:
        policy=SharedLinUCB(target)
        policy_before=copy.deepcopy(policy.state_dict())
        decision=inspect_promotion(candidate_path,report_path,target)
        assert decision['eligible'] and decision['passed']==12 and not saves
        promoted=promote(candidate_path,report_path,target)
        assert promoted.name=='candidate' and saves==[True] and len(target)==2
        assert promoted.metadata['governance_status']=='promoted'
        assert 0<promoted.stats['verified_improvement_points']<=25
        receipt=promoted.stats['verified_improvement_receipt']
        assert receipt['credited_skill']=='candidate' and receipt['candidate_sha256']==candidate['sha256']
        assert not receipt['ranking_weights_deployed'] and policy.state_dict()==policy_before
        assert not baseline.stats.get('verified_improvement_points')
        assert json.loads(candidate_path.read_text(encoding='utf-8'))['reward_receipt']==receipt
        # Resetting a copied candidate's state cannot bypass the library receipt.
        copied=tmp_path/'copied.json'
        copied.write_text(json.dumps(candidate),encoding='utf-8')
        with pytest.raises(ValueError,match='already rewarded'):promote(copied,report_path,target)
        assert saves==[True]
        # A real atomic library save preserves points and receipt across restart.
        persisted=tmp_path/'library.json'
        SkillLibrary([baseline,promoted]).save(persisted)
        restored=SkillLibrary.load(persisted,include_community=False).get('candidate')
        assert restored.stats['verified_improvement_receipt']==receipt


def test_single_run_gates_abstain_on_missing_comparison_even_with_perfect_judge(tmp_path):
    run=business_run(tmp_path)
    result=assessment.assess(run,tmp_path,library())
    decision=reward_gates.observation_gates(run,result)
    assert decision['passed']==4 and not decision['eligible']
    assert len(decision['gates'])==12 and decision['points']==0
    assert all(r['status']=='unknown' for r in decision['gates'][4:])
    run.judge['weighted']=0
    assert reward_gates.observation_gates(run,result)==decision


@pytest.mark.parametrize('status',['unknown','failed'])
def test_and_gate_requires_every_constraint_even_if_eleven_pass(status):
    for blocked in reward_gates.GATES:
        audit=reward_gates.Audit()
        for key,_,_ in reward_gates.GATES:audit.set(key,'passed','fixture')
        audit.set(blocked[0],status,'missing or failed evidence')
        result=audit.result()
        assert not result['eligible'] and result['blockers']==[blocked[0]]
        assert result['points']==0 and not result['reward_applied']


def test_cli_promotion_lock_prevents_two_writers_and_releases_after_error(tmp_path,monkeypatch):
    from skillnet import config
    from tools.promote_candidate import promotion_lock
    monkeypatch.setattr(config,'OUT_DIR',tmp_path)
    with pytest.raises(ValueError,match='writer failure'):
        with promotion_lock():
            with pytest.raises(RuntimeError,match='writer lock'):
                with promotion_lock():pass
            raise ValueError('writer failure')
    assert not (tmp_path/'.promotion.lock').exists()
    with promotion_lock():assert (tmp_path/'.promotion.lock').exists()


def test_promotion_refuses_a_live_api_or_worker_writer(tmp_path,monkeypatch):
    from skillnet import config
    from skillnet.worker import acquire_writer_lock
    from tools.promote_candidate import promotion_lock
    monkeypatch.setattr(config,'OUT_DIR',tmp_path)
    writer=acquire_writer_lock(tmp_path/'worker.lock')
    try:
        with pytest.raises(RuntimeError,match='Stop the API writer'):
            with promotion_lock():pytest.fail('must not write a stale library snapshot')
    finally:
        writer.close()
    assert not (tmp_path/'.promotion.lock').exists()
    with promotion_lock():pass


def test_read_only_audit_does_not_create_a_missing_run_store(tmp_path,monkeypatch):
    from skillnet import config
    monkeypatch.setattr(config,'OUT_DIR',tmp_path/'uncreated')
    candidate=tmp_path/'candidate.json';report=tmp_path/'report.json'
    skill=Skill('candidate','method','data')
    candidate.write_text(json.dumps(dict(skill=skill.to_dict(),sha256=fingerprint(skill),state='candidate')))
    report.write_text(json.dumps(dict(pairs=[])))
    decision=inspect_promotion(candidate,report,SkillLibrary([]))
    assert not decision['eligible'] and not (tmp_path/'uncreated').exists()


def test_cli_keeps_catalog_diagnostics_out_of_audit_json(monkeypatch,capsys):
    from tools.promote_candidate import load_library
    sentinel=object()
    def noisy_load():
        print('catalog diagnostic')
        return sentinel
    monkeypatch.setattr(SkillLibrary,'load',noisy_load)
    assert load_library() is sentinel
    captured=capsys.readouterr()
    assert captured.out=='' and captured.err=='catalog diagnostic\n'
