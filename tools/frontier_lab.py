"""Preregister and execute a finite capability-frontier experiment.

No LLM, external dataset or network. Results retain failures, all subset tests,
versioned code and actual outputs; the independent oracle never ranks probes.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import platform
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from skillnet import frontier, frontier_ops, frontier_oracle, frontier_runtime as runtime
from skillnet.frontier_scenarios import csv_bytes, rows_for, run_scenario

VERSION = 'skillnet-frontier-lab-v1'


def cases():
    result = []
    for split, variant in [('development', 0), ('heldout_input_variants', 3)]:
        for mask in range(8):
            result.append({'id': f'{split}-{mask}', 'split': split, 'valid': True,
                           'bytes': csv_bytes(rows_for(mask, variant))})
    base = rows_for()
    invalid = {}
    for name, column, value in [('out_of_range', 4, '1.2'), ('non_binary', 3, '2'), ('nan', 4, 'NaN')]:
        rows = [list(r) for r in base]
        rows[2][column] = value
        invalid[name] = csv_bytes(rows)
    invalid['wrong_schema'] = b'id,value\n1,2\n'
    invalid['empty'] = csv_bytes([])
    invalid['no_test'] = csv_bytes([[r[0], r[1], 'train', r[3], r[4]] for r in base])
    invalid['all_leaking'] = csv_bytes([
        ['1', 'A', 'train', '1', '.9'], ['2', 'A', 'test', '1', '.6']])
    result.extend({'id': name, 'split': 'negative_controls', 'valid': False, 'bytes': raw}
                  for name, raw in invalid.items())
    return result


def compact(report):
    value = runtime.public_report(report)
    # Full predicate details remain in the workspace; committed evidence retains
    # per-condition verdicts/SHA and actual outputs for independent reproduction.
    def observation(obs):
        return {'facts': obs['facts'], 'checks': {
            'state': obs['checks'].get('state'), 'checks': [
                {k: c[k] for k in ('fact_id', 'id', 'state', 'observed_state', 'reason', 'detail', 'evidence', 'predicate') if k in c}
                for c in obs['checks'].get('checks', [])]}}
    for key in ('initial', 'final'):
        value[key] = observation(value[key])
    for row in value['trace']:
        row['before'] = observation(row['before'])
        row['after'] = observation(row['after'])
    value.pop('report_sha256', None)
    value['report_sha256'] = runtime.digest(value)
    return value


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def run_lab(output: Path, workspace: Path):
    workspace.mkdir(parents=True, exist_ok=False)
    tasks = cases()
    registry = frontier_ops.registry()
    hypotheses = {'ge': {'ordinary_positive': 'positive', 'ordinary_negative': 'negative', 'threshold': 'positive'},
                  'gt': {'ordinary_positive': 'positive', 'ordinary_negative': 'negative', 'threshold': 'negative'}}
    probe_order = ['ordinary_positive', 'ordinary_negative', 'threshold']
    seeds = list(range(20))
    protocol = {'version': VERSION, 'created_at_ns': time.time_ns(),
        'tasks': [{k: v for k, v in t.items() if k != 'bytes'} | {
            'input_sha256': hashlib.sha256(t['bytes']).hexdigest(), 'input_csv': t['bytes'].decode()} for t in tasks],
        'strategies': ['flat', 'plan_only', 'active'], 'max_calls': 5,
        'registry': registry, 'hypotheses': hypotheses, 'probe_order': probe_order,
        'random_seeds': seeds, 'basis_tasks': [t['id'] for t in tasks if t['split'] == 'development'],
        'basis_metric_priority': ['metrics_decimal', 'metrics_strict_bug'],
        'source_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT / 'tools/frontier_lab.py', *[ROOT / 'skillnet' / (name + '.py') for name in
                ('frontier', 'frontier_ops', 'frontier_oracle', 'frontier_runtime', 'frontier_scenarios')]]},
        'claims': ['measured_valid_task_coverage', 'counterexample_detection', 'same_input_provider_restoration',
                   'minimum_subset_on_frozen_tasks_only'],
        'no_claims': ['learned_causal_model', 'universal_equivalence', 'global_minimum_basis', 'production_S1_validation'],
        'boundary': runtime.BOUNDARY}
    protocol_sha = runtime.digest(protocol)
    frozen = {'protocol': protocol, 'protocol_sha256': protocol_sha}
    _save(workspace / 'preregistered-protocol.json', frozen)
    _save(output.with_name('frontier-protocol.json'), frozen)
    preregistered = time.time_ns()
    records, summary = [], {}
    def execute_case(task, arm, ids=None, metric='metrics_decimal', folder='strategies'):
        work = workspace / folder / arm / task['id']
        work.mkdir(parents=True, exist_ok=True)
        source = work / 'input.csv'
        source.write_bytes(task['bytes'])
        started = time.time_ns()
        result = runtime.run(source, work / 'execution', strategy=arm if folder == 'strategies' else 'active',
                             operator_ids=ids, metric_id=metric)
        return {'task_id': task['id'], 'valid': task['valid'], 'split': task['split'],
                'arm': arm, 'started_at_ns': started, 'report': compact(result)}
    for arm in protocol['strategies']:
        arm_records = [execute_case(t, arm) for t in tasks]
        records.extend(arm_records)
        summary[arm] = {'verified': sum(r['report']['status'] == 'observed_success' for r in arm_records),
            'valid_verified': sum(r['valid'] and r['report']['status'] == 'observed_success' for r in arm_records),
            'invalid_verified': sum(not r['valid'] and r['report']['status'] == 'observed_success' for r in arm_records),
            'code_calls': sum(r['report']['summary']['code_calls'] for r in arm_records),
            'false_accepts': sum(r['report']['status'] == 'observed_success' and r['report']['oracle']['state'] != 'passed'
                                 for r in arm_records),
            'unverified_metric_outputs': sum(r['report']['status'] == 'rejected_by_oracle' for r in arm_records),
            'development_verified': sum(r['split'] == 'development' and r['report']['status'] == 'observed_success' for r in arm_records),
            'heldout_verified': sum(r['split'] == 'heldout_input_variants' and r['report']['status'] == 'observed_success' for r in arm_records)}
        print(f"{arm}: {summary[arm]}", flush=True)

    scenarios = {}
    for scenario in ('missing-provider', 'restored-provider', 'threshold-counterexample', 'unmodeled-condition'):
        scenarios[scenario] = run_scenario(scenario, workspace / 'scenarios' / scenario)
    # Explicitly test candidate vs FULL registry on clean input where a path is
    # decidable. Invalid initial facts are not misreported as a retrieval miss.
    clean = workspace / 'retrieval.csv'
    clean.write_bytes(csv_bytes(rows_for()))
    facts = frontier_ops.observe(clean)['facts']
    retrieval = runtime.diagnose(facts, [], [op for op in registry if op['id'] != 'metrics_strict_bug'])

    # Probe selection reads only these authored hypotheses, not the hidden code,
    # oracle, or any observations. Each ordering really starts new subprocesses.
    scores = runtime.probe_scores(hypotheses, probe_order)
    probe_rows = {'ordinary_positive': [['p', 'P', 'test', '1', '.9']],
                  'ordinary_negative': [['n', 'N', 'test', '0', '.1']],
                  'threshold': [['b', 'B', 'test', '1', '.5']]}
    probe_records = []
    def probe_trial(name, order):
        for count, probe in enumerate(order, 1):
            work = workspace / 'probes' / name / probe
            work.mkdir(parents=True, exist_ok=True)
            source = work / 'input.csv'
            source.write_bytes(csv_bytes(probe_rows[probe]))
            started = time.time_ns()
            execution = frontier_ops.execute('metrics_strict_bug', source, work / 'execution')
            metric_path = Path(execution['metrics_path']) if execution.get('metrics_path') else None
            oracle = frontier_oracle.evaluate(source, source, metric_path)
            observation = None
            if execution['status'] == 'completed':
                # Read actual program result, never its expected prediction.
                import csv
                with metric_path.open(encoding='utf-8', newline='') as stream:
                    values = dict(list(csv.reader(stream))[1:])
                observation = 'positive' if int(values['tp']) + int(values['fp']) else 'negative'
            predictions = {h: p[probe] for h, p in hypotheses.items()}
            item = {'trial': name, 'probe': probe, 'call': count, 'started_at_ns': started,
                    'input_csv': source.read_text(encoding='utf-8'), 'execution': execution,
                    'observation': observation, 'oracle': oracle,
                    'update': runtime.update_hypotheses(predictions, observation)}
            # Preserve real bytes before dropping temporary absolute paths.
            if metric_path:
                item['metric_csv'] = metric_path.read_bytes().decode('utf-8')
            for key in ('workspace', 'output_path', 'metrics_path'):
                item['execution'].pop(key, None)
            probe_records.append(item)
            if oracle['state'] == 'failed':
                return count, item
        return None, probe_records[-1]
    fixed_calls, _ = probe_trial('fixed', probe_order)
    active_calls, selected_result = probe_trial('active', [r['probe'] for r in scores])
    random_results = []
    for seed in seeds:
        order = list(probe_order)
        random.Random(seed).shuffle(order)
        count, _ = probe_trial(f'random-{seed}', order)
        random_results.append({'seed': seed, 'calls': count, 'order': order})
    active_probe = {'hypotheses': list(hypotheses), 'candidate_order': probe_order,
        'scores': scores, 'selected_probe': scores[0]['probe'],
        'first_counterexample_calls': {'fixed': fixed_calls, 'active': active_calls, 'random': random_results},
        'random_mean': sum(r['calls'] for r in random_results) / len(random_results),
        'observation': selected_result['observation'], 'update': selected_result['update'],
        'physical_code_calls': len(probe_records),
        'boundary': '仅两个预定义确定性阈值假设、三个候选输入；分歧排序没有读取隐藏实现或独立oracle，不代表开放任务的最优探针。'}
    print(f'active probes: {active_probe["first_counterexample_calls"]}', flush=True)

    # Exhaustive subset measurement, not greedy compression or text similarity.
    # All 32 subsets and all 8 frozen development tasks are ACTUALLY executed.
    basis_records = []
    ids = [op['id'] for op in registry]
    basis_tasks = [t for t in tasks if t['split'] == 'development']
    for bits in range(1 << len(ids)):
        subset = [name for i, name in enumerate(ids) if bits & (1 << i)]
        metric = 'metrics_decimal' if 'metrics_decimal' in subset else 'metrics_strict_bug'
        measured = [execute_case(t, f'subset-{bits:02d}', subset, metric, 'basis') for t in basis_tasks]
        basis_records.append({'operators': subset,
            'verified_tasks': [r['task_id'] for r in measured if r['report']['status'] == 'observed_success'],
            'records': measured})
    maximum = max(len(row['verified_tasks']) for row in basis_records)
    preserving = [row for row in basis_records if len(row['verified_tasks']) == maximum]
    minimum = min(len(row['operators']) for row in preserving)
    basis = {'scope': '8 frozen development CSV tasks / fixed controller and independent reference',
        'registry_size': len(ids), 'minimum_size': minimum,
        'minimum_subsets': [row['operators'] for row in preserving if len(row['operators']) == minimum],
        'enumerated_subsets': len(basis_records), 'measured_coverage': maximum,
        'boundary': '穷举的是该任务集、执行器和控制器下的最小登记子集；不是全部开放技能的最小能力基，也不删除正式技能。'}
    print(f'basis: {basis}', flush=True)
    experiments = [
        {'id': 'retrieval', 'label': '候选漏检与完整登记模型分开',
         'passed': retrieval['state'] == 'retrieval_miss', 'details': retrieval},
        {'id': 'coverage', 'label': '定向执行后重观测提高有限任务覆盖',
         'passed': summary['active']['valid_verified'] == 16 and summary['active']['invalid_verified'] == 0
             and summary['active']['valid_verified'] > summary['plan_only']['valid_verified'],
         'details': summary},
        {'id': 'provider', 'label': '同一输入补提供者，独立验收恢复',
         'passed': scenarios['missing-provider']['status'] != 'observed_success'
             and scenarios['restored-provider']['status'] == 'observed_success'
             and scenarios['missing-provider']['input_sha256'] == scenarios['restored-provider']['input_sha256'],
         'details': {'before': scenarios['missing-provider']['status'], 'after': scenarios['restored-provider']['status'],
                     'same_input_sha256': scenarios['restored-provider']['input_sha256']}},
        {'id': 'counterexample', 'label': '结构通过仍拒绝错误阈值版本',
         'passed': scenarios['threshold-counterexample']['status'] == 'rejected_by_oracle'
             and bool(scenarios['threshold-counterexample']['quarantined_versions']),
         'details': {'state': scenarios['threshold-counterexample']['status'], 'probe': active_probe}},
        {'id': 'unmodeled', 'label': '未建模条件保留真实失败',
         'passed': scenarios['unmodeled-condition']['diagnosis']['state'] == 'reachable_declared'
             and scenarios['unmodeled-condition']['status'] == 'execution_failed',
         'details': {'declaration': scenarios['unmodeled-condition']['diagnosis']['state'],
                     'execution': scenarios['unmodeled-condition']['status']}},
        {'id': 'finite_basis', 'label': '穷举固定任务集的最小登记子集',
         'passed': maximum == 8 and minimum == 4 and len(basis_records) == 32, 'details': basis},
    ]
    finished = time.time_ns()
    report = {'version': VERSION, 'scope': 'public synthetic CSV / frozen programs / no LLM / no production policy update',
        'protocol_sha256': protocol_sha, 'protocol': protocol,
        'environment': {'python': platform.python_version(), 'platform': platform.platform()},
        'preregistered_at_ns': preregistered, 'finished_at_ns': finished,
        'summary': {'task_count': len(tasks), 'valid_tasks': 16, 'invalid_tasks': 7, 'strategies': summary,
            'all_obligations_passed': all(e['passed'] for e in experiments),
            'physical_code_calls': sum(r['report']['summary']['code_calls'] for r in records)
                + sum(s['summary']['code_calls'] for s in scenarios.values()) + len(probe_records)
                + sum(r['report']['summary']['code_calls'] for b in basis_records for r in b['records'])},
        'experiments': experiments, 'active_probe': active_probe, 'basis': basis,
        'records': records, 'scenarios': scenarios, 'probe_records': probe_records, 'basis_records': basis_records,
        'executed_sources': dict(frontier_ops._SOURCES),
        'reward_applied': False, 'formal_library_changed': False, 'boundary': runtime.BOUNDARY}
    report['report_sha256'] = runtime.digest(report)
    _save(output, report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/evidence/frontier-lab.json')
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    result = run_lab(args.output, args.workspace)
    print(json.dumps({'summary': result['summary'], 'report_sha256': result['report_sha256']}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['summary']['all_obligations_passed'] else 1)
