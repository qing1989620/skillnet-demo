from __future__ import annotations

import copy
import hashlib

import pytest

from skillnet import (capabilities, evidence, frontier_bridge, frontier_ops,
                      frontier_runtime, llm, pipeline, research, runtime, state_policy)
from skillnet.bandit import SharedLinUCB
from skillnet.catalog import SkillLibrary
from skillnet.schema import Skill


def make_run():
    return runtime.Run('frontier-bridge-public', research.research_scenario()['task'], 'public-research',
                       started_at_ms=100, ended_at_ms=101)


def bind(run, path):
    run.staged['state_policy'] = state_policy.bind(run, path)
    return run


def forbidden(*args, **kwargs):
    pytest.fail('read-only frontier projection executed code or called a model')


def test_exact_host_input_projects_observed_gaps_without_execution_or_mutation(tmp_path, monkeypatch):
    run = bind(make_run(), tmp_path)
    before = copy.deepcopy(run.to_dict())
    input_path = tmp_path / 'artifacts' / frontier_bridge.INPUT_NAME
    original = input_path.read_bytes()
    monkeypatch.setattr(frontier_ops, 'execute', forbidden)
    monkeypatch.setattr(llm, 'chat', forbidden)
    report = frontier_bridge.project(run, tmp_path)
    assert run.to_dict() == before
    assert input_path.read_bytes() == original
    assert report['read_only'] is True and report['experimental_execution_applied'] is False
    assert report['reward_applied'] is False and report['formal_library_changed'] is False
    assert report['scope'] == frontier_bridge.SCOPE
    assert report['input_sha256'] == run.artifacts[0].sha256 == hashlib.sha256(original).hexdigest()
    assert set(report['observation']['facts']) == {'data.file', 'data.schema', 'data.nonempty', 'data.binary'}
    assert {item['fact'] for item in report['diagnosis']['gaps']} == {
        'data.unique', 'data.disjoint', 'data.complete', 'data.range'}
    assert report['diagnosis']['real_world_unreachable_proven'] is False
    assert {operator['id'] for operator in report['registry']} == set(frontier_bridge.OPERATOR_IDS)
    assert 'metrics_strict_bug' not in {operator['id'] for operator in report['registry']}
    assert report['report_sha256'] == frontier_runtime.digest({key: value for key, value in report.items() if key != 'report_sha256'})


@pytest.mark.parametrize('damage', [
    'other-task', 'unknown-host', 'task-sha', 'file-bytes', 'registered-sha',
    'registered-bytes', 'logical-name', 'kind', 'source-run', 'producer',
    'duplicate-registration', 'no-registration', 'unregistered-host-bytes',
])
def test_incorrect_scope_registration_or_snapshot_remains_unmeasured(tmp_path, damage):
    run = bind(make_run(), tmp_path)
    path = tmp_path / 'artifacts' / frontier_bridge.INPUT_NAME
    if damage == 'other-task':
        run.task = '仅帮我统计这份 CSV'
    elif damage == 'unknown-host':
        run.staged['state_policy']['host_reference'] = 'some-other-reference'
    elif damage == 'task-sha':
        run.staged['state_policy']['task_sha256'] = '0' * 64
    elif damage == 'file-bytes':
        path.write_bytes(path.read_bytes().replace(b'0.90', b'0.91'))
    elif damage == 'registered-sha':
        run.artifacts[0].sha256 = '0' * 64
    elif damage == 'registered-bytes':
        run.artifacts[0].bytes += 1
    elif damage == 'logical-name':
        run.artifacts[0].logical_name = 'some-other.csv'
    elif damage == 'kind':
        run.artifacts[0].kind = '跨轮输入'
    elif damage == 'source-run':
        run.artifacts[0].source_run_id = 'another-run'
    elif damage == 'producer':
        run.artifacts[0].from_step = 0
    elif damage == 'duplicate-registration':
        run.artifacts.append(copy.deepcopy(run.artifacts[0]))
    elif damage == 'no-registration':
        run.artifacts = []
    elif damage == 'unregistered-host-bytes':
        raw = path.read_bytes().replace(b'0.90', b'0.91')
        path.write_bytes(raw)
        run.artifacts[0].sha256 = hashlib.sha256(raw).hexdigest()
    before = copy.deepcopy(run.to_dict())
    assert frontier_bridge.project(run, tmp_path) is None
    assert run.to_dict() == before


def test_pipeline_emits_scoped_frontier_without_changing_contracts_or_policy(tmp_path, monkeypatch):
    run = make_run()
    library = SkillLibrary([Skill('bridge-test', 'CSV analysis', 'data')])
    bandit = SharedLinUCB(library)
    policy_before = copy.deepcopy(bandit.state_dict())
    library_before = [copy.deepcopy(skill.to_dict()) for skill in library]
    observed = []
    def record_pipeline(current, workspace, lib, budget):
        observed.append(copy.deepcopy(current.steps[0].contract))
        current.steps[0].status = runtime.STEP_DONE
    monkeypatch.setattr(pipeline, '_run_steps_graph', record_pipeline)
    monkeypatch.setattr(frontier_ops, 'execute', forbidden)
    monkeypatch.setattr(llm, 'chat', forbidden)
    plan = {'steps': [{'action': '清洗公开 CSV', 'output_files': ['clean_predictions.csv']}]}
    pipeline.execute_run(run, library, tmp_path, plan, max_steps=1, step_filter=lambda *_: True)
    assert run.staged['capability_frontier']['read_only'] is True
    events = [event for event in run.events if event.type == 'capability.frontier']
    assert len(events) == 1 and events[0].data['frontier'] == run.staged['capability_frontier']
    assert run.events.index(events[0]) < next(i for i, event in enumerate(run.events) if event.type == 'run.executing')
    frozen = run.staged['state_policy']['frozen']['0']['declaration']
    assert state_policy.declaration(run.steps[0]) == frozen
    assert observed[0] == run.steps[0].contract
    assert bandit.state_dict() == policy_before
    assert [skill.to_dict() for skill in library] == library_before
    assert run.llm_calls == 0 and not run.evolution


def test_other_production_task_has_no_frontier_field_or_event(tmp_path, monkeypatch):
    run = runtime.Run('ordinary-run', '计算这个数据的均值', 'ordinary')
    monkeypatch.setattr(pipeline, '_run_steps_graph', lambda *args: None)
    monkeypatch.setattr(frontier_ops, 'execute', forbidden)
    pipeline.execute_run(run, None, tmp_path, {'steps': [{'action': '计算数据'}]}, max_steps=1)
    assert 'capability_frontier' not in run.staged
    assert not any(event.type == 'capability.frontier' for event in run.events)
    capsule = evidence.capsule(run, tmp_path)
    assert 'capability_frontier' not in capsule
    assert 'capability_frontier' not in capabilities.transitions(capsule)


def test_capsule_and_capabilities_bind_optional_projection_to_current_input_integrity(tmp_path):
    run = bind(make_run(), tmp_path)
    run.staged['capability_frontier'] = frontier_bridge.project(run, tmp_path)
    before = copy.deepcopy(run.to_dict())
    capsule = evidence.capsule(run, tmp_path)
    frontier = capsule['capability_frontier']
    assert frontier['input_integrity'] == frontier['record_integrity'] == 'passed'
    assert frontier['recorded_report_sha256'] == run.staged['capability_frontier']['report_sha256']
    assert frontier['report_sha256'] == frontier_runtime.digest({key: value for key, value in frontier.items() if key != 'report_sha256'})
    report = capabilities.transitions(capsule)
    assert report['capability_frontier'] == frontier
    assert run.to_dict() == before
    path = tmp_path / 'artifacts' / frontier_bridge.INPUT_NAME
    path.write_bytes(path.read_bytes().replace(b'0.90', b'0.91'))
    damaged = evidence.capsule(run, tmp_path)
    assert damaged['capability_frontier']['input_integrity'] == 'failed'
    assert damaged['capability_frontier']['observation'] == frontier['observation']
    assert 'recorded_before_execution' in damaged['capability_frontier']['observation_time']


def test_modified_recorded_projection_is_not_currently_intact(tmp_path):
    run = bind(make_run(), tmp_path)
    run.staged['capability_frontier'] = frontier_bridge.project(run, tmp_path)
    run.staged['capability_frontier']['diagnosis']['state'] = 'invented-causal-proof'
    capsule = evidence.capsule(run, tmp_path)
    assert capsule['capability_frontier']['record_integrity'] == 'failed'
    assert capsule['capability_frontier']['input_integrity'] == 'failed'


def test_historical_absent_or_empty_optional_field_preserves_projection_shape(tmp_path):
    run = runtime.Run('history-bridge-test', 'old task', 'old-task', started_at_ms=100, ended_at_ms=101)
    before = evidence.capsule(run, tmp_path)
    assert frontier_bridge.project(run, tmp_path) is None
    assert evidence.capsule(run, tmp_path) == before
    report_before = capabilities.transitions(before)
    empty_capsule = copy.deepcopy(before)
    empty_capsule['capability_frontier'] = {}
    assert capabilities.transitions(empty_capsule) == report_before
    run.staged['capability_frontier'] = {}
    assert 'capability_frontier' not in evidence.capsule(run, tmp_path)


def test_optional_frontier_survives_run_store_roundtrip(tmp_path):
    workspace = tmp_path / 'workspace'
    run = bind(make_run(), workspace)
    run.staged['capability_frontier'] = frontier_bridge.project(run, workspace)
    store = runtime.RunStore(tmp_path / 'runs')
    store.save(run)
    assert store.load(run.run_id).staged['capability_frontier'] == run.staged['capability_frontier']
