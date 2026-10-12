"""Freeze executable state contracts; host references cannot be weakened by a plan.

Model predicates are hypotheses. A matching host scenario adds independently
defined requirements. Neither declaration is an observed effect or a reward.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from . import research
from .runtime import Artifact, now_ms

VERSION = 'state-admission-v1'


def input_catalog(task):
    if task.strip() != research.research_scenario()['task'].strip():
        return []
    raw = research.DATA.encode()
    return [dict(file='raw_predictions.csv',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
        source='host_public_synthetic_input',boundary='公开任务原始输入，不是清洗或指标参考答案')]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_predicates(names):
    if not isinstance(names, list) or len(names) > 32:
        return [dict(kind='invalid_file_contract', file='')]
    return [dict(kind='file_exists', file=name) for name in names]


def _merge(existing, required):
    if not isinstance(existing, list) or len(existing) > 32:
        return [dict(kind='invalid_state_contract', file='')]
    result = copy.deepcopy(existing)
    for spec in required:
        if spec not in result:
            result.append(copy.deepcopy(spec))
    return result


def declaration(step):
    return {key:copy.deepcopy(step.contract.get(key, [])) for key in ('requires', 'ensures', 'input_files', 'output_files')}


def clean_conditions(file='clean_predictions.csv'):
    return [dict(kind='csv_schema', file=file,
                 columns=['sample_id','subject_id','split','label','score'], exact=True),
            dict(kind='csv_nonempty', file=file),
            dict(kind='csv_unique', file=file, columns=['sample_id']),
            dict(kind='csv_no_missing', file=file, columns=['sample_id','subject_id','split','label','score']),
            dict(kind='csv_numeric_range', file=file, column='score', min=0, max=1),
            dict(kind='csv_values_in', file=file, column='label', values=[0,1]),
            dict(kind='csv_disjoint_groups', file=file, entity='subject_id', group='split')]


def bind(run, workspace: Path):
    """Called once before execution. Preserve hypotheses and attach trusted scope."""
    is_research = run.task.strip() == research.research_scenario()['task'].strip()
    if is_research:
        raw = research.DATA.encode()
        root = workspace/'artifacts'
        root.mkdir(parents=True, exist_ok=True)
        name = 'input_raw_predictions.csv'
        if any(a.name == name for a in run.artifacts):
            raise ValueError('Host input name already registered')
        path = root/name
        # Never overwrite an existing physical input silently.
        with path.open('xb') as stream:
            stream.write(raw)
        run.artifacts.append(Artifact(name=name, logical_name='raw_predictions.csv',
            kind='任务输入', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
            source_run_id=run.run_id))
    for step in run.steps:
        step.contract['requires'] = _merge(step.contract.get('requires', []),
            file_predicates(step.contract.get('input_files', [])))
        step.contract['ensures'] = _merge(step.contract.get('ensures', []),
            file_predicates(step.contract.get('output_files', [])))
        outputs = step.contract.get('output_files', [])
        trusted_pre, trusted_post = [], []
        if is_research:
            if 'clean_predictions.csv' in outputs:
                step.contract['input_files'] = list(dict.fromkeys(
                    step.contract.get('input_files', []) + ['raw_predictions.csv']))
                trusted_pre += [dict(kind='csv_schema', file='raw_predictions.csv',
                    columns=['sample_id','subject_id','split','label','score'], exact=True),
                    dict(kind='csv_nonempty', file='raw_predictions.csv')]
                trusted_post += clean_conditions()
            if 'cohort_audit.csv' in outputs:
                trusted_post += [dict(kind='csv_schema',file='cohort_audit.csv',columns=['check','count'],exact=True)]
            if 'heldout_metrics.csv' in outputs:
                # A fused clean+metrics action checks the cleaned table on exit.
                if 'clean_predictions.csv' not in outputs:
                    trusted_pre += clean_conditions()
                    step.contract['input_files'] = list(dict.fromkeys(
                        step.contract.get('input_files', []) + ['clean_predictions.csv']))
                trusted_post += [dict(kind='csv_schema',file='heldout_metrics.csv',columns=['metric','value'],exact=True),
                    dict(kind='csv_nonempty',file='heldout_metrics.csv')]
            if 'report.md' in outputs and 'heldout_metrics.csv' not in outputs:
                trusted_pre += [dict(kind='csv_schema',file='heldout_metrics.csv',columns=['metric','value'],exact=True)]
                step.contract['input_files'] = list(dict.fromkeys(
                    step.contract.get('input_files', []) + ['heldout_metrics.csv']))
        step.contract['requires'] = _merge(step.contract['requires'], trusted_pre)
        step.contract['ensures'] = _merge(step.contract['ensures'], trusted_post)
        step.contract['state_contract_source'] = 'host_reference_and_plan' if trusted_pre or trusted_post else 'plan_hypothesis_and_file_contract'
    frozen = {str(s.idx):dict(declaration=declaration(s), sha256=digest(declaration(s)),
        source=s.contract['state_contract_source']) for s in run.steps}
    return dict(version=VERSION, task_sha256=hashlib.sha256(run.task.strip().encode()).hexdigest(),
        captured_at_ms=now_ms(), frozen=frozen,
        host_reference='research-reproducibility-v1' if is_research else None,
        boundary='状态声明经真实文件判定后才成为本次观测；不代表跨环境成功率、因果贡献或全库能力边界')


def check_rows(report, phase):
    rows = [dict(name=f'状态{phase}：{(c.get("predicate") if isinstance(c.get("predicate"),dict) else {}).get("kind", "invalid")} / {(c.get("predicate") if isinstance(c.get("predicate"),dict) else {}).get("file", "")}',
                 passed=c.get('state') == 'passed',
                 detail=c.get('state', 'unknown') + ' · ' + c.get('detail', ''), required=True)
            for c in report.get('checks', [])]
    if not rows and report.get('state') not in ('passed','not_declared'):
        rows.append(dict(name=f'状态{phase}：未知条件',passed=False,detail='unknown · 没有可验证的条件',required=True))
    return rows
