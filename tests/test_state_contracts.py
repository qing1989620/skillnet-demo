from __future__ import annotations

import hashlib
import pytest

from skillnet import state_contracts as sc


def predicate(kind, file='data.csv', **kwargs):
    return dict(kind=kind, file=file, **kwargs)


def artifact(tmp_path, text='id,split,score\na,train,0.2\nb,test,0.9\n'):
    path = tmp_path / 'data.csv'
    path.write_bytes(text.encode('utf-8'))
    return path


def step(idx, *, requires=(), ensures=(), deps=()):
    return dict(idx=idx, depends_on=list(deps), contract=dict(requires=list(requires), ensures=list(ensures)))


def check(tmp_path, spec, text='id,split,score\na,train,0.2\nb,test,0.9\n'):
    return sc.evaluate([spec], {'data.csv': artifact(tmp_path, text)})['checks'][0]


def test_complete_snapshot_hashes_real_bytes_and_checks_all_typed_predicates(tmp_path):
    path = artifact(tmp_path, '\ufeffid,split,score\na,train,0.2\nb,test,0.9\n')
    specs = [predicate('file_exists'), predicate('csv_schema', columns=['score', 'id', 'split'], exact=True),
             predicate('csv_nonempty'), predicate('csv_no_missing', columns=['id', 'score']),
             predicate('csv_unique', columns=['id']), predicate('csv_numeric_range', column='score', min=0, max=1),
             predicate('csv_disjoint_groups', entity='id', group='split')]
    result = sc.evaluate(specs, {'data.csv': path})
    assert result['version'] == sc.VERSION
    assert result['state'] == 'passed'
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert all(c['evidence']['sha256'] == expected and c['evidence']['bytes'] == path.stat().st_size for c in result['checks'])
    assert result['checks'][1]['evidence']['rows'] == 2


@pytest.mark.parametrize(('spec', 'text'), [
    (predicate('csv_no_missing', columns=['score']), 'id,score\na, \n'),
    (predicate('csv_unique', columns=['id']), 'id,score\na,0\na,1\n'),
    (predicate('csv_numeric_range', column='score', min=0, max=1), 'id,score\na,1.01\n'),
    (predicate('csv_numeric_range', column='score', min=0, max=1), 'id,score\na,NaN\n'),
    (predicate('csv_numeric_range', column='score', min=0, max=1), 'id,score\na,Infinity\n'),
    (predicate('csv_numeric_range', column='score', min=0, max=1), 'id,score\na,-Infinity\n'),
    (predicate('csv_numeric_range', column='score', min=0, max=1), 'id,score\na,\n'),
    (predicate('csv_disjoint_groups', entity='id', group='split'), 'id,split\na,train\na,test\n'),
    (predicate('csv_schema', columns=['id'], exact=True), 'id,score\na,0\n'),
    (predicate('csv_schema', columns=['absent']), 'id,score\na,0\n'),
])
def test_condition_violations_are_real_counterexamples(tmp_path, spec, text):
    result = check(tmp_path, spec, text)
    assert result['state'] == 'failed'
    assert len(result['evidence']['sha256']) == 64


@pytest.mark.parametrize('text', ['id,id\na,b\n', 'id,score\na\n', 'id,score\na,0,extra\n', 'id,score\n"unterminated,0\n', ',score\na,0\n', ''])
def test_malformed_csv_fails_with_physical_byte_evidence(tmp_path, text):
    result = check(tmp_path, predicate('csv_nonempty'), text)
    assert result['state'] == 'failed'
    assert result['evidence']['sha256'] == hashlib.sha256(text.encode()).hexdigest()


def test_invalid_utf8_is_failed_csv_but_file_still_exists(tmp_path):
    path = tmp_path / 'data.csv'
    path.write_bytes(b'id,score\na,\xff\n')
    result = sc.evaluate([predicate('file_exists'), predicate('csv_nonempty')], {'data.csv': path})
    assert [c['state'] for c in result['checks']] == ['passed', 'failed']


def test_empty_csv_universal_constraints_do_not_invent_nonempty_evidence(tmp_path):
    path = artifact(tmp_path, 'id,score\n')
    specs = [predicate('csv_unique', columns=['id']), predicate('csv_no_missing', columns=['score']),
             predicate('csv_numeric_range', column='score', min=0, max=1), predicate('csv_nonempty')]
    result = sc.evaluate(specs, {'data.csv': path})
    assert [c['state'] for c in result['checks']] == ['passed', 'passed', 'passed', 'failed']


@pytest.mark.parametrize('spec', [
    predicate('made_up'), predicate('csv_unique', columns=[]), predicate('csv_unique', columns=['id', 'id']),
    predicate('csv_no_missing', columns='id'), predicate('csv_schema', columns=['id'], exact=1),
    predicate('csv_numeric_range', column='score'), predicate('csv_numeric_range', column='score', min=True),
    predicate('csv_numeric_range', column='score', min=float('nan')),
    predicate('csv_numeric_range', column='score', min='Infinity'),
    predicate('csv_numeric_range', column='score', min=2, max=1),
    predicate('csv_numeric_range', column='score', min=0, maximum=1),
    predicate('csv_disjoint_groups', entity='id', group=''),
    predicate('file_exists', file='../secret'), predicate('file_exists', file='/root'),
    predicate('file_exists', file='C:/secret'), predicate('file_exists', file='folder\\secret'),
    predicate('file_exists', file='folder//secret'), predicate('file_exists', file='CON.txt'),
    predicate('file_exists', file='nul'), predicate('file_exists', file='data.csv.'),
    None, [], 'csv_nonempty',
])
def test_unsupported_or_invalid_predicates_are_unknown_without_reading(tmp_path, monkeypatch, spec):
    monkeypatch.setattr(sc, '_snapshot', lambda *_: pytest.fail('invalid predicates must not read a mapped file'))
    result = sc.evaluate([spec], {'data.csv': tmp_path / 'absent'})
    assert result['state'] == 'unknown'
    assert result['checks'][0]['state'] == 'unknown'


def test_absent_artifact_is_unknown_not_a_negative_example(tmp_path):
    result = sc.evaluate([predicate('file_exists'), predicate('csv_nonempty')], {'data.csv': tmp_path / 'absent'})
    assert result['state'] == 'unknown'
    assert all(c['state'] == 'unknown' and 'sha256' not in c['evidence'] for c in result['checks'])
    assert sc.evaluate([predicate('file_exists')], {})['state'] == 'unknown'


def test_mapped_file_is_authority_not_logical_path_resolution(tmp_path, monkeypatch):
    path = artifact(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert sc.evaluate([predicate('file_exists')], {})['state'] == 'unknown'
    assert sc.evaluate([predicate('file_exists', file='folder/data.csv')], {'folder/data.csv': path})['state'] == 'passed'


def test_snapshot_is_once_per_file_and_not_reopened_between_conditions(tmp_path, monkeypatch):
    path = artifact(tmp_path)
    original = sc._snapshot
    calls = []

    def capture(file, logical):
        calls.append(logical)
        snapshot = original(file, logical)
        path.write_text('id,score\na,999\n', encoding='utf-8')
        return snapshot

    monkeypatch.setattr(sc, '_snapshot', capture)
    specs = [predicate('csv_nonempty'), predicate('csv_numeric_range', column='score', min=0, max=1)]
    result = sc.evaluate(specs, {'data.csv': path})
    assert result['state'] == 'passed'
    assert calls == ['data.csv']
    assert len({c['evidence']['sha256'] for c in result['checks']}) == 1
    assert sc.evaluate(specs, {'data.csv': path})['state'] == 'failed'


def test_interleaved_file_groups_preserve_report_order_and_one_snapshot(tmp_path, monkeypatch):
    path = artifact(tmp_path)
    original = sc._snapshot
    calls = []

    def capture(file, logical):
        calls.append(logical)
        return original(file, logical)

    monkeypatch.setattr(sc, '_snapshot', capture)
    specs = [predicate('csv_nonempty'), predicate('file_exists', file='other.csv'),
             predicate('csv_schema', columns=['id']), predicate('made_up')]
    result = sc.evaluate(specs, {'data.csv': path, 'other.csv': path})
    assert [c['predicate'] for c in result['checks']] == specs
    assert [c['state'] for c in result['checks']] == ['passed', 'passed', 'passed', 'unknown']
    assert calls == ['data.csv', 'other.csv']


def test_existing_directory_and_symlink_are_not_admissible_evidence(tmp_path):
    assert sc.evaluate([predicate('file_exists')], {'data.csv': tmp_path})['state'] == 'unknown'
    path = artifact(tmp_path)
    link = tmp_path / 'link.csv'
    try:
        link.symlink_to(path)
    except OSError:
        pytest.skip('symlinks require privileges on this platform')
    assert sc.evaluate([predicate('file_exists')], {'data.csv': link})['state'] == 'unknown'


def test_bounds_fail_closed_instead_of_hashing_partial_artifact(tmp_path, monkeypatch):
    path = artifact(tmp_path)
    monkeypatch.setattr(sc, 'MAX_BYTES', 8)
    result = sc.evaluate([predicate('file_exists')], {'data.csv': path})
    assert result['state'] == 'unknown'
    assert 'sha256' not in result['checks'][0]['evidence']


def test_row_and_column_limits_are_unknown_with_complete_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, 'MAX_ROWS', 1)
    result = check(tmp_path, predicate('csv_nonempty'))
    assert result['state'] == 'unknown'
    assert len(result['evidence']['sha256']) == 64
    monkeypatch.setattr(sc, 'MAX_COLUMNS', 2)
    assert check(tmp_path, predicate('csv_nonempty'))['state'] == 'unknown'


def test_long_finite_numbers_are_not_rejected_by_a_short_text_heuristic(tmp_path):
    text = 'id,score\na,0.' + '0' * 200 + '1\n'
    assert check(tmp_path, predicate('csv_numeric_range', column='score', min=0, max=1), text)['state'] == 'passed'


def test_csv_field_resource_limit_is_unknown_not_a_counterexample(tmp_path):
    text = 'id,score\na,' + '0' * 200_000 + '\n'
    result = check(tmp_path, predicate('csv_nonempty'), text)
    assert result['state'] == 'unknown'
    assert len(result['evidence']['sha256']) == 64


def test_modification_between_stat_and_open_is_unknown_without_partial_hash(tmp_path, monkeypatch):
    path = artifact(tmp_path)
    original = sc.os.open

    def replace_then_open(*args, **kwargs):
        path.write_text('id,score\na,999\n', encoding='utf-8')
        return original(*args, **kwargs)

    monkeypatch.setattr(sc.os, 'open', replace_then_open)
    result = sc.evaluate([predicate('file_exists')], {'data.csv': path})
    assert result['state'] == 'unknown'
    assert 'sha256' not in result['checks'][0]['evidence']


def test_empty_and_unbounded_predicate_sets_are_unknown(tmp_path):
    assert sc.evaluate([], {})['state'] == 'unknown'
    assert sc.evaluate([predicate('file_exists')] * 33, {})['state'] == 'unknown'
    assert sc.evaluate({}, {})['state'] == 'unknown'
    assert sc.evaluate([predicate('file_exists')], [])['state'] == 'unknown'


def test_combined_state_cannot_hide_failure_behind_unknown_or_success(tmp_path):
    result = sc.evaluate([predicate('file_exists'), predicate('unsupported'), predicate('csv_schema', columns=['missing'])],
                         {'data.csv': artifact(tmp_path)})
    assert result['state'] == 'failed'
    assert [c['state'] for c in result['checks']] == ['passed', 'unknown', 'failed']


def test_transitive_noncontiguous_dag_proves_only_declarations():
    required = predicate('csv_no_missing', columns=['id'])
    result = sc.composition([step(40, requires=[required], deps=[20]), step(20, deps=[7]),
                             step(7, ensures=[predicate('csv_no_missing', columns=['id', 'score'])])])
    assert result['state'] == 'declared_compatible'
    assert result['edges'][0]['source'] == 7
    assert result['edges'][0]['target'] == 40
    assert result['frontier'] == []
    assert 'runtime evidence' in result['boundary']


def test_nonancestor_matching_skill_does_not_satisfy_requirement():
    required = predicate('csv_nonempty')
    result = sc.composition([step(0, ensures=[required]), step(1, requires=[required])])
    assert result['state'] == 'unknown'
    assert result['edges'][0]['source'] is None
    assert result['frontier'][0]['reason'] == 'unsatisfied_declared_precondition'


@pytest.mark.parametrize(('ensure', 'required', 'expected'), [
    (predicate('csv_schema', columns=['id', 'score']), predicate('csv_schema', columns=['id']), 'declared_compatible'),
    (predicate('csv_schema', columns=['id']), predicate('csv_schema', columns=['id'], exact=True), 'unknown'),
    (predicate('csv_schema', columns=['id'], exact=True), predicate('csv_schema', columns=['score']), 'contradicted'),
    (predicate('csv_schema', columns=['id', 'score'], exact=True), predicate('csv_schema', columns=['id'], exact=True), 'contradicted'),
    (predicate('csv_schema', columns=['id', 'score']), predicate('csv_schema', columns=['id'], exact=True), 'contradicted'),
    (predicate('csv_schema', columns=['id'], exact=True), predicate('csv_no_missing', columns=['score']), 'contradicted'),
    (predicate('csv_numeric_range', column='score', min=0.2, max=0.8), predicate('csv_numeric_range', column='score', min=0, max=1), 'declared_compatible'),
    (predicate('csv_numeric_range', column='score', min=0, max=1), predicate('csv_numeric_range', column='score', min=0.2, max=0.8), 'unknown'),
    (predicate('csv_numeric_range', column='score', max=1), predicate('csv_numeric_range', column='score', min=2), 'unknown'),
    (predicate('csv_numeric_range', column='score', min=1, max=2), predicate('csv_numeric_range', column='score', min=2, max=3), 'unknown'),
    (predicate('csv_numeric_range', column='other', min=0, max=1), predicate('csv_numeric_range', column='score', min=0, max=1), 'unknown'),
    (predicate('csv_no_missing', columns=['id', 'score']), predicate('csv_no_missing', columns=['id']), 'declared_compatible'),
    (predicate('csv_no_missing', columns=['id']), predicate('csv_no_missing', columns=['id', 'score']), 'unknown'),
    (predicate('csv_unique', columns=['id', 'score']), predicate('csv_unique', columns=['id']), 'unknown'),
    (predicate('csv_disjoint_groups', entity='id', group='split'), predicate('csv_disjoint_groups', entity='id', group='split'), 'declared_compatible'),
    (predicate('csv_disjoint_groups', entity='id', group='split'), predicate('csv_disjoint_groups', entity='id', group='other'), 'unknown'),
    (predicate('csv_nonempty'), predicate('file_exists'), 'declared_compatible'),
    (predicate('file_exists'), predicate('csv_nonempty'), 'unknown'),
])
def test_conservative_predicate_implication(ensure, required, expected):
    result = sc.composition([step(0, ensures=[ensure]), step(1, deps=[0], requires=[required])])
    assert result['state'] == expected


def test_unique_subset_entails_superset_only_when_extra_columns_exist():
    unique = predicate('csv_unique', columns=['id'])
    wanted = predicate('csv_unique', columns=['id', 'score'])
    unknown = sc.composition([step(0, ensures=[unique]), step(1, deps=[0], requires=[wanted])])
    assert unknown['state'] == 'unknown'
    proven = sc.composition([step(0, ensures=[unique, predicate('csv_schema', columns=['id', 'score'])]),
                             step(1, deps=[0], requires=[wanted])])
    assert proven['state'] == 'declared_compatible'


def test_latest_producer_shadows_older_properties_of_same_file():
    required = predicate('csv_no_missing', columns=['score'])
    result = sc.composition([step(0, ensures=[required]), step(1, deps=[0], ensures=[predicate('file_exists')]),
                             step(2, deps=[1], requires=[required])])
    assert result['state'] == 'unknown'
    assert result['edges'][0]['source'] == 1


def test_parallel_producers_are_ambiguous_even_with_identical_contracts():
    required = predicate('csv_nonempty')
    result = sc.composition([step(0, ensures=[required]), step(1, ensures=[required]), step(2, deps=[0, 1], requires=[required])])
    assert result['state'] == 'unknown'
    assert result['edges'][0]['candidate_sources'] == [0, 1]
    assert result['edges'][0]['source'] is None


def test_latest_branch_producer_resolves_shared_ancestor():
    required = predicate('csv_nonempty')
    result = sc.composition([step(0, ensures=[required]), step(1, deps=[0], ensures=[required]),
                             step(2, deps=[0, 1], requires=[required])])
    assert result['state'] == 'declared_compatible'
    assert result['edges'][0]['source'] == 1


def test_unsupported_and_inconsistent_output_declarations_do_not_prove_state():
    wanted = predicate('csv_numeric_range', column='score', min=0, max=1)
    bad = predicate('csv_numeric_range', column='score', min=2, max=3)
    result = sc.composition([step(0, ensures=[wanted, bad, predicate('csv_nonempty')]), step(1, deps=[0], requires=[wanted])])
    assert result['state'] == 'unknown'
    assert 'inconsistent' in result['edges'][0]['detail']
    unsupported = sc.composition([step(0, ensures=[predicate('made_up')]), step(1, deps=[0], requires=[predicate('file_exists')])])
    assert unsupported['state'] == 'unknown'


@pytest.mark.parametrize('steps', [
    [], {}, [step(0), step(0)], [step(True)], [step(0, deps=[1])],
    [step(0, deps=[1]), step(1, deps=[0])], [step(0, deps=[0])],
    [dict(idx=0, depends_on=[False])], [dict(idx=0, contract=None)],
    [dict(idx=0, contract={'requires': None})],
])
def test_invalid_or_cyclic_plan_is_unknown(steps):
    result = sc.composition(steps)
    assert result['state'] == 'unknown'
    assert result['frontier'][0]['reason'] == 'invalid_declared_plan'


def test_no_typed_requirements_is_unknown_not_certified():
    assert sc.composition([step(0)])['state'] == 'unknown'
    unsupported = sc.composition([step(0, requires=[predicate('unsupported')])])
    assert unsupported['state'] == 'unknown'
    assert unsupported['frontier'][0]['reason'] == 'unsatisfied_declared_precondition'


def test_range_contradiction_requires_nonempty_output_declaration():
    ensure = predicate('csv_numeric_range', column='score', max=1)
    required = predicate('csv_numeric_range', column='score', min=2)
    result = sc.composition([step(0, ensures=[ensure, predicate('csv_nonempty')]), step(1, deps=[0], requires=[required])])
    assert result['state'] == 'contradicted'
    vacuous = sc.composition([step(0, ensures=[ensure, required]), step(1, deps=[0], requires=[required])])
    assert vacuous['state'] == 'declared_compatible'


@pytest.mark.parametrize(('values', 'cells', 'expected'), [
    ([0, 1], ['0', '1', '0.0', '1e0', ' 1 '], 'passed'),
    ([0, 1], ['0.5'], 'failed'),
    ([0, 1], ['NaN'], 'failed'),
    ([0, 1], ['Infinity'], 'failed'),
    ([0, 1], [''], 'failed'),
    (['train', 'test'], ['train', 'test'], 'passed'),
    (['train', 'test'], [' Train '], 'failed'),
    ([''], [''], 'passed'),
])
def test_enumerated_values_have_numeric_or_exact_text_semantics(tmp_path, values, cells, expected):
    text = 'id,label\n' + ''.join(f'{i},{cell}\n' for i, cell in enumerate(cells))
    result = check(tmp_path, predicate('csv_values_in', column='label', values=values), text)
    assert result['state'] == expected


@pytest.mark.parametrize('values', [[], [True], [False, 1], [0.5], ['1', 1], [None], ['a'] * 65, ['a\nb']])
def test_invalid_enumeration_is_unknown(tmp_path, values):
    assert check(tmp_path, predicate('csv_values_in', column='label', values=values))['state'] == 'unknown'


def test_interval_is_not_a_binary_label_certificate(tmp_path):
    path = artifact(tmp_path, 'id,label\na,0.5\n')
    result = sc.evaluate([predicate('csv_numeric_range', column='label', min=0, max=1),
                          predicate('csv_values_in', column='label', values=[0, 1])], {'data.csv': path})
    assert [c['state'] for c in result['checks']] == ['passed', 'failed']


def test_enum_composition_proves_only_same_column_subset():
    required = predicate('csv_values_in', column='label', values=[0, 1, 2])
    valid = predicate('csv_values_in', column='label', values=['0.0', 1])
    assert sc.composition([step(0, ensures=[valid]), step(1, deps=[0], requires=[required])])['state'] == 'declared_compatible'
    assert sc.composition([step(0, ensures=[required]), step(1, deps=[0], requires=[valid])])['state'] == 'unknown'
    other = predicate('csv_values_in', column='other', values=[0, 1])
    assert sc.composition([step(0, ensures=[other]), step(1, deps=[0], requires=[required])])['state'] == 'unknown'
