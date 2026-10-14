import hashlib
import pytest
from skillnet import state_contracts as sc


def spec(**extra):
    return {'kind':'csv_group_numeric_coverage','file':'data.csv','group':'group','column':'value',
            'where':{'column':'split','equals':'test'},**extra}


def observed(tmp_path,text,predicate=None):
    path=tmp_path/'data.csv';path.write_text(text,encoding='utf-8')
    return sc.evaluate([predicate or spec()],{'data.csv':path})['checks'][0]


def test_partial_group_blank_is_detected_even_when_entire_dataset_has_values(tmp_path):
    r=observed(tmp_path,'group,value,split\na,1,test\nb,,test\nb, ,test\n')
    assert r['state']=='failed'
    assert r['evidence']['groups_without_numeric']==1 and r['evidence']['empty_groups']==['b']
    assert len(r['evidence']['sha256'])==64


def test_mixed_blank_numeric_groups_pass_and_training_only_group_does_not_block(tmp_path):
    r=observed(tmp_path,'group,value,split\na,1,test\na,,test\nb,2,test\nc,,train\n')
    assert r['state']=='passed' and r['evidence']['groups']==2


@pytest.mark.parametrize('value',['NaN','Infinity','1 cm','bad'])
def test_one_invalid_value_cannot_hide_behind_another_valid_value(tmp_path,value):
    r=observed(tmp_path,f'group,value,split\na,1,test\na,{value},test\n')
    assert r['state']=='failed' and r['evidence']['invalid_numeric_records']==1


def test_no_matching_partition_fails_instead_of_vacuous_success(tmp_path):
    r=observed(tmp_path,'group,value,split\na,1,train\n')
    assert r['state']=='failed' and r['evidence']['groups']==0


@pytest.mark.parametrize('where',[{'column':'split','equals':1},{'column':'split','equals':'test','eval':'evil'},'test',True])
def test_invalid_filter_is_unknown_without_reading(tmp_path,monkeypatch,where):
    monkeypatch.setattr(sc,'_snapshot',lambda *_:pytest.fail('invalid filter read file'))
    assert sc.evaluate([spec(where=where)],{'data.csv':tmp_path/'missing'})['checks'][0]['state']=='unknown'


def test_column_schema_and_filters_must_agree_before_declared_composition():
    def step(i,**c):return {'idx':i,'depends_on':[] if i==0 else [0],'contract':c}
    wanted=spec();other=spec(where={'column':'split','equals':'train'})
    mismatch=sc.composition([step(0,ensures=[other]),step(1,requires=[wanted])])
    assert mismatch['state']=='unknown'
    same=sc.composition([step(0,ensures=[wanted]),step(1,requires=[wanted])])
    assert same['state']=='declared_compatible'


def test_real_pipeline_blocks_paid_codegen_for_partial_group_missing(tmp_path,monkeypatch):
    from skillnet import pipeline,runtime,llm
    raw=b'group,value,split\na,1,test\nb,,test\n'
    (tmp_path/'artifacts').mkdir();(tmp_path/'artifacts'/'data.csv').write_bytes(raw)
    run=runtime.Run(run_id=runtime.new_run_id('group'),task='group-summary-boundary',task_fp='group')
    run.artifacts=[runtime.Artifact(name='data.csv',logical_name='data.csv',kind='跨轮输入',
        sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))]
    monkeypatch.setattr(llm,'chat',lambda *args,**kw:pytest.fail('group failure reached paid code generation'))
    pipeline.execute_run(run,None,tmp_path,{'steps':[{'action':'按分组计算均值','input_files':['data.csv'],
        'requires':[spec()]}]},max_steps=1,step_filter=lambda *_:True)
    step=run.steps[0]
    assert step.state_evidence['pre']['state']=='failed'
    assert step.state_evidence['pre']['admitted'] is False
    assert not step.code and not step.attempts
    assert not any(e.type=='code.generating' for e in run.events)


def test_no_declared_proof_from_coverage_when_enumeration_forbids_selected_rows():
    coverage=spec()
    impossible={'kind':'csv_values_in','file':'data.csv','column':'split','values':['train']}
    result=sc.composition([{'idx':0,'contract':{'ensures':[coverage,impossible]}},
                           {'idx':1,'depends_on':[0],'contract':{'requires':[coverage]}}])
    assert result['state']=='unknown'
    assert 'inconsistent' in result['edges'][0]['detail']
