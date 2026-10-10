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
    sources = ['pipeline.py','executor.py','contracts.py','checks.py','scenarios.py','llm.py','governance.py','promotion.py','reward_gates.py','assessment.py','runtime.py','schema.py']
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
    """Award only after all versioned constraints pass on physical evidence."""
    from .promotion import award
    return award(candidate_path, report_path, library)



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
