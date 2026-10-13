"""Exercise admission at the real pipeline boundary, before the paid code call."""
import hashlib

import pytest

from skillnet import llm, pipeline, research, runtime, state_policy


@pytest.fixture(autouse=True)
def ledger():
    llm.LEDGER.reset()
    yield
    llm.LEDGER.reset()


def run():
    return runtime.Run(run_id=runtime.new_run_id('state'), task='计算数据并写出结果', task_fp='state')


def execute(r, path, plan):
    pipeline.execute_run(r, None, path, plan, max_steps=3, step_filter=lambda *_: True)
    pipeline.finalize_status(r)


@pytest.mark.parametrize('requires,state', [
    ([dict(kind='csv_schema', file='absent.csv', columns=['score'])], 'unknown'),
    ([dict(kind='clinical_validity', file='absent.csv')], 'unknown'),
])
def test_unprovable_precondition_never_calls_codegen(tmp_path, monkeypatch, requires, state):
    def forbidden(*_, **__):
        pytest.fail('Code generation must not be called on unknown admission')
    monkeypatch.setattr(llm, 'chat', forbidden)
    r = run()
    execute(r, tmp_path, dict(steps=[dict(action='读取表格计算', requires=requires)]))
    s = r.steps[0]
    assert s.status == 'failed' and not s.attempts and not s.code
    assert s.state_evidence['pre']['state'] == state
    assert s.state_evidence['pre']['admitted'] is False
    assert not any(e.type == 'code.generating' for e in r.events)


def test_real_postcondition_failure_blocks_downstream(tmp_path, monkeypatch):
    calls = []
    def code(*_, **__):
        calls.append(1)
        return '```python\nopen("data.csv","w").write("score\\n1.5\\n")\nprint("written")\n```'
    monkeypatch.setattr(llm, 'chat', code)
    r = run(); r.budget.max_attempts_per_step = 1
    execute(r, tmp_path, dict(steps=[
        dict(action='写表格', output_files=['data.csv'], ensures=[
            dict(kind='csv_numeric_range',file='data.csv',column='score',min=0,max=1)]),
        dict(action='统计表格',input_files=['data.csv'])]))
    assert len(calls) == 1
    assert r.steps[0].state_evidence['post']['state'] == 'failed'
    assert r.steps[0].status == 'failed' and r.steps[1].status == 'skipped'
    assert r.status != 'COMPLETED'
    assert r.steps[0].attempts[0].ok is True  # exit 0 is insufficient


def test_registered_input_tamper_never_calls_codegen(tmp_path, monkeypatch):
    (tmp_path/'artifacts').mkdir()
    (tmp_path/'artifacts'/'input.csv').write_text('score\n0.7\n')
    r = run()
    r.artifacts = [runtime.Artifact(name='input.csv',logical_name='input.csv',kind='跨轮输入',
        sha256=hashlib.sha256(b'score\n0.2\n').hexdigest(),bytes=10)]
    monkeypatch.setattr(llm, 'chat', lambda *a,**k: pytest.fail('tampered input admitted'))
    execute(r, tmp_path, dict(steps=[dict(action='统计数据',input_files=['input.csv'])]))
    assert r.steps[0].state_evidence['pre']['state'] == 'unknown'
    assert any(c['predicate']['kind']=='input_integrity' for c in r.steps[0].state_evidence['pre']['checks'])


def test_frozen_hypothesis_cannot_be_changed_before_codegen(tmp_path, monkeypatch):
    original = pipeline._run_steps_graph
    def mutate(r, *args):
        r.steps[0].contract['requires'] = []
        return original(r, *args)
    monkeypatch.setattr(pipeline, '_run_steps_graph', mutate)
    monkeypatch.setattr(llm, 'chat', lambda *a,**k: pytest.fail('changed contract admitted'))
    r = run()
    execute(r, tmp_path, dict(steps=[dict(action='计算',requires=[dict(kind='file_exists',file='x')])]))
    assert r.steps[0].state_evidence['pre']['state'] == 'unknown'


def test_host_reference_is_frozen_and_cannot_be_weakened(tmp_path):
    r = run(); r.task = research.research_scenario()['task']
    r.steps = [runtime.RunStep(idx=0,action='清洗',contract=dict(output_files=['clean_predictions.csv'],ensures=[])),
        runtime.RunStep(idx=1,action='指标',contract=dict(output_files=['heldout_metrics.csv'],requires=[]))]
    policy = state_policy.bind(r, tmp_path)
    assert policy['host_reference'] == 'research-reproducibility-v1'
    assert (tmp_path/'artifacts'/'input_raw_predictions.csv').read_bytes() == research.DATA.encode()
    assert r.artifacts[0].sha256 == hashlib.sha256(research.DATA.encode()).hexdigest()
    pre = r.steps[1].contract['requires']
    assert dict(kind='csv_values_in',file='clean_predictions.csv',column='label',values=[0,1]) in pre
    assert dict(kind='csv_disjoint_groups',file='clean_predictions.csv',entity='subject_id',group='split') in pre
    assert policy['frozen']['1']['sha256'] == state_policy.digest(state_policy.declaration(r.steps[1]))
    with pytest.raises(ValueError):
        state_policy.bind(r, tmp_path)


def test_state_evidence_roundtrip_and_historical_shape(tmp_path):
    store = runtime.RunStore(tmp_path)
    r = run(); r.steps = [runtime.RunStep(idx=0,action='x')]
    assert 'state_evidence' not in r.steps[0].to_dict()
    r.steps[0].state_evidence = {'pre':{'state':'unknown','admitted':False}}
    store.save(r)
    assert store.load(r.run_id).steps[0].state_evidence == r.steps[0].state_evidence


def test_codegen_cannot_weaken_frozen_output_conditions(tmp_path, monkeypatch):
    r = run(); r.budget.max_attempts_per_step = 1
    def mutate(*_, **__):
        r.steps[0].contract['ensures'] = []
        return '```python\nopen("data.csv","w").write("score\\n5\\n")\nprint("ok")\n```'
    monkeypatch.setattr(llm, 'chat', mutate)
    execute(r, tmp_path, dict(steps=[dict(action='生成表格',output_files=['data.csv'],ensures=[
        dict(kind='csv_numeric_range',file='data.csv',column='score',max=1)])]))
    assert r.steps[0].status == 'failed'
    post = r.steps[0].state_evidence['post']
    assert any(c['predicate']['kind']=='csv_numeric_range' and c['state']=='failed' for c in post['checks'])
    assert any(c['predicate']['kind']=='frozen_contract' and c['state']=='unknown' for c in post['checks'])


def test_delivery_bytes_must_match_postcondition_snapshot(tmp_path, monkeypatch):
    r = run(); r.budget.max_attempts_per_step = 1
    monkeypatch.setattr(llm,'chat',lambda *a,**k:'```python\nopen("data.csv","w").write("score\\n0.5\\n")\nprint("ok")\n```')
    original = pipeline._copy_retry
    def alter_on_delivery(source, target):
        if target.name=='step1_data.csv':
            source.write_text('score\n2\n')
        return original(source,target)
    monkeypatch.setattr(pipeline,'_copy_retry',alter_on_delivery)
    execute(r,tmp_path,dict(steps=[dict(action='生成表格',output_files=['data.csv'],ensures=[
        dict(kind='csv_numeric_range',file='data.csv',column='score',max=1)])]))
    assert r.steps[0].state_evidence['post']['state']=='unknown'
    assert r.steps[0].status=='failed'
    assert any(c['predicate']['kind']=='output_integrity' for c in r.steps[0].state_evidence['post']['checks'])


@pytest.mark.parametrize('predicate',[None,'plain',42,[]])
def test_malformed_predicate_preserves_unknown_diagnosis(tmp_path,monkeypatch,predicate):
    r=run()
    monkeypatch.setattr(llm,'chat',lambda *a,**k:pytest.fail('invalid predicate admitted'))
    execute(r,tmp_path,dict(steps=[dict(action='计算',requires=[predicate])]))
    assert r.steps[0].state_evidence['pre']['state']=='unknown'
    assert r.steps[0].checks and r.steps[0].checks[0].passed is False


def test_independent_original_values_blocks_before_metrics(tmp_path,monkeypatch):
    import csv
    import io
    r=run();r.task=research.research_scenario()['task'];r.budget.max_attempts_per_step=1
    rows=research.oracle()['clean_predictions']
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=['sample_id','subject_id','split','label','score'])
    writer.writeheader();writer.writerows([{**row,'score':str(float(row['score']))} for row in rows])
    code=f'```python\nopen("clean_predictions.csv","w",newline="").write({stream.getvalue()!r})\nprint("ok")\n```'
    calls=[]
    def generate(*a,**k):calls.append(1);return code
    monkeypatch.setattr(llm,'chat',generate)
    execute(r,tmp_path,dict(steps=[dict(action='清洗',output_files=['clean_predictions.csv']),
        dict(action='计算指标',input_files=['clean_predictions.csv'],output_files=['heldout_metrics.csv'])]))
    assert len(calls)==1 and r.steps[1].status=='skipped'
    assert r.steps[0].state_evidence['post']['state']=='passed'  # shape is fine
    assert any(c.name=='独立结果：clean_predictions.original_values' and not c.passed for c in r.steps[0].checks)
