"""Bounded, evidence-guided execution over a reviewed experimental registry.

The production document library is untouched. Plans are declarations; only an
independent reference and observed bytes can label this scoped task successful.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import frontier, frontier_ops, frontier_oracle

VERSION = 'skillnet-frontier-runtime-v1'
GOAL = ['metrics.file']
BOUNDARY = ('仅固定登记程序与公开模拟 CSV 任务；声明路径不证明真实可达。'
            '实测结果仅适用于本次输入、代码版本和独立判据；不修改正式技能、奖励或 S1 生产状态。')
CLEANERS = ['deduplicate', 'exclude_cross_split', 'drop_missing_score']


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def diagnose(facts: list[str], candidates: list[dict], registered: list[dict] | None = None) -> dict:
    """A full registry comparison distinguishes retrieval omission from model gaps."""
    registry_scope = 'fixed_experimental_registry' if registered is None else 'provided_finite_registry'
    registered = frontier_ops.registry() if registered is None else registered
    candidate = frontier.plan(facts, GOAL, candidates)
    full = frontier.plan(facts, GOAL, registered)
    if candidate.get('reason') == 'invalid_input' or full.get('reason') == 'invalid_input':
        return {'state': 'invalid_declared_model', 'candidate': candidate, 'registry': full,
                'gaps': [], 'registry_sha256': None, 'model_kind': 'conservative_declarations',
                'registry_complete': False, 'registry_scope': registry_scope,
                'real_world_unreachable_proven': False, 'boundary': BOUNDARY}
    providers = {}
    for op in registered:
        for fact in op['adds']:
            providers.setdefault(fact, []).append(op['id'])
    metric_ops = [op for op in registered if 'metrics.file' in op['adds']]
    needed = sorted(set().union(*(set(op['requires']) for op in metric_ops)) - set(facts)) if metric_ops else ['metrics.file']
    gaps = [{'fact': f, 'providers': providers.get(f, []),
             'kind': 'observed_or_provider_needed' if providers.get(f) else 'no_registered_provider'} for f in needed]
    if candidate['status'] == 'plan_found':
        state = 'reachable_declared'
    elif full['status'] == 'plan_found':
        state = 'retrieval_miss'
    elif full['status'] == 'unknown' or candidate['status'] == 'unknown':
        state = 'search_truncated'
    else:
        state = 'evidence_insufficient' if any(g['providers'] for g in gaps) else 'unreachable_declared_model'
    return {'state': state, 'candidate': candidate, 'registry': full, 'gaps': gaps,
            'registry_sha256': digest(registered), 'model_kind': 'conservative_declarations',
            'registry_complete': True, 'registry_scope': registry_scope,
            'registry_complete_scope': 'all supplied registered operators were compared; not all skills or real-world capabilities',
            'real_world_unreachable_proven': False, 'boundary': BOUNDARY}


def _observed_check(observation: dict, fact: str) -> dict:
    return next((item for item in observation.get('checks', {}).get('checks', [])
                 if item.get('fact_id') == fact), {})


def _observed_sha(observation: dict, fact: str) -> str | None:
    return _observed_check(observation, fact).get('evidence', {}).get('sha256')


def run(input_path: Path, workspace: Path, *, strategy: str = 'active',
        operator_ids: list[str] | None = None, metric_id: str = 'metrics_decimal',
        max_calls: int = 5) -> dict:
    if type(strategy) is not str or strategy not in ('flat', 'plan_only', 'active'):
        raise ValueError('unknown execution strategy')
    if type(max_calls) is not int or not 0 <= max_calls <= 8:
        raise ValueError('max_calls must be an integer in [0,8]')
    all_ops = frontier_ops.registry()
    by_id = {op['id']: op for op in all_ops}
    if metric_id not in ('metrics_decimal', 'metrics_strict_bug'):
        raise ValueError('unregistered metrics version')
    ids = operator_ids if operator_ids is not None else CLEANERS + [metric_id]
    if (type(ids) is not list or len(ids) > len(all_ops) or not all(type(i) is str for i in ids)
            or len(ids) != len(set(ids)) or any(i not in by_id for i in ids)):
        raise ValueError('invalid registry subset')
    operators = [by_id[i] for i in ids if i not in ('metrics_decimal', 'metrics_strict_bug') or i == metric_id]
    # The input is immutable; each executable copies its current input into a
    # new attempt directory and produces a new version for re-observation.
    workspace = Path(workspace)
    if frontier_ops._linked(workspace.absolute()):
        raise ValueError('linked experimental workspaces are not admissible')
    workspace.mkdir(parents=True, exist_ok=True)
    if frontier_ops._linked(workspace.absolute()):
        raise ValueError('linked experimental workspaces are not admissible')
    input_path = Path(input_path)
    source_bytes = frontier_oracle._snapshot(input_path)
    source = workspace / 'frozen-source.csv'
    if source.exists() or (workspace / 'report.json').exists():
        raise ValueError('experimental workspace must not contain a prior frozen source or report')
    with source.open('xb') as stream:
        stream.write(source_bytes)
    current, metrics = source, None
    initial = frontier_ops.observe(current)
    diagnosis = diagnose(initial['facts'], operators, operators)
    report = {'version': VERSION, 'strategy': strategy, 'status': 'blocked', 'goal': GOAL,
              'initial': initial, 'diagnosis': diagnosis, 'trace': [], 'boundary': BOUNDARY,
              'input_sha256': hashlib.sha256(source_bytes).hexdigest(),
              'registry_sha256': digest(operators), 'reward_applied': False,
              'formal_library_changed': False, 'quarantined_versions': [],
              'controller_kind': 'fixed_priority_targeted_execution_and_reobservation',
              'controller_learned': False, 'stop_reason': None,
              'evidence_integrity': True}
    tried = set()
    for turn in range(max_calls):
        observed = frontier_ops.observe(current, metrics)
        if 'metrics.file' in observed['facts']:
            report['stop_reason'] = 'metrics_artifact_observed'
            break
        facts = set(observed['facts'])
        available = [op for op in operators if set(op['requires']) <= facts]
        planned = frontier.plan(observed['facts'], GOAL, operators)
        kind = 'declared_plan'
        if strategy == 'flat':
            op = by_id[metric_id] if metric_id in ids else None
            kind = 'unconditional_retrieval'
        elif planned['status'] == 'plan_found' and planned['plan']:
            op = by_id[planned['plan'][0]]
        elif strategy == 'active':
            # A conservative cleaner deliberately invalidates nonempty/range/
            # binary facts. Re-observe rather than inventing preserved effects.
            metric = by_id[metric_id]
            missing = set(metric['requires']) - facts
            op = next((item for name in CLEANERS for item in available
                       if item['id'] == name and set(item['adds']) & missing), None)
            kind = 'targeted_execution_probe'
        else:
            op = None
        if op is None:
            report['stop_reason'] = ('planning_unknown' if planned['status'] == 'unknown'
                                     else 'no_declared_plan_or_targeted_action')
            if planned['status'] == 'unknown':
                report['status'] = 'search_unknown'
            break
        input_sha = _observed_sha(observed, 'data.file')
        if (op['id'], input_sha) in tried:
            report['stop_reason'] = 'repeated_action_without_new_input'
            break
        tried.add((op['id'], input_sha))
        execution = frontier_ops.execute(op['id'], current, workspace / f'attempt-{turn:02d}')
        if execution.get('status') == 'completed':
            if op['id'].startswith('metrics_'):
                metrics = Path(execution['metrics_path']) if execution.get('metrics_path') else None
            else:
                current = Path(execution['output_path']) if execution.get('output_path') else current
        after = frontier_ops.observe(current, metrics)
        row = {'operator_id': op['id'], 'kind': kind, 'before': observed, 'after': after,
               'execution': execution, 'oracle': None, 'planning': planned,
               'admission': {'enforced': strategy != 'flat', 'checks': [
                   {'fact': fact, 'state': _observed_check(observed, fact).get('state', 'unknown')}
                   for fact in op['requires']]},
               'effect_verification': [{'fact': fact,
                   'state': _observed_check(after, fact).get('state', 'unknown')}
                   for fact in op['adds']]}
        report['trace'].append(row)
        promised_fact = 'metrics.file' if op['id'].startswith('metrics_') else 'data.file'
        promised_sha = execution.get('metrics_sha256' if promised_fact == 'metrics.file' else 'output_sha256')
        integrity = execution.get('code_sha256') == op['metadata']['code_sha256']
        if execution.get('input_sha256') is not None or execution.get('status') == 'completed':
            integrity = integrity and execution.get('input_sha256') == input_sha
        if execution.get('status') == 'completed':
            integrity = integrity and promised_sha == _observed_sha(after, promised_fact)
        row['evidence_integrity'] = integrity
        if not integrity:
            report['evidence_integrity'] = False
            report['status'] = 'evidence_changed'
            report['stop_reason'] = 'observed_input_code_or_artifact_version_mismatch'
            break
        if execution.get('status') != 'completed':
            report['status'] = 'execution_failed'
            report['stop_reason'] = 'registered_operator_did_not_complete'
            break
        if any(item['state'] != 'passed' for item in row['effect_verification']):
            report['status'] = 'effect_unconfirmed'
            report['stop_reason'] = 'declared_add_effect_not_observed'
            break
        if metrics is not None:
            row['oracle'] = frontier_oracle.evaluate(source, current, metrics)
            # Invalid upstream data is not evidence that this implementation
            # caused the failure. Only a valid admitted input and a matching
            # cleaning result support this narrowly scoped counterexample.
            if (row['oracle']['state'] == 'failed' and set(op['requires']) <= facts
                    and {'original_cells_and_policy', 'metric_schema'} <= {
                        c['id'] for c in row['oracle']['checks'] if c['passed']}):
                report['quarantined_versions'].append({'operator_id': op['id'],
                    'code_sha256': execution.get('code_sha256'), 'reason': 'independent_counterexample',
                    'scope': 'this experimental invocation only'})
            report['stop_reason'] = 'independent_metrics_reference_evaluated'
            break
    report['final'] = frontier_ops.observe(current, metrics)
    report['oracle'] = frontier_oracle.evaluate(source, current, metrics)
    if report['oracle']['state'] == 'passed' and report['evidence_integrity']:
        report['status'] = 'observed_success'
    elif metrics is not None and report['evidence_integrity']:
        report['status'] = 'rejected_by_oracle'
    elif len(report['trace']) >= max_calls and report['status'] == 'blocked':
        report['status'] = 'budget_exhausted'
        report['stop_reason'] = 'execution_call_budget_exhausted'
    try:
        input_unchanged = frontier_oracle._snapshot(input_path) == source_bytes
    except (OSError, ValueError):
        input_unchanged = False
    if not input_unchanged:
        report['status'] = 'source_changed'
        report['stop_reason'] = 'original_input_no_longer_matches_frozen_snapshot'
    report['summary'] = {'code_calls': len(report['trace']),
        'active_probes': sum(r['kind'] == 'targeted_execution_probe' for r in report['trace']),
        'independently_verified': report['oracle']['state'] == 'passed' and report['evidence_integrity'],
        'input_unchanged': input_unchanged,
        'eligible_for_current_source': report['oracle']['state'] == 'passed'
            and report['evidence_integrity'] and input_unchanged}
    report['report_sha256'] = digest(report)
    with (workspace / 'report.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    return report


def public_report(report: dict) -> dict:
    """Inline bounded public artifacts before temporary workspaces disappear."""
    result = json.loads(json.dumps(report, allow_nan=False))
    result.pop('report_sha256', None)
    for row in result.get('trace', []):
        execution = row.get('execution', {})
        # Already-public snapshots survive another call unchanged. Replacing
        # them with an empty mapping would erase the evidence on replay.
        artifacts = execution.get('artifacts', {})
        for key in ('output_path', 'metrics_path'):
            value = execution.pop(key, None)
            if value:
                try:
                    raw = frontier_ops._read_input(Path(value))
                    sha = hashlib.sha256(raw).hexdigest()
                    expected = execution.get(key.replace('_path', '_sha256'))
                    if sha != expected:
                        raise ValueError('artifact bytes no longer match the execution snapshot SHA-256')
                    text = raw.decode('utf-8-sig')
                    artifacts[key.replace('_path', '')] = {'sha256': sha,
                        'bytes': len(raw), 'text': text[:65536], 'text_truncated': len(text) > 65536}
                except (OSError, ValueError, UnicodeError) as exc:
                    execution.setdefault('artifact_errors', []).append({'artifact': key, 'reason': str(exc)})
                    result['status'] = 'evidence_changed'
                    result['evidence_integrity'] = False
                    result['summary']['independently_verified'] = False
                    result['summary']['eligible_for_current_source'] = False
        execution.pop('workspace', None)
        execution['artifacts'] = artifacts
    result['report_sha256'] = digest(result)
    return result


def probe_scores(hypotheses: dict[str, dict[str, str | None]], candidates: list[str]) -> list[dict]:
    """Finite, uniform, deterministic hypothesis disagreement, never hidden truth."""
    import math
    if (type(hypotheses) is not dict or not 1 <= len(hypotheses) <= 32
            or not all(frontier._name(h) for h in hypotheses)
            or type(candidates) is not list or len(candidates) > 128
            or not all(frontier._name(probe) for probe in candidates)
            or len(candidates) != len(set(candidates))):
        raise ValueError('bounded nonempty hypotheses required')
    for values in hypotheses.values():
        if (type(values) is not dict or len(values) > 128
                or not all(frontier._name(probe) for probe in values)
                or not all(_prediction(value) for value in values.values())):
            raise ValueError('hypotheses must contain bounded finite outcome labels or null')
    rows = []
    for probe in candidates:
        predictions = {h: values.get(probe) for h, values in hypotheses.items()}
        counts = {}
        for prediction in predictions.values():
            counts[prediction] = counts.get(prediction, 0) + 1
        score = None if None in counts else -sum((n / len(hypotheses)) * math.log2(n / len(hypotheses)) for n in counts.values())
        rows.append({'probe': probe, 'score': score, 'predictions': predictions,
                     'score_kind': 'uniform_finite_prediction_partition_entropy'})
    order = {probe: index for index, probe in enumerate(candidates)}
    return sorted(rows, key=lambda r: (r['score'] is None, -(r['score'] or 0), order[r['probe']]))


def _prediction(value: Any) -> bool:
    return value is None or (type(value) is str and 0 < len(value) <= 128
                             and not any(ord(character) < 32 for character in value))


def update_hypotheses(predictions: dict[str, str | None], observation: str | None) -> dict:
    if (type(predictions) is not dict or not 1 <= len(predictions) <= 32
            or not all(frontier._name(h) for h in predictions)
            or not all(_prediction(value) for value in predictions.values())
            or not _prediction(observation)):
        raise ValueError('bounded hypothesis outcomes and observation required')
    if observation is None:
        return {'state': 'unknown', 'survivors': list(predictions), 'universal_correctness_proven': False}
    survivors = [h for h, pred in predictions.items() if pred is None or pred == observation]
    return {'state': 'consistent' if survivors else 'model_mismatch', 'survivors': survivors,
            'universal_correctness_proven': False}
