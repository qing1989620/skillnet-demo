import numpy as np
import pytest
from skillnet import conditional_boundary as cb
import test_conditional_utility as base


def test_group_boundary_is_observed_before_execution_and_respects_task_actions():
    data=base.raw(base.ROWS+[['d','D','test','other','']])
    preserve=cb.observe(data,base.intent(0),0)
    remove=cb.observe(data,base.intent(4),4)
    assert preserve['conditions']['any_projected_group_without_number']==1
    assert preserve['empty_groups']==['other']
    assert remove['conditions']['any_projected_group_without_number']==0
    assert 'projection' in remove['observation_kind']


def test_boundary_gradient_training_can_learn_observed_failure_labels():
    x=np.array([[0,0,0]]*12+[[1,0,0],[0,1,0],[0,0,1]]*6)
    y=np.array([0]*12+[1]*18);model=cb.fit(x,y)
    clean={'supported':True,'vector':[0,0,0]}
    failing={'supported':True,'vector':[0,1,0]}
    assert cb.predict(model,clean,.5)['abstain'] is False
    assert cb.predict(model,failing,.5)['abstain'] is True
    assert model['curve'][-1]['loss']<model['curve'][0]['loss']
    assert not model['reward_applied']


def test_schema_and_goal_unknown_do_not_receive_fabricated_probability():
    data=base.raw(base.ROWS);task=base.intent();task['goal']='median'
    o=cb.observe(data,task,0);model=cb.fit(np.array([[0,0,0],[1,0,0]]*2),np.array([0,1]*2))
    p=cb.predict(model,o,.5)
    assert p['failure_score'] is None and p['abstain'] and p['reason']=='unsupported_contract'


@pytest.mark.parametrize('coefficient',[float('nan'),float('inf'),True,101,'1'])
def test_invalid_boundary_weights_refused(coefficient):
    m={'version':cb.VERSION,'features':list(cb.FEATURES),'coefficients':[0,1,1,coefficient]}
    with pytest.raises(ValueError):cb.validate(m)
