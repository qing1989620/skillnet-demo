from __future__ import annotations
import csv
import io
import json
from pathlib import Path
import numpy as np
import pytest

from skillnet import conditional_utility as cu, utility_ops as ops, utility_oracle as oracle


def raw(rows):
    f=io.StringIO(newline='');w=csv.writer(f,lineterminator='\n');w.writerow(ops.HEADER);w.writerows(rows)
    return f.getvalue().encode()


def intent(mask=0):
    return {**{k:bool(mask&(1<<j)) for j,k in enumerate(cu.KEYS)},'goal':'group_mean'}


ROWS=[['a','A','test','g','10'],['b','B','test','g','20'],['c','C','train','g','30']]


def test_real_program_and_independent_reference_disagree_on_unwanted_dedup(tmp_path):
    data=raw(ROWS+[list(ROWS[0])]);source=tmp_path/'input.csv';source.write_bytes(data)
    good=ops.execute(0,source,tmp_path/'keep');bad=ops.execute(1,source,tmp_path/'drop')
    assert good['status']==bad['status']=='completed'
    assert oracle.evaluate(data,intent(0),tmp_path/'keep')['deliverable']
    assert not oracle.evaluate(data,intent(0),tmp_path/'drop')['deliverable']
    table=list(csv.reader((tmp_path/'keep'/'summary.csv').open()))
    assert table[1][1:4]==['3','3','40']
    assert oracle.evaluate(data,intent(1),tmp_path/'drop')['deliverable']


def test_missing_retention_changes_row_count_without_changing_mean(tmp_path):
    data=raw(ROWS+[['d','D','test','g',' ']]);source=tmp_path/'input.csv';source.write_bytes(data)
    ops.execute(0,source,tmp_path/'keep');ops.execute(4,source,tmp_path/'drop')
    assert oracle.evaluate(data,intent(0),tmp_path/'keep')['deliverable']
    assert not oracle.evaluate(data,intent(0),tmp_path/'drop')['deliverable']
    assert oracle.evaluate(data,intent(4),tmp_path/'drop')['deliverable']


@pytest.mark.parametrize('mask',[True,-1,8,'1',1.0,None])
def test_program_only_accepts_registered_actions(tmp_path,mask):
    with pytest.raises(ValueError):ops.execute(mask,tmp_path/'missing',tmp_path/'bad')
    assert not (tmp_path/'bad').exists()


def test_tampered_numeric_output_is_rejected(tmp_path):
    data=raw(ROWS);source=tmp_path/'input.csv';source.write_bytes(data)
    ops.execute(0,source,tmp_path/'run')
    summary=tmp_path/'run'/'summary.csv'
    summary.write_text('group,n_rows,n_numeric,sum,mean\ng,2,2,30,19\n')
    report=oracle.evaluate(data,intent(),tmp_path/'run')
    assert report['state']=='failed' and not report['deliverable']


@pytest.mark.parametrize('cell',['NaN','Infinity','bad-unit'])
def test_bad_test_number_is_observed_and_program_failure_not_positive_label(tmp_path,cell):
    data=raw(ROWS+[['d','D','test','g',cell]])
    assert cu.features(data,intent())['features']['has_bad_test_number']==1
    source=tmp_path/'input.csv';source.write_bytes(data)
    execution=ops.execute(0,source,tmp_path/'run');report=oracle.evaluate(data,intent(),tmp_path/'run')
    assert execution['status']=='failed' and not report['reference_valid'] and not report['deliverable']


def test_unmodeled_group_boundary_is_preserved_not_relabeled_success(tmp_path):
    data=raw(ROWS+[['d','D','test','other','']])
    observed=cu.features(data,intent())
    assert observed['features']['all_test_blank']==0 and observed['features']['has_missing']==1
    source=tmp_path/'input.csv';source.write_bytes(data)
    assert ops.execute(0,source,tmp_path/'run')['status']=='failed'
    assert not oracle.evaluate(data,intent(),tmp_path/'run')['reference_valid']


def test_tree_learns_effect_reversal_and_keeps_unknown_outside_scope(tmp_path):
    xs,ys=[],[]
    for want in (0,1):
        obs=cu.features(raw(ROWS+[list(ROWS[0])]),intent(want))
        for _ in range(2):
            xs.append(obs['vector']);ys.append([int(bool(m&1)==bool(want)) for m in range(8)]+[0]*8)
    model=cu.fit_tree(np.array(xs),np.array(ys))
    path=tmp_path/'model.json';path.write_text(json.dumps(model))
    model=cu.load_model(path)
    keep=cu.predict(model,cu.features(raw(ROWS+[list(ROWS[0])]),intent(0)))
    drop=cu.predict(model,cu.features(raw(ROWS+[list(ROWS[0])]),intent(1)))
    assert keep['marginal'][0]['predicted_marginal_gain']==-1
    assert drop['marginal'][0]['predicted_marginal_gain']==1
    assert keep['mask']==0 and drop['mask']==1
    unknown=cu.predict(model,cu.features(raw(ROWS),intent()))
    assert unknown['abstain'] and unknown['mask'] is None
    assert not unknown['reward_applied'] and not unknown['formal_routing_deployed']


def test_corrupt_or_nonfinite_model_refused():
    x=np.zeros((4,len(cu.FEATURES)));y=np.zeros((4,16));m=cu.fit_tree(x,y)
    m['tree']['value'][0]=float('nan')
    with pytest.raises(ValueError):cu.validate_model(m)


def test_unsupported_goal_is_not_silently_turned_into_supported_task():
    task=intent();task['goal']='weighted_median'
    assert not cu.features(raw(ROWS),task)['supported_contract']
    assert not oracle.evaluate(raw(ROWS),task,None)['reference_valid']


def test_task_policy_types_cannot_be_coerced():
    task=intent();task['deduplicate']='false'
    with pytest.raises(ValueError):cu.features(raw(ROWS),task)


@pytest.mark.parametrize('text',[
    '{"mask":true,"reject":false}', '{"mask":0,"reject":"false"}',
    '{"mask":0,"reject":false,"code":"evil"}', '{"mask":9,"reject":false}',
    '{"mask":7,"reject":true}', 'not JSON', '[]', '{"reject":true}',
])
def test_model_cannot_supply_code_or_unregistered_actions(text):
    from tools.conditional_llm_contrast import parse_action
    with pytest.raises((ValueError,TypeError)):parse_action(text)


def test_valid_model_action_is_exact_and_budgeted():
    from tools.conditional_llm_contrast import parse_action
    assert parse_action('{"mask":3,"reject":false}')=={'mask':3,'reject':False}
    assert parse_action('{"mask":null,"reject":true}')=={'mask':None,'reject':True}
