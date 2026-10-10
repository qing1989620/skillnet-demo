"""Versioned observations, never a self-judged reward or a causal improvement claim."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .contracts import projection_check
from .governance import fingerprint, evaluation_profile
from .scenarios import scenarios, evaluate_artifacts
from . import reward_gates

VERSION = 'outcome-evidence-v3'
NETWORK_REASON = '单次运行只产生经验观察；未证明技能的因果贡献或跨任务增益，正式排序与技能网络不更新'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def prepare_contract(task: str) -> dict:
    """Freeze the independent reference before execution; model plans are not references."""
    case = next((c for c in scenarios() if c['task'].strip() == task.strip()), None)
    return dict(version=VERSION, reward_policy_sha256=reward_gates.policy_sha256(), profile=evaluation_profile(),
                task_sha256=hashlib.sha256(task.strip().encode()).hexdigest(),
                source='frozen_business_reference' if case else 'user_task_without_independent_reference',
                case_id=case['id'] if case else None,
                reference_sha256=digest(case) if case else None,
                scope='月度汇总的独立算术、图表存在和模拟数据标记；不评价报告洞察' if case else '仅核对执行事实和可重算的步骤契约；不能证明用户整体目标已满足',
                unverified=['用户满意度', '报告洞察与业务价值', '技能的因果贡献', '网络是否整体提升'])


def _physical_files(run, workspace):
    root = (workspace/'artifacts').resolve()
    paths, checks = {}, []
    for artifact in run.artifacts:
        path = (root/artifact.name).resolve()
        valid = path.is_relative_to(root) and path.is_file()
        if valid:
            try:
                sha = hashlib.sha256()
                with path.open('rb') as stream:
                    while chunk := stream.read(65536):
                        sha.update(chunk)
                valid = sha.hexdigest() == artifact.sha256
            except OSError:
                valid = False
        checks.append(dict(name=artifact.name, passed=valid, sha256=artifact.sha256))
        if valid:
            paths[artifact.name] = path
    return paths, checks


def assess(run, workspace: Path, library) -> dict:
    expected = prepare_contract(run.task)
    prepared = run.staged.get('evaluation_contract')
    anchored = prepared == expected
    paths, integrity = _physical_files(run, workspace)
    intact = bool(integrity) and all(c['passed'] for c in integrity)
    independent, reference = {}, None
    issues = []
    if not anchored:
        issues.append('缺少执行前冻结的评价契约，不能事后补写标准答案')
    if any(not c['passed'] for c in integrity):
        issues.append('登记文件缺失或指纹不一致，证据不能用于学习')
    if anchored and intact and expected['case_id']:
        case = next(c for c in scenarios() if c['id'] == expected['case_id'])
        try:
            reference = evaluate_artifacts(case, run, workspace)
        except (OSError, ValueError, KeyError, UnicodeError):
            issues.append('独立参考检查不可用；保留未知，不能当作低分')
        if reference:
            # Attribute observations only to the actual producer of the measured table.
            # SVG existence and a simulation label cannot grade a visualization or report.
            numeric = [c for c in reference['checks'] if c['name'] not in ('矢量图存在', '报告标注模拟数据')]
            for step in run.steps:
                if any(a.name in paths and a.name.endswith('monthly_summary.csv') for a in step.artifacts):
                    independent.setdefault(step.idx, []).extend(numeric)
    if anchored and intact:
        for step in run.steps:
            inputs = {a['logical_name']: paths[a['name']] for a in step.input_artifacts
                      if a.get('name') in paths and a.get('logical_name')}
            outputs = {a.logical_name or a.name: paths[a.name] for a in step.artifacts if a.name in paths}
            for spec in step.contract.get('data_checks', []) if isinstance(step.contract.get('data_checks', []), list) else []:
                if isinstance(spec, dict) and spec.get('kind') == 'csv_projection':
                    independent.setdefault(step.idx, []).append(projection_check(spec, inputs, outputs))
    observations = []
    for step in run.steps:
        measured = independent.get(step.idx, [])
        necessary = [c for c in step.checks if c.required]
        reward = sum(c['passed'] is True for c in measured)/len(measured) if measured else None
        if step.status in ('pending', 'running', 'skipped') or not intact:
            reward = None
        kind = ('supported_in_scope' if reward == 1 else 'violated_in_scope' if reward is not None
                else 'blocked' if step.status == 'skipped' else 'unconfirmed')
        skill = library.get(step.skill) if step.skill and hasattr(library, 'get') else None
        observations.append(dict(idx=step.idx, skill=step.skill,
            skill_sha256=fingerprint(skill) if skill else None, verdict=kind,
            observed_score=reward, independent_checks=measured,
            necessary_passed=sum(c.passed for c in necessary), necessary_total=len(necessary),
            semantic_advisory=[v.to_dict() for v in step.verifications],
            reason='独立读取实际产物，仅支持本步骤已测量部分；不是技能因果贡献' if measured else
                   '上游阻断，不能归罪当前技能' if step.status == 'skipped' else
                   '执行与模型评价保留为事实；没有独立结果判据，不分配奖励'))
    measured = [c for row in observations for c in row['independent_checks']]
    reference_checks = reference['checks'] if reference else []
    failed = any(not c['passed'] for c in measured + reference_checks)
    # Broken evidence establishes an integrity problem, not a bad user result.
    scope = ('unknown' if not anchored or not intact or issues else
             'failed' if failed else 'passed' if measured else 'unknown')
    complete = bool(run.steps) and all(s.status == 'done' and any(c.required for c in s.checks)
        and all(c.passed for c in s.checks if c.required) and all(v.passed for v in s.verifications) for s in run.steps)
    omitted = (run.staged.get('execution_scope') or {}).get('omitted', [])
    candidate = complete and not omitted and scope == 'passed' and anchored and not issues
    result = dict(version=VERSION, task_sha256=expected['task_sha256'], goal_contract=prepared,
        reference_anchored_before_execution=anchored, scope_verdict=scope, overall_verdict='unconfirmed',
        scope=expected['scope'], unverified=expected['unverified'], integrity=integrity,
        independent_reference=reference, observations=observations, issues=issues,
        candidate_eligible=candidate, candidate_score=1.0 if candidate else None,
        network=dict(mode='shadow', applied=False, causal_attribution=False, reason=NETWORK_REASON))
    result['evidence_sha256'] = digest(result)
    return result


def shadow_feedback(policy, task, assessment):
    """Preview one bounded update on detached parameters. Never call live update()."""
    observed = {}
    for row in assessment['observations']:
        if row['skill'] and row['observed_score'] is not None:
            observed.setdefault(row['skill'], []).append(row['observed_score'])
    rewards = {name: sum(values)/len(values) for name, values in observed.items()}
    preview = policy.preview_feedback(task, rewards) if hasattr(policy, 'preview_feedback') else {}
    simulated = {r['name']: r for r in preview.get('rows', [])}
    names = sorted({row['skill'] for row in assessment['observations'] if row['skill']})
    before = {name:e for name, _p, e, _x in policy.rank(task, names)}
    rows = [dict(name=name, exploit_before=before.get(name, 0), exploit_after=before.get(name, 0),
                 delta=0.0, nudged=False, mode='shadow', observed_score=rewards.get(name),
                 shadow_exploit_after=simulated.get(name, {}).get('after'),
                 shadow_delta=simulated.get(name, {}).get('delta'),
                 weight=simulated.get(name, {}).get('weight', 0),
                 skip_reason=NETWORK_REASON) for name in names]
    return dict(mode='shadow', applied=False, rows=rows,
                policy_state_sha256=preview.get('policy_state_sha256'),
                evidence_sha256=assessment['evidence_sha256'], reason=NETWORK_REASON)
