"""Read-only capability evidence. Declarations and observed transitions stay separate.

This is an audit projection, not a learned world model, causal estimator or a
proof of behavioral equivalence. No catalogue, rewards or run history is changed.
"""
from .evidence import digest
from .governance import fingerprint


def passport(skill):
    """Current declared scope only; historical stats never certify this version."""
    return dict(version='skillnet-passport-v1', name=skill.name, skill_sha256=fingerprint(skill),
        evidence_kind='current_declaration', capability=skill.capability or skill.description,
        activation=list(skill.use_when), inputs=list(skill.inputs), effects=list(skill.outputs),
        failure_boundary=list(skill.pitfalls), verification=list(skill.verification),
        environment=skill.compatibility or None, allowed_tools=skill.allowed_tools or None,
        empirical_success_probability=None, causal_effect=None,
        boundary='这些字段是技能声明与注意事项，不代表运行时条件已经满足；成功率与因果效果尚未估计')


def transitions(capsule):
    """Use a freshly rehashed capsule; bind composition to exact consumed files."""
    files=capsule.get('files', [])
    rows=[]
    links=[]
    gaps=[]
    chain=capsule.get('chain', [])
    for step in chain:
        idx=step['idx']
        inputs=[]
        for item in step.get('inputs', []):
            # Physical filename + digest + producer, not similar prose or logical name.
            matches=[f for f in files if f['name']==item.get('name') and f['sha256']==item.get('sha256')
                and f.get('producer_step')==item.get('from_step')]
            f=matches[0] if len(matches)==1 else None
            intact=f is not None and f['integrity']=='passed'
            inputs.append(dict(name=item.get('name'), sha256=item.get('sha256'),
                producer_step=item.get('from_step'), integrity='passed' if intact else 'unknown_or_failed'))
            if item.get('from_step') is not None:
                links.append(dict(source=item['from_step'], target=idx, file=item.get('name'),
                    source_run_id=f.get('source_run_id') if f else None,
                    sha256=item.get('sha256'), kind='recorded_file_consumption',
                    integrity='passed' if intact else 'unknown_or_failed',
                    boundary='文件交接可复核，不证明上下游技能语义兼容或因果贡献'))
        outputs=[dict(name=f['name'],sha256=f['sha256'],integrity=f['integrity']) for f in files
            if f.get('producer_step')==idx and f.get('role')=='output' and f['name'] in step.get('outputs', [])]
        independent=step.get('independent_checks', [])
        checks=step.get('checks', [])
        required=[c for c in checks if c.get('required') is not False]
        observed=bool(independent) and all(c.get('passed') is True for c in independent)
        intact=bool(outputs) and all(f['integrity']=='passed' for f in outputs)
        status='observed_in_scope' if (step['status']=='done' and observed and intact
            and capsule.get('scope_verified') is True and all(c.get('passed') is True for c in required)
            and all(i['integrity']=='passed' for i in inputs)) else 'not_confirmed'
        if independent and any(c.get('passed') is False for c in independent):status='violated_in_scope'
        if step['status']=='failed':status='execution_failed'
        if any(f['integrity']!='passed' for f in outputs):status='artifact_integrity_failed'
        generic=not step.get('skill') or step['skill']=='manual'
        if generic:gaps.append(dict(kind='unbound_skill',step=idx,reason='该动作由通用执行完成，尚未绑定可复用技能；不是任务无法完成'))
        if not independent:gaps.append(dict(kind='missing_independent_verifier',step=idx,reason='本步骤没有独立结果判据，不能从运行成功推断能力已验证'))
        if any(i['integrity']!='passed' for i in inputs):gaps.append(dict(kind='unverified_input',step=idx,reason='输入文件的名称、版本或生产步骤未能与登记记录一致绑定'))
        if not intact:gaps.append(dict(kind='unverified_effect',step=idx,reason='尚无完整且指纹一致的登记产物，不能确认状态变化'))
        if not step.get('skill_sha256') and not generic:gaps.append(dict(kind='unrecorded_version',step=idx,reason='历史技能版本未记录，不能认证当前版本'))
        state_evidence = step.get('state_evidence') or {}
        pre = state_evidence.get('pre') or {}
        if pre.get('admitted') is False:
            gaps.append(dict(kind='state_admission_blocked',step=idx,
                reason='实际输入未满足或无法核实冻结的前置条件；本步未调用代码生成，不将其记为技能负贡献'))
        rows.append(dict(idx=idx,action=step.get('action'),skill=None if generic else step.get('skill'),
            skill_sha256=step.get('skill_sha256'), version_capture=step.get('version_capture'),
            status=step['status'], observation=status, inputs=inputs, effects=outputs,
            checks=dict(passed=sum(c.get('passed') is True for c in required),total=len(required)),
            independent_checks=dict(passed=sum(c.get('passed') is True for c in independent),total=len(independent)),
            applicability=pre.get('state', 'not_measured'), causal_contribution='not_measured',
            boundary='只陈述本次文件与限定范围检查，不外推跨任务成功率'))
        if state_evidence:
            rows[-1]['state_evidence'] = state_evidence
    for item in capsule.get('delivery',{}).get('omitted_steps',[]):
        gaps.append(dict(kind='unexecuted_plan',step=item.get('idx'),reason=item.get('action') or '有规划动作未执行'))
    report=dict(version='skillnet-transitions-v1',run_id=capsule['run_id'],
        source_capsule_sha256=capsule['capsule_sha256'], source='recorded_execution_and_rehashed_files',
        scope_verified=capsule.get('scope_verified') is True,
        scope=capsule.get('acceptance',{}).get('scope'),steps=rows,composition=links,evidence_gaps=gaps,
        summary=dict(steps=len(rows),observed_in_scope=sum(r['observation']=='observed_in_scope' for r in rows),
            verified_file_links=sum(e['integrity']=='passed' for e in links),file_links=len(links),evidence_gaps=len(gaps)),
        research_status=dict(learned_causal_model=False,behavioral_equivalence=False,minimal_basis=False,reachable_space_proven=False),
        boundary='证据缺口不等于缺少真实能力；文件组合不等于因果技能代数；报告不会发奖或修改技能库')
    if capsule.get('state_kernel'):
        report['state_kernel'] = capsule['state_kernel']
    if capsule.get('capability_frontier'):
        report['capability_frontier'] = capsule['capability_frontier']
    report['report_sha256']=digest(report)
    return report
