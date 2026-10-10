"""Fail-closed, versioned AND gates. An observation is not an improvement reward."""
from __future__ import annotations

import hashlib
import json
import math
import time

VERSION = 'improvement-gates-v1'
GATES = (
    ('frozen', '标准提前冻结', '执行前锁定判据、阈值、模型与评测代码，禁止事后改规则'),
    ('independent', '独立重算结果', '从真实产物重算冻结的业务参考，模型评分不能替代'),
    ('integrity', '物理产物可信', '实际文件存在、路径合法、SHA-256 与登记一致'),
    ('complete', '执行完整合格', '候选全部步骤完成、必要验收通过、无删步取消或预算超限'),
    ('version', '绑定技能版本', '对照组与候选组实际执行冻结的精确技能版本'),
    ('fair', '对照条件公平', '模型、预算、动作依赖相同，并按预定次序交替执行'),
    ('heldout', '任务未用于生成', '排除当前任务、记录的祖先训练任务和实际来源运行'),
    ('suite', '完整报告样本', '至少 5 道留出任务各 2 组配对，禁止漏报、重用或挑选赢家'),
    ('regression', '每组没有退步', '每一组候选结果均不低于对应基线，提升不能抵消退步'),
    ('gain', '增益达到门槛', '按不同任务等权计算平均增益，至少 0.02'),
    ('reliable', '多任务一致提升', '以不同任务为统计单位，单侧符号检验 p ≤ 0.05'),
    ('novel', '同一版本只奖一次', '积分只给被验证版本；相同版本不能重放或换报告重复领奖'),
)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def policy():
    return dict(version=VERSION, operator='AND', unknown_blocks=True,
        min_tasks=5, min_repeats=2, min_mean_gain=.02, max_sign_p=.05,
        max_points=25, points_per_gain=100,
        reward_scope='此技能版本在冻结评测范围内的相对提升积分；不代表全网或所有任务提升',
        ranking_weights_deployed=False,
        gates=[dict(id=key, title=title, rule=rule) for key, title, rule in GATES])


def policy_sha256():
    return digest(policy())


class Audit:
    def __init__(self, context=None):
        self.rows = {key:dict(id=key, title=title, rule=rule, status='unknown',
            reason='缺少对应证据，不能放行', evidence={}) for key,title,rule in GATES}
        self.context = context or {}

    def set(self, key, status, reason, **evidence):
        if status not in ('passed', 'failed', 'unknown'):
            raise ValueError('Unknown gate status')
        self.rows[key].update(status=status, reason=reason, evidence=evidence)

    def result(self):
        rows = list(self.rows.values())
        eligible = all(row['status'] == 'passed' for row in rows)
        value = dict(version=VERSION, policy_sha256=policy_sha256(), operator='AND',
            eligible=eligible, reward_applied=False, points=0,
            passed=sum(r['status']=='passed' for r in rows), total=len(rows),
            blockers=[r['id'] for r in rows if r['status']!='passed'], gates=rows,
            context=self.context, reward_scope=policy()['reward_scope'],
            ranking_weights_deployed=False)
        value['audit_sha256'] = digest(value)
        return value


def observation_gates(run, assessment):
    """Show what this run can establish; never invent the missing comparison."""
    audit = Audit(dict(kind='single_run', run_id=run.run_id,
        assessment_sha256=assessment['evidence_sha256']))
    contract = assessment.get('goal_contract') or {}
    from .governance import evaluation_profile
    frozen = (assessment['reference_anchored_before_execution'] and contract.get('reward_policy_sha256') == policy_sha256()
        and contract.get('profile') == evaluation_profile() and contract['profile']['model'] == run.model)
    audit.set('frozen', 'passed' if frozen else 'unknown',
        '本次结果判据与奖励规则在执行前冻结；晋级还需预注册对照计划' if frozen else '未记录当前奖励规则的执行前冻结证据',
        task_sha256=assessment['task_sha256'], policy_sha256=contract.get('reward_policy_sha256'))
    audit.set('independent', {'passed':'passed','failed':'failed'}.get(assessment['scope_verdict'],'unknown'),
        '仅证明本次已测范围；尚无与旧版本的独立对照', scope=assessment['scope'])
    integrity = assessment['integrity']
    audit.set('integrity', 'passed' if integrity and all(r['passed'] is True for r in integrity) else 'failed' if integrity else 'unknown',
        '重新读取实际文件并核对指纹', checked=len(integrity))
    # Worker evaluates before the terminal status is assigned: rely on steps,
    # cancellation and budget facts, not an optimistic overall status string.
    complete = bool(run.steps) and all(s.status=='done' and any(c.required for c in s.checks)
        and all(c.passed is True for c in s.checks if c.required)
        and all(v.passed is True for v in s.verifications) for s in run.steps)
    elapsed = (run.ended_at_ms or int(time.time()*1000))-run.started_at_ms
    within_budget = (math.isfinite(run.cost_yuan) and 0 <= run.cost_yuan <= run.budget.max_cost_yuan
        and 0 <= run.llm_calls <= run.budget.max_llm_calls and 0<=elapsed<=run.budget.max_seconds*1000)
    complete = complete and within_budget and not run.cancel_requested and not (run.staged.get('execution_scope') or {}).get('omitted')
    if run.status in ('PARTIAL','FAILED','CANCELLED','INTERRUPTED','BUDGET_EXCEEDED'):
        complete = False
    audit.set('complete', 'passed' if complete else 'failed',
        '本次执行完整，必要验收通过' if complete else '存在未完成、未通过验收、取消、删步或超预算',
        steps=len(run.steps), cost_yuan=run.cost_yuan if math.isfinite(run.cost_yuan) else None)
    # Remaining gates concern a candidate-versus-baseline experiment. A live
    # trajectory, even a perfect one, does not provide those facts.
    return audit.result()
