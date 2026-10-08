"""Candidate quarantine and promotion backed by frozen execution evidence."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import time

from .schema import Skill


def fingerprint(skill: Skill) -> str:
    return hashlib.sha256(skill.to_skill_md().encode()).hexdigest()


def quarantine(skill: Skill, directory: Path, *, origin_run_id='') -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    record = dict(skill=skill.to_dict(), sha256=fingerprint(skill), state='candidate',
                  origin_run_id=origin_run_id, created_at=time.time(),
                  promotion_policy='frozen paired real executions; no regression; positive quality gain')
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
    # Recompute from stored runs and physical files; a JSON score is not evidence.
    from . import config, runtime
    from .scenarios import scenarios, evaluate_artifacts
    frozen = {c['task_sha256']: c for c in scenarios() if c['frozen']}
    store = runtime.RunStore(config.OUT_DIR / 'runs')
    seen_runs = set()
    for pair in pairs:
        case = frozen.get(pair['task_sha256'])
        if case is None:
            raise ValueError('Unknown frozen task')
        for arm in ('before','after'):
            run_id = pair[arm + '_run_id']
            if run_id in seen_runs or not re.fullmatch(r'[a-zA-Z0-9-]+', run_id):
                raise ValueError('Duplicated or invalid run evidence')
            seen_runs.add(run_id)
            run = store.load(run_id)
            if run is None or run.task != case['task'] or run.status != 'COMPLETED':
                raise ValueError('Missing completed frozen run evidence')
            if arm == 'after' and not any(s.skill == skill.name for s in run.steps):
                raise ValueError('Candidate was not used by the evaluated run')
            if arm == 'after' and run.staged.get('evaluated_skill_sha256') != candidate['sha256']:
                raise ValueError('Run did not record this exact candidate content')
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
    skill.metadata.update(governance_status='promoted', evidence_report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest())
    library.add(skill)
    library.save()
    candidate.update(state='promoted', promoted_at=time.time(), report=report_path.name)
    candidate_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding='utf-8')
    return skill
