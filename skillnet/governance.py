"""Candidate quarantine and promotion backed by frozen execution evidence."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import re
import time

from .schema import Skill


def fingerprint(skill: Skill) -> str:
    return hashlib.sha256(skill.to_skill_md().encode()).hexdigest()


def evaluation_digest(value) -> str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',', ':')).encode()).hexdigest()


def evaluation_profile() -> dict:
    from . import config
    import os
    sources = ['pipeline.py','executor.py','contracts.py','checks.py','scenarios.py','llm.py','governance.py']
    return dict(model=config.MODEL,sandbox=os.environ.get('SKILLNET_SANDBOX','local'),
                sources={p:hashlib.sha256((Path(__file__).parent/p).read_bytes()).hexdigest() for p in sources})


def validate_evaluation_plan(plan, pairs, candidate_sha256, frozen) -> None:
    """Require the complete preregistered suite, preventing post-hoc winner selection."""
    if plan.get('protocol') != 'heldout-task-cluster-v1' or plan.get('candidate_sha256') != candidate_sha256:
        raise ValueError('Evaluation plan does not bind this candidate and protocol')
    baseline = plan.get('baseline_skill') or {}
    if (not baseline.get('name') or not re.fullmatch(r'[0-9a-f]{64}',baseline.get('sha256',''))
            or plan.get('arm_order') != 'alternating_before_after'):
        raise ValueError('Evaluation plan must freeze the baseline version and arm order')
    repeats, tasks = plan.get('repeats'), plan.get('tasks') or {}
    if type(repeats) is not int or repeats < 2 or len(tasks) < 5:
        raise ValueError('Evaluation plan must freeze five tasks and at least two repeats')
    for task, reference in tasks.items():
        if task not in frozen or evaluation_digest(frozen[task]) != reference:
            raise ValueError('Frozen task or reference changed after registration')
    expected = {(task,repeat) for task in tasks for repeat in range(repeats)}
    actual = [(p.get('task_sha256'),p.get('repeat')) for p in pairs]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError('Missing, duplicated or selectively reported evaluation pairs')
    if plan.get('profile') != evaluation_profile():
        raise ValueError('Evaluation implementation or model changed; rerun the frozen suite')


def known_training_tasks(library, names) -> set[str]:
    """Recorded task lineage only; external model pretraining is not observable."""
    found, seen, pending = set(), set(), list(names)
    while pending:
        name = pending.pop()
        if name in seen:continue
        seen.add(name)
        skill = library.get(name)
        if skill is None:continue
        if skill.origin_task:found.add(hashlib.sha256(skill.origin_task.strip().encode()).hexdigest())
        context = skill.metadata.get('evidence_context') or {}
        if isinstance(context, dict):
            found.update(context.get('training_task_sha256') or [])
            if context.get('origin_task_sha256'):found.add(context['origin_task_sha256'])
        pending.extend(skill.parent)
    return found


def quarantine(skill: Skill, directory: Path, *, origin_run_id='') -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    record = dict(skill=skill.to_dict(), sha256=fingerprint(skill), state='candidate',
                  origin_run_id=origin_run_id, created_at=time.time(),
                  promotion_policy='5 held-out tasks x 2 pairs; matched budget; no regression; mean gain >= .02; task-cluster sign test p <= .05; scoped claims only')
    suffix = ('-' + record['sha256'][:8] + '-' + hashlib.sha256(origin_run_id.encode()).hexdigest()[:8]) if origin_run_id else ''
    path = directory / (skill.name + suffix + '.json')
    if path.exists():
        existing = json.loads(path.read_text(encoding='utf-8'))
        if existing['sha256'] == record['sha256']:
            return existing
        raise ValueError('Candidate content collision')
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    return record


def promote(candidate_path: Path, report_path: Path, library) -> Skill:
    candidate = json.loads(candidate_path.read_text(encoding='utf-8'))
    report = json.loads(report_path.read_text(encoding='utf-8'))
    skill = Skill.from_dict(candidate['skill'])
    if candidate['state'] != 'candidate' or fingerprint(skill) != candidate['sha256']:
        raise ValueError('Candidate state or content has changed')
    if report.get('candidate_sha256') != candidate['sha256'] or report.get('evaluation_kind') != 'paired-real-execution':
        raise ValueError('Report does not evaluate this exact candidate')
    pairs = report.get('pairs') or []
    if len(pairs) < 4 or len({p.get('task_sha256') for p in pairs}) < 2:
        raise ValueError('At least two frozen tasks and four paired executions required')
    differences = []
    for pair in pairs:
        if not pair.get('frozen') or not pair.get('before_run_id') or not pair.get('after_run_id'):
            raise ValueError('Missing actual frozen run evidence')
        before, after = pair.get('before'), pair.get('after')
        if type(before) not in (float, int) or type(after) not in (float, int):
            raise ValueError('Scores must come from artifact oracles')
        if not 0 <= before <= after <= 1:
            raise ValueError('Candidate regressed or score is invalid')
        differences.append(after-before)
    if sum(differences) <= 0:
        raise ValueError('No measured improvement; candidate stays quarantined')
    if not candidate.get('origin_run_id'):
        raise ValueError('Missing candidate origin; cannot establish held-out tasks')
    validate_promotion_design(pairs, candidate)
    # Recompute from stored runs and physical files; a JSON score is not evidence.
    from . import config, runtime
    from .scenarios import scenarios, evaluate_artifacts
    frozen = {c['task_sha256']: c for c in scenarios() if c['frozen']}
    plan_sha = report.get('evaluation_plan_sha256') or ''
    if not re.fullmatch(r'[0-9a-f]{64}',plan_sha):
        raise ValueError('Missing preregistered evaluation plan')
    plan_path = config.OUT_DIR/'evaluation_plans'/(plan_sha+'.json')
    if not plan_path.is_file():raise ValueError('Missing physical evaluation plan')
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    if evaluation_digest(plan) != plan_sha:raise ValueError('Evaluation plan content changed')
    validate_evaluation_plan(plan,pairs,candidate['sha256'],frozen)
    baseline = plan['baseline_skill']
    current_baseline = library.get(baseline['name'])
    if current_baseline is None or fingerprint(current_baseline) != baseline['sha256']:
        raise ValueError('Serving baseline changed; rerun the paired evaluation')
    store = runtime.RunStore(config.OUT_DIR / 'runs')
    seen_runs = set()
    for pair in pairs:
        case = frozen.get(pair['task_sha256'])
        if case is None:
            raise ValueError('Unknown frozen task')
        arms = {}
        for arm in ('before','after'):
            run_id = pair[arm + '_run_id']
            if run_id in seen_runs or not re.fullmatch(r'[a-zA-Z0-9-]+', run_id):
                raise ValueError('Duplicated or invalid run evidence')
            seen_runs.add(run_id)
            run = store.load(run_id)
            if run is None or run.task.strip() != case['task'].strip() or run.status != 'COMPLETED':
                raise ValueError('Missing completed frozen run evidence')
            arms[arm] = run
            if (run.staged.get('evaluation_plan_sha256') != plan_sha
                    or run.started_at_ms < plan.get('created_at_ms', float('inf'))
                    or run.budget.to_dict() != plan.get('budget') or run.model != plan['profile']['model']):
                raise ValueError('Run does not match the pre-execution evaluation plan')
            expected_name = skill.name if arm == 'after' else baseline['name']
            expected_sha = candidate['sha256'] if arm == 'after' else baseline['sha256']
            if (not run.steps or any(s.skill != expected_name for s in run.steps)
                    or run.staged.get('evaluated_skill_sha256') != expected_sha):
                raise ValueError('Evaluated treatment or baseline differs from the frozen plan')
            if run.run_id == candidate.get('origin_run_id'):
                raise ValueError('Training run cannot be evaluation evidence')
            if arm == 'before' and any(s.skill == skill.name for s in run.steps):
                raise ValueError('Baseline already used this candidate')
            if arm == 'after' and not any(s.skill == skill.name for s in run.steps):
                raise ValueError('Candidate was not used by the evaluated run')
            if arm == 'after' and run.staged.get('evaluated_skill_sha256') != candidate['sha256']:
                raise ValueError('Run did not record this exact candidate content')
            if arm == 'after' and (not run.steps or any(s.status != 'done'
                    or not any(c.required for c in s.checks)
                    or any(not c.passed for c in s.checks if c.required)
                    or any(not v.passed for v in s.verifications) for s in run.steps)
                    or (run.staged.get('execution_scope') or {}).get('omitted')):
                raise ValueError('Candidate execution was incomplete or failed acceptance')
            workspace = config.OUT_DIR / 'runs' / run_id
            for artifact in run.artifacts:
                path = (workspace / 'artifacts' / artifact.name).resolve()
                if not path.is_relative_to((workspace / 'artifacts').resolve()) or not path.is_file():
                    raise ValueError('Missing physical artifact evidence')
                if hashlib.sha256(path.read_bytes()).hexdigest() != artifact.sha256:
                    raise ValueError('Artifact evidence changed after evaluation')
            measured = evaluate_artifacts(case, run, workspace)['score']
            if abs(measured - pair[arm]) > 1e-9:
                raise ValueError('Report score disagrees with physical artifact oracle')
        before, after = arms['before'], arms['after']
        first, second = (before,after) if pair['repeat'] % 2 == 0 else (after,before)
        if first.started_at_ms > second.started_at_ms:
            raise ValueError('Paired arm order differs from the frozen plan')
        if before.budget.to_dict() != after.budget.to_dict() or before.model != after.model:
            raise ValueError('Paired runs must use identical budgets and model')
        if before.staged.get('execution_mode') != 'contract' or after.staged.get('execution_mode') != 'contract':
            raise ValueError('Paired runs must use the same execution mode')
        steps = lambda run: [{k:v for k,v in s.items() if k != 'skill'} for s in run.plan.get('steps',[])]
        if not steps(before) or steps(before) != steps(after):
            raise ValueError('Paired runs must use the same planned actions and dependencies')
    # Old candidates may lack task metadata. Recover it from the actual origin
    # record rather than trusting that a different run ID means a held-out task.
    origin_id = candidate.get('origin_run_id')
    if origin_id:
        origin = store.load(origin_id)
        if origin is None:
            raise ValueError('Missing candidate origin; cannot establish held-out tasks')
        if hashlib.sha256(origin.task.strip().encode()).hexdigest() in {p['task_sha256'] for p in pairs}:
            raise ValueError('Training task leaked into evaluation')
    skill.metadata.update(governance_status='promoted', evidence_report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest())
    library.add(skill)
    library.save()
    candidate.update(state='promoted', promoted_at=time.time(), report=report_path.name)
    candidate_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding='utf-8')
    return skill


def validate_promotion_design(pairs: list[dict], candidate: dict) -> dict:
    """Design gate only. Physical runs and artifacts must still be recomputed.

    Repeats of the same task are one statistical cluster, never extra samples.
    This test supports only the frozen suite's measured scope, not global skill
    quality. The thresholds are a conservative release policy, not a theorem.
    """
    context = candidate.get('skill', {}).get('metadata', {}).get('evidence_context') or {}
    training = set(context.get('training_task_sha256') or [])
    if context.get('origin_task_sha256'):training.add(context['origin_task_sha256'])
    groups = {}
    for pair in pairs:
        task = pair.get('task_sha256')
        if not task or task in training:
            raise ValueError('Training task leaked into evaluation')
        before, after = pair.get('before'), pair.get('after')
        if (type(before) not in (int, float) or type(after) not in (int, float)
                or not 0 <= before <= after <= 1):
            raise ValueError('Candidate regressed or score is invalid')
        groups.setdefault(task, []).append(after-before)
    if len(groups) < 5 or any(len(values) < 2 for values in groups.values()):
        raise ValueError('At least five held-out tasks with two pairs each required')
    gains = [sum(values)/len(values) for values in groups.values()]
    mean_gain = sum(gains)/len(gains)
    nonzero = [g for g in gains if abs(g) > 1e-9]
    wins = sum(g > 0 for g in nonzero)
    p = sum(math.comb(len(nonzero), k) for k in range(wins, len(nonzero)+1)) / 2**len(nonzero)
    if mean_gain < .02 or p > .05:
        raise ValueError('Insufficient task-level improvement evidence; candidate stays quarantined')
    return dict(tasks=len(groups), pairs=len(pairs), mean_gain=mean_gain,
                one_sided_sign_p=p, unit='distinct_task', scope='frozen suite only')
