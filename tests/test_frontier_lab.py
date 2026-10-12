"""Revalidate committed experiment bytes without executing its experiment runner.

Expected success is recomputed from source CSV and actual inline artifacts using
the independent oracle. Stored scores, success labels, and oracle verdicts are
compared only after deriving that expectation. Archived engineering iterations
remain repeated measurements of the same tasks, never independent extra samples.
"""
import copy
import csv
import gzip
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import random

import pytest

from skillnet import frontier_oracle

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs' / 'evidence'


def canonical(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def raw_sha(value):
    return hashlib.sha256(value).hexdigest()


def assert_digest(report):
    body = dict(report)
    claimed = body.pop('report_sha256')
    assert claimed == canonical(body)


@pytest.fixture(scope='module')
def evidence():
    report = json.loads((EVIDENCE / 'frontier-lab.json').read_text(encoding='utf-8'))
    frozen = json.loads((EVIDENCE / 'frontier-protocol.json').read_text(encoding='utf-8'))
    return report, frozen


def all_reports(report):
    for record in report['records']:
        yield ('strategy', record['arm'], record['task_id']), record['report']
    for index, subset in enumerate(report['basis_records']):
        for record in subset['records']:
            yield ('basis', index, record['task_id']), record['report']
    for scenario_id, item in report['scenarios'].items():
        yield ('scenario', scenario_id), item


def _check_observation_hashes(observation, data, metrics):
    expected = {'data.csv': data, 'metrics.csv': metrics}
    for check in observation['checks']['checks']:
        artifact = check.get('evidence', {})
        if 'sha256' not in artifact:
            continue
        raw = expected[artifact['file']]
        assert raw is not None
        assert artifact['sha256'] == raw_sha(raw)
        assert artifact['bytes'] == len(raw)


def _reconstruct(report, source_bytes, code_sha):
    data, metrics = source_bytes, None
    assert report['input_sha256'] == raw_sha(source_bytes)
    _check_observation_hashes(report['initial'], data, metrics)
    assert report['summary']['code_calls'] == len(report['trace'])
    for row in report['trace']:
        execution = row['execution']
        assert execution['status'] in ('completed', 'failed')
        assert type(execution['returncode']) is int
        assert execution['input_sha256'] == raw_sha(data)
        assert execution['code_sha256'] == code_sha[row['operator_id']]
        assert execution['operator_id'] == row['operator_id']
        assert row['evidence_integrity'] is True
        _check_observation_hashes(row['before'], data, metrics)
        actual = {}
        for key, artifact in execution['artifacts'].items():
            assert artifact['text_truncated'] is False
            raw = artifact['text'].encode('utf-8')
            assert artifact['sha256'] == raw_sha(raw) == execution[key + '_sha256']
            assert artifact['bytes'] == len(raw)
            actual[key] = raw
        if execution['status'] == 'completed':
            if row['operator_id'].startswith('metrics_'):
                metrics = actual['metrics']
            else:
                data = actual['output']
        _check_observation_hashes(row['after'], data, metrics)
    _check_observation_hashes(report['final'], data, metrics)
    return data, metrics


@pytest.fixture(scope='module')
def revalidated(evidence, tmp_path_factory):
    """Only file reconstruction and oracle arithmetic; no subprocess calls."""
    report, _ = evidence
    source_by_task = {item['id']: item['input_csv'].encode('utf-8') for item in report['protocol']['tasks']}
    code_sha = {identity: raw_sha(text.encode('utf-8')) for identity, text in report['executed_sources'].items()}
    scenario_task = {'missing-provider': 'development-2', 'restored-provider': 'development-2',
                     'threshold-counterexample': 'development-0', 'unmodeled-condition': 'no_test'}
    workspace = tmp_path_factory.mktemp('frontier-evidence-reference-only')
    verdicts = {}
    for index, (key, item) in enumerate(all_reports(report)):
        task = scenario_task[key[1]] if key[0] == 'scenario' else key[2]
        raw_source = source_by_task[task]
        final_data, metric_bytes = _reconstruct(item, raw_source, code_sha)
        folder = workspace / str(index)
        folder.mkdir()
        source_path, data_path = folder / 'source.csv', folder / 'data.csv'
        source_path.write_bytes(raw_source)
        data_path.write_bytes(final_data)
        metric_path = None
        if metric_bytes is not None:
            metric_path = folder / 'metrics.csv'
            metric_path.write_bytes(metric_bytes)
        independent = frontier_oracle.evaluate(source_path, data_path, metric_path)
        # Do not take stored oracle/status as the answer above.
        assert independent['state'] == item['oracle']['state'], key
        passed = independent['state'] == 'passed'
        assert (item['status'] == 'observed_success') == passed, key
        assert item['summary']['independently_verified'] == passed
        assert item['summary']['input_unchanged'] is True
        assert item['evidence_integrity'] is True
        assert item['reward_applied'] is False and item['formal_library_changed'] is False
        verdicts[key] = {'passed': passed, 'state': independent['state'],
                         'metrics_produced': metric_bytes is not None}
    for item in report['probe_records']:
        raw_source, raw_metric = item['input_csv'].encode('utf-8'), item['metric_csv'].encode('utf-8')
        execution = item['execution']
        assert execution['status'] == 'completed' and execution['returncode'] == 0
        assert execution['input_sha256'] == raw_sha(raw_source)
        assert execution['metrics_sha256'] == raw_sha(raw_metric)
        assert execution['code_sha256'] == code_sha['metrics_strict_bug']
        folder = workspace / f"probe-{item['trial']}-{item['call']}"
        folder.mkdir()
        source_path, metric_path = folder / 'source.csv', folder / 'metrics.csv'
        source_path.write_bytes(raw_source)
        metric_path.write_bytes(raw_metric)
        independent = frontier_oracle.evaluate(source_path, source_path, metric_path)
        assert independent['state'] == item['oracle']['state']
        values = dict(list(csv.reader(io.StringIO(item['metric_csv'], newline='')))[1:])
        observed = 'positive' if int(values['tp']) + int(values['fp']) else 'negative'
        assert observed == item['observation']
        predictions = {hypothesis: values[item['probe']]
                       for hypothesis, values in report['protocol']['hypotheses'].items()}
        survivors = [hypothesis for hypothesis, prediction in predictions.items()
                     if prediction is None or prediction == observed]
        assert item['update']['survivors'] == survivors
        assert item['update']['universal_correctness_proven'] is False
        verdicts['probe', item['trial'], item['call']] = {'state': independent['state']}
    return verdicts


def test_report_protocol_and_every_compact_report_canonical_digest(evidence):
    report, frozen = evidence
    assert_digest(report)
    assert frozen['protocol'] == report['protocol']
    assert frozen['protocol_sha256'] == report['protocol_sha256'] == canonical(report['protocol'])
    for _, item in all_reports(report):
        assert_digest(item)


def test_frozen_source_hashes_are_current_lf_bytes_and_executed_versions(evidence):
    report, _ = evidence
    paths = report['protocol']['source_sha256']
    assert len(paths) == 6
    for relative, digest in paths.items():
        path = ROOT / relative
        assert path.resolve().is_relative_to(ROOT.resolve())
        raw = path.read_bytes()
        assert b'\r\n' not in raw  # Git attributes preserve these LF experiment sources.
        assert raw_sha(raw) == digest, relative
    registry = {item['id']: item for item in report['protocol']['registry']}
    assert set(report['executed_sources']) == set(registry)
    for identity, text in report['executed_sources'].items():
        assert raw_sha(text.encode('utf-8')) == registry[identity]['metadata']['code_sha256']


def test_protocol_precedes_all_timestamped_execution_records(evidence):
    report, _ = evidence
    assert report['protocol']['created_at_ns'] < report['preregistered_at_ns'] < report['finished_at_ns']
    records = report['records'] + report['probe_records'] + [
        row for subset in report['basis_records'] for row in subset['records']]
    assert len(records) == 69 + 46 + 256
    assert all(report['preregistered_at_ns'] < row['started_at_ns'] < report['finished_at_ns'] for row in records)


def test_all_391_recorded_calls_reconstructed_independently(evidence, revalidated):
    report, _ = evidence
    actual_calls = sum(len(item['trace']) for _, item in all_reports(report)) + len(report['probe_records'])
    assert actual_calls == report['summary']['physical_code_calls'] == 391
    assert len(revalidated) == 69 + 256 + 4 + 46
    assert report['active_probe']['physical_code_calls'] == len(report['probe_records']) == 46


def test_task_matrix_and_strategy_summaries_from_independent_verdicts(evidence, revalidated):
    report, _ = evidence
    tasks = {item['id']: item for item in report['protocol']['tasks']}
    assert len(tasks) == 23
    assert sum(item['valid'] for item in tasks.values()) == 16
    assert sum(not item['valid'] for item in tasks.values()) == 7
    pairs = [(row['arm'], row['task_id']) for row in report['records']]
    assert len(pairs) == len(set(pairs)) == 69
    assert set(pairs) == set(itertools.product(('flat', 'plan_only', 'active'), tasks))
    for item in tasks.values():
        assert item['input_sha256'] == raw_sha(item['input_csv'].encode('utf-8'))
    for arm in report['protocol']['strategies']:
        rows = [row for row in report['records'] if row['arm'] == arm]
        def accepted(row):
            return revalidated['strategy', arm, row['task_id']]['passed']
        expected = {
            'verified': sum(accepted(row) for row in rows),
            'valid_verified': sum(tasks[row['task_id']]['valid'] and accepted(row) for row in rows),
            'invalid_verified': sum(not tasks[row['task_id']]['valid'] and accepted(row) for row in rows),
            'code_calls': sum(len(row['report']['trace']) for row in rows),
            'false_accepts': sum(row['report']['status'] == 'observed_success' and not accepted(row) for row in rows),
            'unverified_metric_outputs': sum(
                revalidated['strategy', arm, row['task_id']]['metrics_produced'] and not accepted(row) for row in rows),
            'development_verified': sum(row['split'] == 'development' and accepted(row) for row in rows),
            'heldout_verified': sum(row['split'] == 'heldout_input_variants' and accepted(row) for row in rows),
        }
        assert expected == report['summary']['strategies'][arm]
    assert report['summary']['strategies']['active']['valid_verified'] == 16
    assert report['summary']['strategies']['active']['invalid_verified'] == 0
    assert report['summary']['strategies']['plan_only']['valid_verified'] == 2


def test_all_32_subsets_and_8_tasks_minimum_is_rederived(evidence, revalidated):
    report, _ = evidence
    ids = [item['id'] for item in report['protocol']['registry']]
    development = set(report['protocol']['basis_tasks'])
    assert len(ids) == 5 and len(development) == 8
    subsets = report['basis_records']
    assert len(subsets) == 32
    assert {frozenset(row['operators']) for row in subsets} == {
        frozenset(ids[index] for index in range(5) if bits & (1 << index)) for bits in range(32)}
    measured = []
    for index, subset in enumerate(subsets):
        task_ids = [row['task_id'] for row in subset['records']]
        assert len(task_ids) == len(set(task_ids)) == 8
        assert set(task_ids) == development
        assert subset['operators'] == [ids[bit] for bit in range(5) if index & (1 << bit)]
        verified = [row['task_id'] for row in subset['records']
                    if revalidated['basis', index, row['task_id']]['passed']]
        assert verified == subset['verified_tasks']
        measured.append((subset['operators'], len(verified)))
    maximum = max(coverage for _, coverage in measured)
    minimum = min(len(operators) for operators, coverage in measured if coverage == maximum)
    minimum_subsets = [operators for operators, coverage in measured if coverage == maximum and len(operators) == minimum]
    assert maximum == report['basis']['measured_coverage'] == 8
    assert minimum == report['basis']['minimum_size'] == 4
    assert minimum_subsets == report['basis']['minimum_subsets']
    assert minimum_subsets == [['deduplicate', 'exclude_cross_split', 'drop_missing_score', 'metrics_decimal']]


def test_probe_partition_scores_orders_seeds_and_counterexample_calls(evidence, revalidated):
    report, _ = evidence
    protocol, measured = report['protocol'], report['active_probe']
    predictions = protocol['hypotheses']
    calculated_scores = []
    for probe in protocol['probe_order']:
        labels = [values[probe] for values in predictions.values()]
        counts = {label: labels.count(label) for label in set(labels)}
        entropy = -sum((count / len(labels)) * math.log2(count / len(labels)) for count in counts.values())
        calculated_scores.append((probe, entropy))
    calculated_scores.sort(key=lambda item: (-item[1], protocol['probe_order'].index(item[0])))
    assert [(row['probe'], row['score']) for row in measured['scores']] == calculated_scores
    assert measured['selected_probe'] == calculated_scores[0][0] == 'threshold'
    assert protocol['random_seeds'] == list(range(20))
    random_results = measured['first_counterexample_calls']['random']
    assert [item['seed'] for item in random_results] == list(range(20))
    orders = {'fixed': protocol['probe_order'], 'active': [item[0] for item in calculated_scores]}
    for item in random_results:
        order = list(protocol['probe_order'])
        random.Random(item['seed']).shuffle(order)
        assert item['order'] == order
        orders[f"random-{item['seed']}"] = order
    assert {row['trial'] for row in report['probe_records']} == set(orders)
    counts = {}
    for trial, order in orders.items():
        records = [row for row in report['probe_records'] if row['trial'] == trial]
        assert [row['call'] for row in records] == list(range(1, len(records) + 1))
        assert [row['probe'] for row in records] == order[:len(records)]
        verdicts = [revalidated['probe', trial, row['call']]['state'] for row in records]
        assert verdicts[-1] == 'failed' and all(value == 'passed' for value in verdicts[:-1])
        counts[trial] = len(records)
    assert counts['active'] == measured['first_counterexample_calls']['active'] == 1
    assert counts['fixed'] == measured['first_counterexample_calls']['fixed'] == 3
    for item in random_results:
        assert item['calls'] == counts[f"random-{item['seed']}"]
    assert measured['random_mean'] == sum(counts[f'random-{seed}'] for seed in range(20)) / 20


def test_archived_first_iteration_proves_serialization_failure_and_final_repair(evidence):
    final, _ = evidence
    archive_path = EVIDENCE / 'frontier-initial.json.gz'
    issue = json.loads((EVIDENCE / 'frontier-serialization-issue.json').read_text(encoding='utf-8'))
    compressed = archive_path.read_bytes()
    raw = gzip.decompress(compressed)
    initial = json.loads(raw.decode('utf-8'))
    assert raw_sha(compressed) == issue['archive_sha256']
    assert raw_sha(raw) == issue['initial_raw_sha256']
    assert_digest(initial)
    assert initial['report_sha256'] == issue['initial_report_sha256']
    assert initial['protocol_sha256'] == issue['initial_protocol_sha256']
    assert initial['protocol_sha256'] != final['protocol_sha256']
    assert initial['protocol']['source_sha256']['tools/frontier_lab.py'] != final['protocol']['source_sha256']['tools/frontier_lab.py']
    for row in initial['probe_records']:
        text = row['metric_csv']
        assert '\r\n' not in text
        assert raw_sha(text.encode('utf-8')) != row['execution']['metrics_sha256']
        assert raw_sha(text.replace('\n', '\r\n').encode('utf-8')) == row['execution']['metrics_sha256']
    for row in final['probe_records']:
        assert '\r\n' in row['metric_csv']
        assert raw_sha(row['metric_csv'].encode('utf-8')) == row['execution']['metrics_sha256']
    assert initial['summary'] == issue['summary'] == final['summary']
    assert final['summary']['physical_code_calls'] == 391  # Never present the two iterations as n=782.


def test_portability_archive_keeps_prior_sources_and_same_task_counts(evidence):
    final, _ = evidence
    compressed = (EVIDENCE / 'frontier-before-portability.json.gz').read_bytes()
    issue = json.loads((EVIDENCE / 'frontier-portability-issue.json').read_text(encoding='utf-8'))
    raw = gzip.decompress(compressed)
    before = json.loads(raw)
    assert raw_sha(compressed) == issue['archive_sha256']
    assert raw_sha(raw) == issue['before_raw_sha256']
    assert_digest(before)
    assert before['report_sha256'] == issue['before_report_sha256']
    assert before['protocol_sha256'] == issue['before_protocol_sha256']
    assert before['summary'] == issue['summary'] == final['summary']
    assert before['protocol']['source_sha256']['skillnet/frontier_ops.py'] != final['protocol']['source_sha256']['skillnet/frontier_ops.py']
    for name, source in final['executed_sources'].items():
        assert source.replace('import encodings.utf_8_sig\n', '', 1) == before['executed_sources'][name]
        assert source.index('import encodings.utf_8_sig') < source.index('sys.addaudithook(audit)')
