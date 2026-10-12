from __future__ import annotations

import csv
from decimal import Decimal
import hashlib
from pathlib import Path
import subprocess

import pytest

from skillnet import frontier_ops


COLUMNS = ['sample_id', 'subject_id', 'split', 'label', 'score']


def write_csv(path: Path, rows, columns=COLUMNS):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)
    return path


def read_csv(path):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        return list(csv.reader(stream))


def metric_values(result):
    return {name: Decimal(value) for name, value in read_csv(result['metrics_path'])[1:]}


def test_registry_is_finite_and_declarations_are_copies():
    operators = frontier_ops.registry()
    assert {operator['id'] for operator in operators} == {
        'deduplicate', 'exclude_cross_split', 'drop_missing_score',
        'metrics_decimal', 'metrics_strict_bug',
    }
    for operator in operators:
        assert set(operator) == {'id', 'requires', 'adds', 'deletes', 'cost', 'metadata'}
        assert operator['cost'] == 1
        assert len(operator['metadata']['code_sha256']) == 64
        assert operator['metadata']['certified'] is False
    metrics = next(operator for operator in operators if operator['id'] == 'metrics_decimal')
    assert set(metrics['requires']) == {name for name in frontier_ops.FACT_SPECS if name.startswith('data.')}
    bug = next(operator for operator in operators if operator['id'] == 'metrics_strict_bug')
    assert bug['metadata']['intentional_bug'] is True
    assert bug['metadata']['code_sha256'] != metrics['metadata']['code_sha256']
    operators[0]['requires'].append('invented')
    operators[0]['metadata']['label'] = 'changed'
    assert 'invented' not in frontier_ops.registry()[0]['requires']
    assert frontier_ops.registry()[0]['metadata']['label'] != 'changed'


def test_deduplicate_preserves_first_value_spelling_and_row_order(tmp_path):
    rows = [['b', 'person-b', 'test', '1', '0.90'],
            ['a', 'person-a', 'train', '0', '0.10'],
            ['b', 'another', 'test', '0', '0.20'],
            ['c', 'person-c', 'test', '1', '5E-1']]
    original = write_csv(tmp_path / 'original.csv', rows)
    before = original.read_bytes()
    result = frontier_ops.execute('deduplicate', original, tmp_path / 'runs')
    assert result['status'] == 'completed', result['stderr']
    assert result['returncode'] == 0
    assert read_csv(result['output_path']) == [COLUMNS, rows[0], rows[1], rows[3]]
    assert original.read_bytes() == before
    assert result['input_sha256'] == hashlib.sha256(before).hexdigest()
    attempt = Path(result['workspace'])
    assert (attempt / 'input.csv').read_bytes() == before
    assert result['code_sha256'] == hashlib.sha256((attempt / 'main.py').read_bytes()).hexdigest()
    assert result['output_sha256'] == hashlib.sha256(Path(result['output_path']).read_bytes()).hexdigest()
    assert result['metrics_path'] is None
    assert 'data.unique' in frontier_ops.observe(Path(result['output_path']))['facts']


def test_split_exclusion_removes_all_contaminated_subject_rows(tmp_path):
    rows = [['a', 'leaked', 'train', '0', '0.10'],
            ['b', 'safe-a', 'test', '1', '0.90'],
            ['c', 'leaked', 'test', '1', '0.80'],
            ['d', 'safe-b', 'train', '0', '0.20'],
            ['e', 'leaked', 'train', '1', '0.70']]
    original = write_csv(tmp_path / 'data.csv', rows)
    result = frontier_ops.execute('exclude_cross_split', original, tmp_path / 'runs')
    assert result['status'] == 'completed', result['stderr']
    assert read_csv(result['output_path']) == [COLUMNS, rows[1], rows[3]]
    assert 'data.disjoint' in frontier_ops.observe(Path(result['output_path']))['facts']


def test_missing_score_only_drops_blank_scores_without_reformatting(tmp_path):
    rows = [['a', 'p-a', 'test', '1', ''],
            ['b', 'p-b', 'test', '1', '0.90'],
            ['c', 'p-c', 'train', '0', '  \t'],
            ['d', 'p-d', 'test', '0', '0.10'],
            ['e', 'p-e', 'test', '1', ' 0.50 ']]
    original = write_csv(tmp_path / 'data.csv', rows)
    result = frontier_ops.execute('drop_missing_score', original, tmp_path / 'runs')
    assert result['status'] == 'completed', result['stderr']
    assert read_csv(result['output_path']) == [COLUMNS, rows[1], rows[3], rows[4]]
    assert 'data.complete' in frontier_ops.observe(Path(result['output_path']))['facts']


def test_cleaning_can_empty_data_and_does_not_claim_nonempty(tmp_path):
    original = write_csv(tmp_path / 'data.csv', [['a', 'p-a', 'test', '1', '']])
    result = frontier_ops.execute('drop_missing_score', original, tmp_path / 'runs')
    assert result['status'] == 'completed'
    observed = frontier_ops.observe(Path(result['output_path']))
    assert 'data.complete' in observed['facts']
    assert 'data.nonempty' not in observed['facts']
    operators = frontier_ops.registry()
    for operator in operators[:3]:
        assert set(operator['deletes']) == {'data.nonempty', 'data.range', 'data.binary', 'metrics.file'}


def test_metrics_holdout_and_boundary_distinguish_reviewed_bug(tmp_path):
    original = write_csv(tmp_path / 'data.csv', [
        ['train', 'p-train', 'train', '0', '0.99'],
        ['edge', 'p-edge', 'test', '1', '0.50'],
        ['negative', 'p-negative', 'test', '0', '0.10'],
        ['positive', 'p-positive', 'test', '1', '0.90'],
    ])
    before = original.read_bytes()
    correct = frontier_ops.execute('metrics_decimal', original, tmp_path / 'runs')
    bug = frontier_ops.execute('metrics_strict_bug', original, tmp_path / 'runs')
    assert correct['status'] == bug['status'] == 'completed', (correct['stderr'], bug['stderr'])
    expected = {'n': Decimal(3), 'tp': Decimal(2), 'tn': Decimal(1),
                'fp': Decimal(0), 'fn': Decimal(0), 'accuracy': Decimal(1),
                'precision': Decimal(1), 'recall': Decimal(1), 'f1': Decimal(1)}
    assert metric_values(correct) == expected
    actual_bug = metric_values(bug)
    assert actual_bug['tp'] == 1 and actual_bug['fn'] == 1
    assert actual_bug['accuracy'] < 1
    assert original.read_bytes() == before
    assert correct['output_path'] is None
    assert correct['metrics_sha256'] == hashlib.sha256(Path(correct['metrics_path']).read_bytes()).hexdigest()
    assert 'metrics.file' in frontier_ops.observe(original, Path(correct['metrics_path']))['facts']
    assert correct['certified'] is False and bug['certified'] is False


def test_nonempty_without_holdout_is_an_explicit_unmodelled_failure(tmp_path):
    original = write_csv(tmp_path / 'data.csv', [['a', 'p-a', 'train', '1', '0.90']])
    assert 'data.nonempty' in frontier_ops.observe(original)['facts']
    result = frontier_ops.execute('metrics_decimal', original, tmp_path / 'runs')
    assert result['status'] == 'failed'
    assert result['returncode'] != 0
    assert result['metrics_path'] is None
    assert 'split=test' in result['stderr']


def test_schema_matches_column_set_and_retains_original_column_order(tmp_path):
    columns = list(reversed(COLUMNS))
    row = ['0.90', '1', 'test', 'p-a', 'a']
    original = write_csv(tmp_path / 'data.csv', [row], columns=columns)
    assert 'data.schema' in frontier_ops.observe(original)['facts']
    result = frontier_ops.execute('deduplicate', original, tmp_path / 'runs')
    assert result['status'] == 'completed'
    assert read_csv(result['output_path']) == [columns, row]


@pytest.mark.parametrize('rows,columns', [
    ([['a', 'test']], ['sample_id', 'split']),
    ([['a', 'p-a', 'test', '1', '0.90', 'extra']], COLUMNS + ['extra']),
    ([['a', 'p-a', 'test', '1', '0.90']], ['sample_id', 'subject_id', 'split', 'label', 'label']),
])
def test_bad_schema_is_not_negative_effect_evidence(tmp_path, rows, columns):
    original = write_csv(tmp_path / 'data.csv', rows, columns=columns)
    observed = frontier_ops.observe(original)
    checks = {check['fact_id']: check for check in observed['checks']['checks']}
    assert checks['data.schema']['state'] == 'failed'
    assert checks['data.unique']['state'] == 'unknown'
    assert 'data.unique' not in observed['facts']
    result = frontier_ops.execute('deduplicate', original, tmp_path / 'runs')
    assert result['status'] == 'failed'
    assert result['output_path'] is None


def test_absent_input_is_unknown_observation_and_rejected_execution(tmp_path):
    missing = tmp_path / 'absent.csv'
    observation = frontier_ops.observe(missing)
    assert observation['facts'] == []
    assert {check['state'] for check in observation['checks']['checks']} == {'unknown'}
    result = frontier_ops.execute('deduplicate', missing, tmp_path / 'runs')
    assert result['status'] == 'rejected'
    assert result['workspace'] is None


@pytest.mark.parametrize('identifier', ['unknown', '../metrics_decimal', 'deduplicate; echo bad', '', None, []])
def test_unsupported_ids_cannot_select_or_inject_source(tmp_path, identifier):
    original = write_csv(tmp_path / 'data.csv', [['a', 'p-a', 'test', '1', '0.90']])
    result = frontier_ops.execute(identifier, original, tmp_path / 'runs')
    assert result['status'] == 'rejected'
    assert result['code_sha256'] is None
    assert not (tmp_path / 'runs').exists()


@pytest.mark.parametrize('timeout', [0, -1, float('inf'), float('nan'), True, '5', 31])
def test_unbounded_or_invalid_timeout_rejected(tmp_path, timeout):
    result = frontier_ops.execute('deduplicate', tmp_path / 'data.csv', tmp_path / 'runs', timeout_seconds=timeout)
    assert result['status'] == 'rejected'
    assert 'timeout_seconds' in result['stderr']


def test_real_subprocess_timeout_keeps_frozen_input_and_source(tmp_path):
    original = write_csv(tmp_path / 'data.csv', [['a', 'p-a', 'test', '1', '0.90']])
    before = original.read_bytes()
    result = frontier_ops.execute('deduplicate', original, tmp_path / 'runs', timeout_seconds=0.000001)
    assert result['status'] == 'timeout'
    assert result['returncode'] is None
    attempt = Path(result['workspace'])
    assert (attempt / 'input.csv').read_bytes() == before
    assert (attempt / 'main.py').is_file()
    assert original.read_bytes() == before


def test_timeout_stdout_bytes_are_decoded_and_status_not_completed(tmp_path, monkeypatch):
    original = write_csv(tmp_path / 'data.csv', [['a', 'p-a', 'test', '1', '0.90']])
    def timed_out(*args, **kwargs):
        assert kwargs['shell'] is False
        assert Path(kwargs['cwd']).name.startswith('deduplicate-')
        raise subprocess.TimeoutExpired(args[0], 5, output=b'partial', stderr=b'diagnostic')
    monkeypatch.setattr(frontier_ops.subprocess, 'run', timed_out)
    result = frontier_ops.execute('deduplicate', original, tmp_path / 'runs')
    assert result['status'] == 'timeout'
    assert result['stdout'] == 'partial'
    assert 'diagnostic' in result['stderr']
    assert result['output_path'] is None


def test_attempts_are_independent_and_input_with_bom_is_supported(tmp_path):
    original = write_csv(tmp_path / 'data.csv', [['a', 'p-a', 'test', '1', '0.90']])
    original.write_bytes(b'\xef\xbb\xbf' + original.read_bytes())
    first = frontier_ops.execute('deduplicate', original, tmp_path / 'runs')
    second = frontier_ops.execute('deduplicate', original, tmp_path / 'runs')
    assert first['status'] == second['status'] == 'completed'
    assert first['workspace'] != second['workspace']
    assert first['input_sha256'] == second['input_sha256']
    assert first['output_sha256'] == second['output_sha256']
    assert first['network_allowed'] is False


def test_nonfinite_score_fails_metrics_without_promised_artifact(tmp_path):
    original = write_csv(tmp_path / 'data.csv', [['a', 'p-a', 'test', '1', 'NaN']])
    result = frontier_ops.execute('metrics_decimal', original, tmp_path / 'runs')
    assert result['status'] == 'failed'
    assert result['metrics_path'] is None
    assert 'data.range' not in frontier_ops.observe(original)['facts']
