"""Actual fixed-program execution, independent reference, and evidence integrity."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path

import pytest

from skillnet import frontier, frontier_ops, frontier_oracle, frontier_runtime as runtime
from skillnet import frontier_scenarios as scenarios


def source(tmp_path, mask=0, rows=None):
    path = tmp_path / 'input.csv'
    path.write_bytes(scenarios.csv_bytes(scenarios.rows_for(mask) if rows is None else rows))
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_digest(report):
    body = copy.deepcopy(report)
    reported = body.pop('report_sha256')
    assert reported == runtime.digest(body)


@pytest.fixture(scope='module')
def scenario_reports(tmp_path_factory):
    workspace = tmp_path_factory.mktemp('real-frontier-scenarios')
    return {item['id']: scenarios.run_scenario(item['id'], workspace / item['id'])
            for item in scenarios.scenarios()}


@pytest.mark.parametrize('scenario_id,status', [
    ('combined', 'observed_success'),
    ('missing-provider', 'blocked'),
    ('restored-provider', 'observed_success'),
    ('threshold-counterexample', 'rejected_by_oracle'),
    ('unmodeled-condition', 'execution_failed'),
])
def test_five_public_scenarios_actually_execute_and_keep_boundaries(scenario_reports, scenario_id, status):
    report = scenario_reports[scenario_id]
    assert report['status'] == status
    assert report['reward_applied'] is False
    assert report['formal_library_changed'] is False
    assert report['controller_learned'] is False
    assert report['controller_kind'] == 'fixed_priority_targeted_execution_and_reobservation'
    assert report['summary']['input_unchanged'] is True
    assert report['diagnosis']['real_world_unreachable_proven'] is False
    checked_digest(report)


def test_restore_provider_changes_outcome_for_exact_same_input(scenario_reports):
    before, after = scenario_reports['missing-provider'], scenario_reports['restored-provider']
    assert before['input_sha256'] == after['input_sha256']
    assert before['status'] == 'blocked' and after['status'] == 'observed_success'
    gap = next(item for item in before['diagnosis']['gaps'] if item['fact'] == 'data.disjoint')
    assert gap['kind'] == 'no_registered_provider'
    assert before['diagnosis']['registry_scope'] == 'provided_finite_registry'
    assert 'not all skills' in before['diagnosis']['registry_complete_scope']


def test_threshold_counterexample_requires_admitted_valid_upstream(scenario_reports):
    report = scenario_reports['threshold-counterexample']
    row = report['trace'][-1]
    assert all(item['state'] == 'passed' for item in row['admission']['checks'])
    assert row['oracle']['state'] == 'failed'
    assert all(item['passed'] for item in row['oracle']['checks']
               if item['id'] in ('original_cells_and_policy', 'metric_schema'))
    assert any(not item['passed'] for item in row['oracle']['checks'] if item['id'] in ('tp', 'fn'))
    assert report['quarantined_versions'] == [{
        'operator_id': 'metrics_strict_bug', 'code_sha256': row['execution']['code_sha256'],
        'reason': 'independent_counterexample', 'scope': 'this experimental invocation only'}]


def test_declared_reachability_does_not_hide_unmodeled_execution_failure(scenario_reports):
    report = scenario_reports['unmodeled-condition']
    assert report['diagnosis']['state'] == 'reachable_declared'
    assert report['status'] == 'execution_failed'
    assert 'split=test' in report['trace'][-1]['execution']['stderr']
    assert report['oracle']['state'] == 'unknown'
    assert report['quarantined_versions'] == []


def test_all_actual_artifacts_match_recorded_sha_and_observation_versions(scenario_reports):
    for report in scenario_reports.values():
        for row in report['trace']:
            execution = row['execution']
            assert row['evidence_integrity'] is True
            assert execution['code_sha256'] == next(
                item for item in frontier_ops.registry() if item['id'] == row['operator_id'])['metadata']['code_sha256']
            observed_input = runtime._observed_sha(row['before'], 'data.file')
            assert execution['input_sha256'] == observed_input
            for key, artifact in execution['artifacts'].items():
                assert artifact['text_truncated'] is False
                raw = artifact['text'].encode('utf-8')
                assert len(raw) == artifact['bytes']
                assert hashlib.sha256(raw).hexdigest() == artifact['sha256']
                assert artifact['sha256'] == execution[key + '_sha256']
                fact = 'metrics.file' if key == 'metrics' else 'data.file'
                assert artifact['sha256'] == runtime._observed_sha(row['after'], fact)


def test_public_report_is_idempotent_and_needs_no_deleted_workspace(scenario_reports, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('a public snapshot should not re-open a temporary path')
    monkeypatch.setattr(frontier_ops, '_read_input', forbidden)
    for report in scenario_reports.values():
        original = copy.deepcopy(report)
        assert runtime.public_report(report) == original
        assert runtime.public_report(runtime.public_report(report)) == original
        assert report == original


def test_runtime_does_not_modify_source_cells_or_metadata(tmp_path):
    path = source(tmp_path, 7)
    raw, before = path.read_bytes(), path.stat()
    report = runtime.run(path, tmp_path / 'run')
    after = path.stat()
    assert report['status'] == 'observed_success'
    assert [row['operator_id'] for row in report['trace']] == [
        'deduplicate', 'exclude_cross_split', 'drop_missing_score', 'metrics_decimal']
    assert path.read_bytes() == raw
    assert (before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns)
    assert report['summary']['eligible_for_current_source'] is True
    checked_digest(report)


def test_dedup_precedes_leakage_exclusion_when_duplicate_changes_group(tmp_path):
    rows = scenarios.rows_for()
    rows.append([rows[0][0], rows[0][1], 'test', '1', '0.70'])
    path = source(tmp_path, rows=rows)
    report = runtime.run(path, tmp_path / 'run')
    assert report['status'] == 'observed_success'
    assert [row['operator_id'] for row in report['trace']] == ['deduplicate', 'metrics_decimal']
    assert report['oracle']['checks'][0]['expected_rows'] == len(rows) - 1


def test_leakage_exclusion_precedes_blank_drop_and_wrong_order_is_rejected(tmp_path):
    rows = scenarios.rows_for()
    rows.append(['blank-leak', rows[0][1], 'test', '1', '  '])
    path = source(tmp_path, rows=rows)
    report = runtime.run(path, tmp_path / 'good')
    assert report['status'] == 'observed_success'
    assert [row['operator_id'] for row in report['trace']] == ['exclude_cross_split', 'metrics_decimal']
    dropped = frontier_ops.execute('drop_missing_score', path, tmp_path / 'bad-drop')
    excluded = frontier_ops.execute('exclude_cross_split', Path(dropped['output_path']), tmp_path / 'bad-exclude')
    metric = frontier_ops.execute('metrics_decimal', Path(excluded['output_path']), tmp_path / 'bad-metric')
    independent = frontier_oracle.evaluate(path, Path(excluded['output_path']), Path(metric['metrics_path']))
    assert independent['state'] == 'failed'
    assert independent['checks'][0]['id'] == 'original_cells_and_policy'
    assert independent['checks'][0]['passed'] is False


def test_invalid_upstream_does_not_assign_failure_to_metrics_version(tmp_path):
    path = source(tmp_path, 2)
    report = runtime.run(path, tmp_path / 'flat', strategy='flat', metric_id='metrics_strict_bug')
    assert report['status'] == 'rejected_by_oracle'
    assert report['trace'][-1]['admission']['enforced'] is False
    assert any(item['state'] != 'passed' for item in report['trace'][-1]['admission']['checks'])
    assert report['quarantined_versions'] == []
    assert report['oracle']['checks'][0]['passed'] is False


@pytest.mark.parametrize('calls', [0, 1, 2, 3])
def test_execution_budget_keeps_unknown_outcome_without_claiming_no_capability(tmp_path, calls):
    path = source(tmp_path, 7)
    report = runtime.run(path, tmp_path / 'run', max_calls=calls)
    assert report['status'] == 'budget_exhausted'
    assert report['summary']['code_calls'] <= calls
    assert report['oracle']['state'] == 'unknown'
    assert report['stop_reason'] == 'execution_call_budget_exhausted'
    assert report['quarantined_versions'] == []
    assert report['diagnosis']['real_world_unreachable_proven'] is False


def test_planner_unknown_does_not_become_world_unreachable(monkeypatch):
    monkeypatch.setattr(frontier, 'plan', lambda *args, **kwargs: {
        'status': 'unknown', 'reason': 'state_budget_exhausted'})
    report = runtime.diagnose([], frontier_ops.registry())
    assert report['state'] == 'search_truncated'
    assert report['real_world_unreachable_proven'] is False


def test_invalid_model_is_diagnosed_without_iterating_invalid_provider_objects():
    report = runtime.diagnose(['data.schema'], [None])
    assert report['state'] == 'invalid_declared_model'
    assert report['registry_complete'] is False
    assert report['real_world_unreachable_proven'] is False


def test_search_unknown_stop_is_separate_from_execution_budget(tmp_path, monkeypatch):
    path = source(tmp_path)
    monkeypatch.setattr(frontier, 'plan', lambda *args, **kwargs: {
        'status': 'unknown', 'reason': 'state_budget_exhausted'})
    report = runtime.run(path, tmp_path / 'run', strategy='plan_only')
    assert report['status'] == 'search_unknown'
    assert report['stop_reason'] == 'planning_unknown'
    assert report['summary']['code_calls'] == 0
    assert report['quarantined_versions'] == []


def test_repeated_action_without_input_change_stops_boundedly(tmp_path, monkeypatch):
    path = source(tmp_path, 1)
    original = frontier_ops.execute
    def no_effect(identifier, current, work):
        result = original(identifier, current, work)
        if identifier == 'deduplicate':
            output = Path(result['output_path'])
            output.write_bytes(current.read_bytes())
            result['output_sha256'] = sha(output)
        return result
    monkeypatch.setattr(frontier_ops, 'execute', no_effect)
    report = runtime.run(path, tmp_path / 'run')
    assert report['status'] == 'effect_unconfirmed'
    assert report['stop_reason'] == 'declared_add_effect_not_observed'
    assert report['summary']['code_calls'] == 1
    assert report['quarantined_versions'] == []


def test_reused_workspace_cannot_overwrite_frozen_source_or_report(tmp_path):
    path = source(tmp_path)
    workspace = tmp_path / 'run'
    runtime.run(path, workspace)
    before = {item.name: item.read_bytes() for item in (workspace / 'frozen-source.csv', workspace / 'report.json')}
    with pytest.raises(ValueError, match='prior frozen source or report'):
        runtime.run(path, workspace)
    assert {item.name: item.read_bytes() for item in (workspace / 'frozen-source.csv', workspace / 'report.json')} == before


def test_original_path_cannot_be_overwritten_by_freeze_destination(tmp_path):
    path = tmp_path / 'frozen-source.csv'
    path.write_bytes(scenarios.csv_bytes(scenarios.rows_for()))
    raw, metadata = path.read_bytes(), path.stat()
    with pytest.raises(ValueError, match='prior frozen source'):
        runtime.run(path, tmp_path)
    assert path.read_bytes() == raw and path.stat().st_mtime_ns == metadata.st_mtime_ns


def test_source_change_during_execution_invalidates_current_source_eligibility(tmp_path, monkeypatch):
    path = source(tmp_path)
    original = frontier_ops.execute
    def mutate_origin(*args, **kwargs):
        result = original(*args, **kwargs)
        path.write_bytes(path.read_bytes() + b'\n')
        return result
    monkeypatch.setattr(frontier_ops, 'execute', mutate_origin)
    report = runtime.run(path, tmp_path / 'run')
    assert report['status'] == 'source_changed'
    assert report['summary']['input_unchanged'] is False
    assert report['summary']['eligible_for_current_source'] is False
    assert report['reward_applied'] is False


@pytest.mark.parametrize('mismatch', ['input', 'code', 'output'])
def test_observation_execution_version_mismatch_is_never_success(tmp_path, monkeypatch, mismatch):
    path = source(tmp_path)
    original = frontier_ops.execute
    def altered(identifier, current, work):
        if mismatch == 'input':
            current.write_bytes(current.read_bytes() + b'\n')
        result = original(identifier, current, work)
        if mismatch == 'code':
            result['code_sha256'] = '0' * 64
        elif mismatch == 'output':
            artifact = Path(result['metrics_path'])
            artifact.write_bytes(artifact.read_bytes() + b'\n')
        return result
    monkeypatch.setattr(frontier_ops, 'execute', altered)
    report = runtime.run(path, tmp_path / 'run')
    assert report['status'] == 'evidence_changed'
    assert report['evidence_integrity'] is False
    assert report['summary']['independently_verified'] is False
    assert report['quarantined_versions'] == []


def test_late_artifact_tamper_revokes_public_snapshot_success(tmp_path):
    report = runtime.run(source(tmp_path), tmp_path / 'run')
    artifact = Path(report['trace'][-1]['execution']['metrics_path'])
    artifact.write_bytes(artifact.read_bytes() + b'\n')
    public = runtime.public_report(report)
    assert report['status'] == 'observed_success'  # Original object is not mutated.
    assert public['status'] == 'evidence_changed'
    assert public['summary']['independently_verified'] is False
    assert public['summary']['eligible_for_current_source'] is False
    assert public['trace'][-1]['execution']['artifact_errors']
    assert runtime.public_report(public) == public
    checked_digest(public)


def test_public_snapshot_does_not_mutate_private_report(tmp_path):
    report = runtime.run(source(tmp_path), tmp_path / 'run')
    original = copy.deepcopy(report)
    public = runtime.public_report(report)
    assert report == original
    assert 'metrics_path' not in public['trace'][-1]['execution']
    assert 'workspace' not in public['trace'][-1]['execution']
    assert public['trace'][-1]['execution']['artifacts']['metrics']['text']


def test_oracle_matches_schema_column_set_and_numeric_binary_contract(tmp_path):
    rows = scenarios.rows_for()
    for row in rows:
        row[3] += '.00'
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(list(reversed(scenarios.HEADER)))
    writer.writerows([list(reversed(row)) for row in rows])
    path = tmp_path / 'input.csv'
    path.write_bytes(stream.getvalue().encode())
    report = runtime.run(path, tmp_path / 'run')
    assert report['status'] == 'observed_success'
    assert report['oracle']['state'] == 'passed'


@pytest.mark.parametrize('value', ['invalid', 'NaN', 'Infinity', '1e999999999', '-1', '9' * 129])
def test_oracle_rejects_malformed_numeric_metrics_without_crashing(tmp_path, value):
    path = source(tmp_path)
    execution = frontier_ops.execute('metrics_decimal', path, tmp_path / 'metric')
    metrics = Path(execution['metrics_path'])
    metrics.write_text(metrics.read_text().replace('accuracy,0.75', 'accuracy,' + value), encoding='utf-8')
    # The fixture currently has 3/4 correct test rows; assert the mutation hit.
    assert 'accuracy,' + value in metrics.read_text()
    report = frontier_oracle.evaluate(path, path, metrics)
    assert report['state'] == 'failed'
    assert next(item for item in report['checks'] if item['id'] == 'accuracy')['passed'] is False


def test_oracle_unknown_on_invalid_original_source_is_not_negative_skill_evidence(tmp_path):
    rows = scenarios.rows_for()
    rows[0][4] = 'NaN'
    path = source(tmp_path, rows=rows)
    report = frontier_oracle.evaluate(path, path, None)
    assert report['state'] == 'unknown'
    assert 'out-of-domain' in report['reason']


@pytest.mark.parametrize('kwargs', [
    {'max_calls': True}, {'max_calls': -1}, {'max_calls': 9}, {'max_calls': 1.2},
    {'strategy': 'learned'}, {'strategy': {}},
    {'operator_ids': 'metrics_decimal'}, {'operator_ids': [{}]},
    {'operator_ids': ['metrics_decimal', 'metrics_decimal']}, {'operator_ids': ['unregistered']},
    {'metric_id': 'unregistered'},
])
def test_runtime_rejects_invalid_registry_or_resource_options(tmp_path, kwargs):
    with pytest.raises(ValueError):
        runtime.run(source(tmp_path), tmp_path / 'run', **kwargs)


def test_runtime_and_reference_reject_oversized_source_before_execution(tmp_path):
    path = tmp_path / 'large.csv'
    path.write_bytes(b'x' * (1024 * 1024 + 1))
    with pytest.raises(ValueError, match='bounded regular file'):
        runtime.run(path, tmp_path / 'run')
    assert frontier_oracle.evaluate(path, path, None)['state'] == 'unknown'
    assert not list((tmp_path / 'run').glob('attempt-*'))


def test_disagreement_probe_selection_uses_predictions_without_oracle():
    hypotheses = {'ge': {'ordinary': 'positive', 'threshold': 'positive', 'unknown': None},
                  'gt': {'ordinary': 'positive', 'threshold': 'negative', 'unknown': 'positive'}}
    ranked = runtime.probe_scores(hypotheses, ['ordinary', 'unknown', 'threshold'])
    assert [row['probe'] for row in ranked] == ['threshold', 'ordinary', 'unknown']
    assert [row['score'] for row in ranked] == [1.0, 0.0, None]
    assert ranked[0]['score_kind'] == 'uniform_finite_prediction_partition_entropy'
    update = runtime.update_hypotheses(ranked[0]['predictions'], 'positive')
    assert update['survivors'] == ['ge']
    assert update['universal_correctness_proven'] is False


def test_unknown_probe_evidence_does_not_eliminate_hypotheses():
    predictions = {'ge': 'positive', 'gt': 'negative', 'unmodeled': None}
    unknown = runtime.update_hypotheses(predictions, None)
    assert unknown['state'] == 'unknown'
    assert unknown['survivors'] == list(predictions)
    assert unknown['universal_correctness_proven'] is False
    partial = runtime.update_hypotheses(predictions, 'positive')
    assert partial['survivors'] == ['ge', 'unmodeled']
    mismatch = runtime.update_hypotheses({'ge': 'positive'}, 'negative')
    assert mismatch['state'] == 'model_mismatch'


@pytest.mark.parametrize('hypotheses,candidates', [
    ([], []), ({}, []), ({'h': {}}, 'probe'), ({'h': {}}, ['same', 'same']),
    ({'h': {'p': float('nan')}}, ['p']), ({'h': {'p': True}}, ['p']),
    ({'h': {'p': ''}}, ['p']), ({'h': []}, ['p']),
    ({'h': {'p': 'x' * 129}}, ['p']), ({'h': {}}, ['p'] * 129),
])
def test_probe_prediction_inputs_are_bounded_and_strict(hypotheses, candidates):
    with pytest.raises(ValueError):
        runtime.probe_scores(hypotheses, candidates)


@pytest.mark.parametrize('predictions,observation', [
    ([], 'positive'), ({}, 'positive'), ({'h': True}, 'positive'),
    ({'h': 'positive'}, True), ({'h': 'positive'}, ''),
    ({'h': 'positive'}, 'x' * 129),
])
def test_hypothesis_update_rejects_invalid_outcomes(predictions, observation):
    with pytest.raises(ValueError):
        runtime.update_hypotheses(predictions, observation)
