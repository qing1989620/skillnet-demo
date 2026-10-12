"""Exercise physical version selection through the real DAG and subprocesses."""
from __future__ import annotations

import hashlib
import re

import pytest

from skillnet import llm, pipeline, runtime


@pytest.fixture(autouse=True)
def ledger():
    llm.LEDGER.reset()
    yield
    llm.LEDGER.reset()


def make_run():
    run = runtime.Run(run_id=runtime.new_run_id('versions'), task='核验文件版本', task_fp='versions')
    run.budget.max_attempts_per_step = 1
    return run


def codegen(monkeypatch, sources):
    calls = []

    def chat(messages, **kwargs):
        action = re.search(r'当前步骤：([^\n]+)', messages[-1]['content']).group(1)
        calls.append(action)
        return '```python\n' + sources[action] + '\n```'

    monkeypatch.setattr(llm, 'chat', chat)
    return calls


def execute(run, path, steps):
    pipeline.execute_run(run, None, path, dict(steps=steps), max_steps=len(steps), step_filter=lambda *_: True)
    pipeline.finalize_status(run)


def writer(action, deps, score):
    return dict(action=action, depends_on=deps, output_files=['shared.csv'],
                ensures=[dict(kind='csv_numeric_range', file='shared.csv', column='score', min=0, max=1)])


def source(score):
    return f'open("shared.csv","w",encoding="utf-8").write("score\\n{score}\\n")\nprint("written")'


def test_shortcut_to_old_ancestor_cannot_override_descendant_output(tmp_path, monkeypatch):
    calls = codegen(monkeypatch, dict(OLD=source('0.1'), NEW=source('0.9'), BRIDGE='print("bridge")',
        CONSUMER='raw=open("shared.csv",encoding="utf-8").read()\nopen("result.txt","w",encoding="utf-8").write(raw)\nprint(raw)'))
    run = make_run()
    execute(run, tmp_path, [writer('OLD', [], '0.1'), writer('NEW', [0], '0.9'),
        dict(action='BRIDGE', depends_on=[1]),
        # The old producer is graph-distance 1; NEW is graph-distance 2. The
        # artifact's ancestry dominance, rather than distance, determines version.
        dict(action='CONSUMER', depends_on=[0, 2], output_files=['result.txt'],
             requires=[dict(kind='csv_numeric_range', file='shared.csv', column='score', min=0, max=1)])])
    assert calls == ['OLD', 'NEW', 'BRIDGE', 'CONSUMER']
    assert run.status == 'COMPLETED'
    assert (tmp_path/'artifacts'/'step4_result.txt').read_text() == 'score\n0.9\n'
    shared = [a for a in run.steps[3].input_artifacts if a['logical_name'] == 'shared.csv']
    assert len(shared) == 1 and shared[0]['from_step'] == 1
    assert 'input_conflicts' not in run.steps[3].state_evidence


def test_parallel_producers_never_choose_a_winner_or_call_consumer_codegen(tmp_path, monkeypatch):
    calls = codegen(monkeypatch, dict(LEFT=source('0.1'), RIGHT=source('0.9')))
    run = make_run()
    execute(run, tmp_path, [writer('LEFT', [], '0.1'), writer('RIGHT', [], '0.9'),
        dict(action='CONSUMER', depends_on=[0, 1], output_files=['result.txt'],
             requires=[dict(kind='file_exists', file='shared.csv')])])
    assert sorted(calls) == ['LEFT', 'RIGHT']
    consumer = run.steps[2]
    assert consumer.status == 'failed' and not consumer.attempts
    assert consumer.state_evidence['pre']['admitted'] is False
    conflict = consumer.state_evidence['input_conflicts'][0]
    assert conflict['logical_name'] == 'shared.csv'
    assert {c['from_step'] for c in conflict['candidates']} == {0, 1}
    assert not (tmp_path/'step3'/'try1'/'shared.csv').exists()


def imported(run, path, name, contents, *, origin='older-run'):
    root = path/'artifacts'
    root.mkdir(parents=True, exist_ok=True)
    (root/name).write_bytes(contents)
    run.artifacts.append(runtime.Artifact(name=name, logical_name='shared.csv', kind='跨轮输入',
        bytes=len(contents), sha256=hashlib.sha256(contents).hexdigest(), source_run_id=origin))


def test_current_run_producer_supersedes_imported_version(tmp_path, monkeypatch):
    calls = codegen(monkeypatch, dict(NEW=source('0.9'),
        CONSUMER='raw=open("shared.csv",encoding="utf-8").read()\nopen("result.txt","w",encoding="utf-8").write(raw)\nprint(raw)'))
    run = make_run()
    imported(run, tmp_path, 'history_shared.csv', b'score\n0.1\n')
    execute(run, tmp_path, [writer('NEW', [], '0.9'),
        dict(action='CONSUMER', depends_on=[0], input_files=['shared.csv'], output_files=['result.txt'])])
    assert calls == ['NEW', 'CONSUMER']
    assert run.status == 'COMPLETED'
    assert (tmp_path/'artifacts'/'step2_result.txt').read_text() == 'score\n0.9\n'
    shared = [a for a in run.steps[1].input_artifacts if a['logical_name'] == 'shared.csv']
    assert len(shared) == 1 and shared[0]['from_step'] == 0


@pytest.mark.parametrize('second', [b'score\n0.9\n', b'score\n0.1\n'])
def test_two_external_sources_are_unknown_even_without_declared_requires(tmp_path, monkeypatch, second):
    run = make_run()
    imported(run, tmp_path, 'history_a.csv', b'score\n0.1\n', origin='older-a')
    imported(run, tmp_path, 'history_b.csv', second, origin='older-b')
    monkeypatch.setattr(llm, 'chat', lambda *_a, **_k: pytest.fail('ambiguous external input reached codegen'))
    execute(run, tmp_path, [dict(action='CONSUMER')])
    assert run.steps[0].status == 'failed'
    assert run.steps[0].state_evidence['pre']['state'] == 'unknown'
    assert run.steps[0].state_evidence['pre']['admitted'] is False
    assert len(run.steps[0].state_evidence['input_conflicts'][0]['candidates']) == 2


def test_unrelated_parallel_output_is_not_a_consumer_input(tmp_path, monkeypatch):
    calls = codegen(monkeypatch, dict(LEFT=source('0.1'), RIGHT=source('0.9'),
        CONSUMER='raw=open("shared.csv",encoding="utf-8").read()\nopen("result.txt","w",encoding="utf-8").write(raw)\nprint(raw)'))
    run = make_run()
    execute(run, tmp_path, [writer('LEFT', [], '0.1'), writer('RIGHT', [], '0.9'),
        dict(action='CONSUMER', depends_on=[0], output_files=['result.txt'], requires=[dict(kind='file_exists', file='shared.csv')])])
    assert sorted(calls) == ['CONSUMER', 'LEFT', 'RIGHT']
    assert run.status == 'COMPLETED'
    assert (tmp_path/'artifacts'/'step3_result.txt').read_text() == 'score\n0.1\n'
    assert 'input_conflicts' not in run.steps[2].state_evidence
