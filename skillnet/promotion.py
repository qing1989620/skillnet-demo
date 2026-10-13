"""Read-only reward audit, followed by a single atomic library award commit."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from . import config, runtime, reward_gates
from .governance import (fingerprint, evaluation_digest, evaluation_profile,
                         known_training_tasks, validate_evaluation_plan)
from .schema import Skill
from .scenarios import scenarios, evaluate_artifacts


class MissingEvidence(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _load_run(run_id):
    path = config.OUT_DIR/'runs'/(run_id+'.json')
    return runtime.RunStore._from_dict(json.loads(path.read_text(encoding='utf-8'))) if path.is_file() else None


def _gains(pairs):
    if not pairs:
        raise MissingEvidence('没有真实配对数据')
    groups = {}
    for pair in pairs:
        before, after = pair.get('before'), pair.get('after')
        _require(_number(before) and _number(after) and 0 <= before <= 1 and 0 <= after <= 1,
                 'Scores must come from finite artifact oracles in [0, 1]')
        _require(bool(pair.get('task_sha256')), 'Missing task identity')
        groups.setdefault(pair['task_sha256'], []).append(after-before)
    gains = [sum(values)/len(values) for values in groups.values()]
    nonzero = [g for g in gains if abs(g)>1e-9]
    wins = sum(g>0 for g in nonzero)
    p = sum(math.comb(len(nonzero), k) for k in range(wins,len(nonzero)+1))/2**len(nonzero)
    return dict(tasks=len(groups), pairs=len(pairs), mean_gain=sum(gains)/len(gains),
        one_sided_sign_p=p, task_gains=dict(zip(groups,gains)))


def inspect_promotion(candidate_path: Path, report_path: Path, library) -> dict:
    """Collect all twelve decisions. Never mutate a library, run or receipt here."""
    audit = reward_gates.Audit(dict(kind='candidate_improvement'))
    try:
        candidate = json.loads(candidate_path.read_text(encoding='utf-8'))
        report_raw = report_path.read_bytes()
        report = json.loads(report_raw)
        _require(isinstance(candidate,dict) and isinstance(report,dict), 'Invalid candidate or report object')
        skill = Skill.from_dict(candidate['skill'])
        _require(isinstance(skill.metadata,dict), 'Invalid skill metadata')
        pairs = report.get('pairs') or []
        _require(isinstance(pairs,list) and all(isinstance(p,dict) for p in pairs), 'Invalid evaluation pairs')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        audit.set('version','unknown','候选或报告不可读取：'+str(exc))
        return audit.result()
    audit.context.update(candidate_name=skill.name, candidate_sha256=candidate.get('sha256'),
        report_sha256=hashlib.sha256(report_raw).hexdigest(),
        evaluation_plan_sha256=report.get('evaluation_plan_sha256'))
    frozen = {c['task_sha256']:c for c in scenarios() if c['frozen']}
    plan, arms = None, []
    rules = reward_gates.policy()

    def check(key, fn):
        try:
            evidence = fn() or {}
            audit.set(key,'passed','规定全部满足',**evidence)
        except MissingEvidence as exc:
            audit.set(key,'unknown',str(exc))
        except (ValueError, OSError, KeyError, TypeError, OverflowError) as exc:
            audit.set(key,'failed',str(exc))

    def need_plan():
        if plan is None:
            raise MissingEvidence('缺少可信的执行前评测计划')
        return plan

    def need_arms():
        if not arms or len(arms)!=len(pairs)*2:
            raise MissingEvidence('缺少完整可读取的配对运行记录')
        return arms

    def freeze():
        nonlocal plan
        sha = report.get('evaluation_plan_sha256') or ''
        if not re.fullmatch(r'[0-9a-f]{64}',sha):
            raise MissingEvidence('Missing preregistered evaluation plan')
        path = config.OUT_DIR/'evaluation_plans'/(sha+'.json')
        loaded = json.loads(path.read_text(encoding='utf-8'))
        _require(evaluation_digest(loaded)==sha, 'Evaluation plan content changed')
        _require(loaded.get('reward_policy_sha256')==reward_gates.policy_sha256(),
                 'Reward rules were not frozen before execution; rerun the suite')
        _require(loaded.get('profile')==evaluation_profile(), 'Evaluation implementation or model changed; rerun the frozen suite')
        _require(loaded.get('protocol')=='heldout-task-cluster-v1', 'Unknown evaluation protocol')
        _require(loaded.get('candidate_sha256')==candidate.get('sha256'), 'Plan evaluates a different candidate')
        _require(loaded.get('candidate_record_sha256')==evaluation_digest(candidate),
                 'Candidate origin or quarantine record changed after registration')
        _require(_number(loaded.get('created_at_ms')), 'Missing pre-execution registration time')
        for task, reference in (loaded.get('tasks') or {}).items():
            _require(task in frozen and evaluation_digest(frozen[task])==reference, 'Frozen task or reference changed')
        plan = loaded  # A failed plan never becomes trusted input for other gates.
        return dict(evaluation_plan_sha256=sha, policy_sha256=reward_gates.policy_sha256())

    check('frozen',freeze)

    # Read exactly the declared records. Reuse/omission is independently blocked
    # by the suite gate, even when individual records happen to be readable.
    loading_issue = None
    for pair in pairs:
        for arm in ('before','after'):
            rid = pair.get(arm+'_run_id')
            if not isinstance(rid,str) or not re.fullmatch(r'[a-zA-Z0-9-]+',rid):
                loading_issue = 'Missing or invalid frozen run identity'
                continue
            try:
                run = _load_run(rid)
            except (OSError,ValueError,KeyError,TypeError):
                run = None
            if run is None:
                loading_issue = 'Missing physical run record'
            else:
                arms.append((pair,arm,run,config.OUT_DIR/'runs'/rid))

    def independent():
        need_plan()
        for pair,arm,run,workspace in need_arms():
            case = frozen.get(pair.get('task_sha256'))
            _require(case is not None and run.task.strip()==case['task'].strip(), 'Unknown or mismatched frozen task')
            actual = evaluate_artifacts(case,run,workspace)
            claimed = pair.get(arm)
            _require(_number(claimed) and abs(actual['score']-claimed)<=1e-9,
                     'Report score disagrees with physical artifact oracle')
            if arm=='after':
                _require(bool(actual['checks']) and all(c['passed'] is True for c in actual['checks']),
                         'Candidate failed an independent result constraint')
        return dict(runs=len(arms),scope='独立业务算术、文件存在与模拟数据标记；不评价管理洞察')

    def integrity():
        files = 0
        for _pair,_arm,run,workspace in need_arms():
            root = (workspace/'artifacts').resolve()
            _require(bool(run.artifacts), 'Missing physical artifact evidence')
            names = set()
            for artifact in run.artifacts:
                path = (root/artifact.name).resolve()
                _require(artifact.name not in names and path.is_relative_to(root) and path.is_file(),
                         'Missing, duplicated or unsafe physical artifact evidence')
                names.add(artifact.name)
                _require(hashlib.sha256(path.read_bytes()).hexdigest()==artifact.sha256,
                         'Artifact evidence changed after evaluation')
                files += 1
            registered = {a.name:a.sha256 for a in run.artifacts}
            _require(all(registered.get(a.name)==a.sha256 for s in run.steps for a in s.artifacts),
                     'Step artifact is not bound to the registered evidence')
        return dict(files=files)

    def complete():
        for _pair,arm,run,_workspace in need_arms():
            _require(run.status=='COMPLETED' and not run.cancel_requested, 'Missing completed frozen run evidence')
            _require(_number(run.cost_yuan) and 0<=run.cost_yuan<=run.budget.max_cost_yuan
                and 0<=run.llm_calls<=run.budget.max_llm_calls
                and run.ended_at_ms>=run.started_at_ms
                and run.ended_at_ms-run.started_at_ms<=run.budget.max_seconds*1000,
                'Execution exceeded its frozen cost, call or time budget')
            if arm=='after':
                _require(bool(run.steps) and all(s.status=='done' and any(c.required for c in s.checks)
                    and all(c.passed is True for c in s.checks if c.required)
                    and all(v.passed is True for v in s.verifications) for s in run.steps)
                    and not (run.staged.get('execution_scope') or {}).get('omitted'),
                    'Candidate execution was incomplete or failed acceptance')
                expected_steps = run.plan.get('steps') or []
                _require(len(expected_steps)==len(run.steps), 'Candidate omitted planned steps')
                _require([s.idx for s in run.steps]==list(range(len(run.steps)))
                    and all(s.action==p.get('action') and s.depends_on==p.get('depends_on',[])
                            for s,p in zip(run.steps,expected_steps)), 'Executed actions differ from the frozen step graph')
        return dict(candidate_runs=len(arms)//2)

    def version():
        p = need_plan()
        _require(candidate.get('state') in ('candidate','promoted') and fingerprint(skill)==candidate.get('sha256'),
                 'Candidate state or content has changed')
        _require(report.get('candidate_sha256')==candidate['sha256'] and report.get('evaluation_kind')=='paired-real-execution',
                 'Report does not evaluate this exact candidate')
        baseline = p.get('baseline_skill') or {}
        current = library.get(baseline.get('name'))
        _require(current is not None and fingerprint(current)==baseline.get('sha256'), 'Serving baseline changed; rerun the paired evaluation')
        _require(baseline['name']!=skill.name, 'Candidate cannot replace its own frozen baseline')
        for _pair,arm,run,_workspace in need_arms():
            name = skill.name if arm=='after' else baseline['name']
            sha = candidate['sha256'] if arm=='after' else baseline['sha256']
            _require(bool(run.steps) and all(s.skill==name for s in run.steps)
                     and run.staged.get('evaluated_skill_sha256')==sha, 'Evaluated treatment or baseline differs from the frozen plan')
        return dict(candidate_sha256=candidate['sha256'],baseline_sha256=baseline['sha256'])

    def fair():
        p = need_plan()
        runs = {run.run_id:run for _,_,run,_ in need_arms()}
        for _pair,_arm,run,_ in arms:
            _require(run.staged.get('evaluation_plan_sha256')==report['evaluation_plan_sha256']
                and run.started_at_ms>=p['created_at_ms'] and run.budget.to_dict()==p.get('budget')
                and run.model==p['profile']['model'] and run.staged.get('execution_mode')=='contract',
                'Run does not match the pre-execution evaluation plan')
        for pair in pairs:
            before,after = runs[pair['before_run_id']],runs[pair['after_run_id']]
            _require(type(pair.get('repeat')) is int, 'Missing repeat identity')
            first,second = (before,after) if pair['repeat']%2==0 else (after,before)
            _require(first.started_at_ms<=second.started_at_ms, 'Paired arm order differs from the frozen plan')
            steps = lambda run: [{k:v for k,v in s.items() if k!='skill'} for s in run.plan.get('steps',[])]
            _require(bool(steps(before)) and steps(before)==steps(after), 'Paired runs must use the same planned actions and dependencies')
        return dict(model=p['profile']['model'],budget=p['budget'],arm_order=p.get('arm_order'))

    def heldout():
        p = need_plan()
        origin_id = candidate.get('origin_run_id')
        if not isinstance(origin_id,str) or not re.fullmatch(r'[a-zA-Z0-9-]+',origin_id):
            raise MissingEvidence('Missing candidate origin; cannot establish held-out tasks')
        origin = _load_run(origin_id)
        if origin is None:
            raise MissingEvidence('Missing candidate origin; cannot establish held-out tasks')
        context = skill.metadata.get('evidence_context') or {}
        training = known_training_tasks(library,skill.parent) | set(context.get('training_task_sha256') or [])
        training.add(hashlib.sha256(origin.task.strip().encode()).hexdigest())
        if context.get('origin_task_sha256'):
            training.add(context['origin_task_sha256'])
        _require(sorted(training)==p.get('known_training_task_sha256'),
                 'Recorded training lineage changed after registration')
        _require(all(p.get('task_sha256') not in training for p in pairs), 'Training task leaked into evaluation')
        _require(all(run.run_id!=origin_id for _,_,run,_ in need_arms()), 'Training run cannot be evaluation evidence')
        return dict(excluded_known_tasks=len(training),scope='已记录的任务谱系；外部预训练内容不可观测')

    def suite():
        p = need_plan()
        validate_evaluation_plan(p,pairs,candidate['sha256'],frozen)
        _require(not loading_issue,loading_issue or 'Missing runs')
        need_arms()
        ids = [run.run_id for _,_,run,_ in arms]
        _require(len(ids)==len(set(ids)) and all(pair.get('frozen') is True for pair in pairs), 'Duplicated or unfrozen run evidence')
        return dict(tasks=len(p['tasks']),pairs=len(pairs),physical_runs=len(ids))

    def regression():
        _gains(pairs)
        _require(all(p['after']>=p['before'] for p in pairs), 'Candidate regressed; gains cannot cancel a failed pair')
        return dict(regressed_pairs=0)

    def gain():
        result = _gains(pairs)
        _require(result['mean_gain']>=rules['min_mean_gain'], 'No measured improvement; candidate stays quarantined' if result['mean_gain']<=0 else 'Mean gain is below the frozen 0.02 threshold')
        return result

    def reliable():
        result = _gains(pairs)
        _require(result['tasks']>=rules['min_tasks'] and result['one_sided_sign_p']<=rules['max_sign_p'],
                 'Insufficient task-level improvement evidence; repeats are not independent tasks')
        return dict(one_sided_sign_p=result['one_sided_sign_p'],unit='distinct_task')

    def novel():
        _require(candidate.get('state')=='candidate', 'This candidate was already promoted; no duplicate reward')
        for item in library.all():
            receipt = item.stats.get('verified_improvement_receipt') or {}
            _require(receipt.get('candidate_sha256')!=candidate.get('sha256'), 'This exact version was already rewarded')
        _require(library.get(skill.name) is None, 'Candidate name already exists; never overwrite an existing rewarded version')
        return dict(rewarded_version=candidate.get('sha256'),max_points=rules['max_points'])

    for key,fn in [('independent',independent),('integrity',integrity),('complete',complete),
        ('version',version),('fair',fair),('heldout',heldout),('suite',suite),
        ('regression',regression),('gain',gain),('reliable',reliable),('novel',novel)]:
        check(key,fn)
    return audit.result()


def award(candidate_path: Path, report_path: Path, library) -> Skill:
    # Library persistence is atomic. Keep the receipt and skill in that same
    # commit, so a failed save cannot leave an independently credited ledger.
    with library._lock:
        decision = inspect_promotion(candidate_path,report_path,library)
        if not decision['eligible']:
            reasons = [r['title']+': '+r['reason'] for r in decision['gates'] if r['status']!='passed']
            raise ValueError('Reward blocked: '+'; '.join(reasons))
        candidate = json.loads(candidate_path.read_text(encoding='utf-8'))
        skill = Skill.from_dict(candidate['skill'])
        _require(fingerprint(skill)==decision['context']['candidate_sha256']
            and hashlib.sha256(report_path.read_bytes()).hexdigest()==decision['context']['report_sha256'],
            'Candidate or report changed during reward verification')
        gain = next(r['evidence']['mean_gain'] for r in decision['gates'] if r['id']=='gain')
        points = round(min(reward_gates.policy()['max_points'],gain*reward_gates.policy()['points_per_gain']),6)
        receipt = dict(candidate_sha256=candidate['sha256'],
            report_sha256=decision['context']['report_sha256'],
            evaluation_plan_sha256=decision['context']['evaluation_plan_sha256'],
            policy_sha256=decision['policy_sha256'], audit_sha256=decision['audit_sha256'],
            points=points, measured_mean_gain=gain, scope=decision['reward_scope'],
            ranking_weights_deployed=False, credited_skill=skill.name)
        receipt['id'] = reward_gates.digest(receipt)
        skill.stats.update(verified_improvement_points=points, verified_improvement_receipt=receipt)
        skill.metadata.update(governance_status='promoted',evidence_report_sha256=receipt['report_sha256'])
        old_dirty = library.dirty
        library.add(skill)
        try:
            library.save()
        except Exception:
            library.remove(skill.name)
            library.dirty = old_dirty
            raise
        # The library receipt is authoritative. If this secondary state write
        # is interrupted, the novelty gate still prevents another award.
        import time
        import os
        import tempfile
        candidate.update(state='promoted',promoted_at=time.time(),report=report_path.name,
                         reward_receipt=receipt,reward_audit=decision)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=candidate_path.parent,delete=False) as stream:
            json.dump(candidate,stream,ensure_ascii=False,indent=2)
            temp = stream.name
        try:
            os.replace(temp,candidate_path)
        finally:
            Path(temp).unlink(missing_ok=True)
        return skill
