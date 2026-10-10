"""Read-only evidence handoff to a host product. Never awards or regrades history."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote

from .runtime import TERMINAL

VERSION = 'skillnet-evidence-v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def capsule(run, workspace: Path):
    """Project an authorized Run; verify exact registered files at request time."""
    data = run.to_dict(with_events=False)
    staged = data.get('staged') or {}
    assessment = staged.get('quality_assessment') or {}
    versions = staged.get('skill_versions') or {}
    observations = {r['idx']: r for r in assessment.get('observations', [])}
    root = (workspace/'artifacts').resolve()
    files = []
    for artifact in run.artifacts:
        path = (root/artifact.name).resolve()
        valid = (path.is_relative_to(root) and path.is_file()
            and bool(re.fullmatch(r'[0-9a-f]{64}', artifact.sha256)))
        actual = None
        if valid:
            try:
                hasher = hashlib.sha256()
                with path.open('rb') as stream:
                    while chunk := stream.read(65536):
                        hasher.update(chunk)
                actual = hasher.hexdigest()
                valid = actual == artifact.sha256 and path.stat().st_size == artifact.bytes
            except OSError:
                valid = False
        consumers = [s.idx for s in run.steps if any(i.get('name') == artifact.name
            and i.get('sha256') == artifact.sha256 for i in s.input_artifacts)]
        files.append(dict(name=artifact.name, logical_name=artifact.logical_name or artifact.name,
            sha256=artifact.sha256, bytes=artifact.bytes, integrity='passed' if valid else 'failed',
            actual_sha256=actual, role='input' if artifact.kind == '跨轮输入' else 'output',
            producer_step=artifact.from_step, consumed_by=consumers, source_run_id=artifact.source_run_id or run.run_id,
            download_path=f'/api/runs/{quote(run.run_id, safe="")}/artifacts/{quote(artifact.name, safe="")}'))
    chain = []
    for step in run.steps:
        recorded = versions.get(step.skill) or {}
        observation = observations.get(step.idx) or {}
        chain.append(dict(idx=step.idx, action=step.action, skill=step.skill, status=step.status,
            depends_on=step.depends_on, skill_sha256=recorded.get('sha256') or observation.get('skill_sha256'),
            version_capture='before_execution' if recorded else 'recorded_observation' if observation.get('skill_sha256') else 'unrecorded',
            code_sha256=hashlib.sha256(step.code.encode()).hexdigest() if step.code else None,
            attempts=len(step.attempts), inputs=step.input_artifacts,
            outputs=[a.name for a in step.artifacts],
            checks=[c.to_dict() for c in step.checks],
            independent_checks=observation.get('independent_checks', []),
            semantic_advisory=[v.to_dict() for v in step.verifications]))
    terminal = run.status in TERMINAL
    intact = bool(files) and all(f['integrity'] == 'passed' for f in files)
    scoped = intact and assessment.get('scope_verdict') == 'passed' and assessment.get('reference_anchored_before_execution') is True
    gates = staged.get('reward_gates') or {}
    value = dict(version=VERSION, run_id=run.run_id, task=run.task, status=run.status,
        task_sha256=hashlib.sha256(run.task.strip().encode()).hexdigest(),
        run_record_sha256=digest(data), verification='registered_files_rehashed_on_read',
        handoff_ready=terminal and intact, scope_verified=scoped,
        delivery=dict(completed_steps=sum(s.status == 'done' for s in run.steps), total_steps=len(run.steps),
            output_files=sum(f['role'] == 'output' for f in files), cost_yuan=run.cost_yuan,
            model=run.model, llm_calls=run.llm_calls, duration_ms=run.duration_ms,
            omitted_steps=(staged.get('execution_scope') or {}).get('omitted', [])),
        files=files, chain=chain,
        acceptance=dict(source='recorded_at_execution', protocol=assessment.get('version'),
            verdict=assessment.get('scope_verdict', 'unknown'), scope=assessment.get('scope'),
            contract=assessment.get('goal_contract'), evidence_sha256=assessment.get('evidence_sha256'),
            unverified=assessment.get('unverified', ['此历史记录未提供独立结果评价'])),
        reuse=dict(candidate=bool(run.evolution.get('candidate')), skill_name=run.evolution.get('name'),
            gates_passed=gates.get('passed', 0), gates_total=gates.get('total', 12),
            improvement_proven=False, reward_applied=gates.get('reward_applied') is True,
            policy_sha256=gates.get('policy_sha256'), ranking_weights_deployed=False),
        host_product=dict(target='立理 S1', production_connection_verified=False,
            mapping=dict(task='project conversation', chain='execution timeline', files='project attachments',
                acceptance='result evidence', reuse='candidate capability asset'),
            next_action='S1 backend verifies capsule digest, downloads files with expected SHA-256, and applies its project permissions'),
        limitations=['文件指纹证明文件一致性，不证明研究结论正确',
            '独立结果评价沿用执行时已冻结的范围，未对历史任务重新评分',
            '单次任务不证明技能贡献或网络增益，候选技能不自动准入'])
    value['capsule_sha256'] = digest(value)
    return value
