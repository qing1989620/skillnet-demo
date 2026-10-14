"""Guard against leakage, misleading pooling and unsupported confidence claims."""
import math
import numpy as np
import pytest

from skillnet.routing_research import (grouped_source_split,query_fingerprint,
    routing_metrics,paired_routing_comparison,binomial_risk_upper)


def task(i,source='local',gold=None,query=None):
    return dict(id=str(i),source=source,gold=gold or [str(i)],query=query or 'question '+str(i))


def test_grouping_keeps_reference_sets_and_question_duplicates_in_one_partition():
    rows=[task(i) for i in range(30)]
    rows.extend([task('same-gold',gold=['2']),task('same-query',gold=['different'],query=' QUESTION  2 ')])
    split=grouped_source_split(rows,external_sources=())
    assert split['2']==split['same-gold']==split['same-query']
    assert {x[0] for x in split.values()}=={'train','validation','calibration','test'}


def test_component_touching_external_source_cannot_become_training():
    rows=[task('a',source='logic',query='shared'),task('b',source='bigcodebench',query='shared'),task('c',source='theoremqa')]
    split=grouped_source_split(rows)
    assert all(v[0]=='external_test' for v in split.values())


def test_question_fingerprint_normalizes_only_case_and_whitespace():
    assert query_fingerprint('  A\n B ')==query_fingerprint('a b')
    assert query_fingerprint('a b')!=query_fingerprint('a c')


def test_reference_recall_is_restricted_to_declared_source_pool():
    rows=[dict(id='q',source='sra',family='f',query='query',gold=['a','b'],pool='sra')]
    m=routing_metrics(np.array([[.8,.7,99.]]),rows,['a','b','wrong-source'],{'sra':[0,1]})
    assert m['recall5']==1 and m['rows'][0]['top5']==['a','b']


@pytest.mark.parametrize('scores,pool',[
    (np.array([[1.,float('nan')]]),[0,1]),(np.zeros((0,2)),[0,1]),
    (np.ones((1,2)),[-1,0]),(np.ones((1,2)),[0,0]),(np.ones((1,2)),[1]),
])
def test_invalid_or_incomplete_comparisons_are_rejected(scores,pool):
    t=dict(id='q',source='sra',family='f',query='q',gold=['a'],pool='sra')
    with pytest.raises(ValueError):routing_metrics(scores,[t],['a','b'],{'sra':pool})


def test_source_family_macro_does_not_reward_repeating_easy_questions():
    rows=[dict(id=str(i),source='a' if i<9 else 'b',family='f',query=str(i),gold=['gold'],pool='all') for i in range(10)]
    scores=np.tile([10.,0.,1.,2.,3.,4.],(10,1));scores[-1,0]=-1
    m=routing_metrics(scores,rows,['gold','x1','x2','x3','x4','x5'],{'all':list(range(6))})
    assert m['recall5']==.9 and m['source_family_macro']==.5
    assert m['families']==2


def test_paired_comparison_does_not_silently_drop_a_failure_or_change_reference():
    t=[dict(id='q',source='sra',family='f',query='q',gold=['a'],pool='all')]
    m=routing_metrics(np.array([[1.]]),t,['a'],{'all':[0]})
    assert paired_routing_comparison(m,m)['family_sign_p']==1
    with pytest.raises(ValueError):paired_routing_comparison(m,dict(rows=[]))
    altered=dict(m);altered['rows']=[dict(m['rows'][0],family='changed')]
    with pytest.raises(ValueError):paired_routing_comparison(m,altered)


def test_risk_bound_requires_evidence_and_matches_independent_beta_implementation():
    beta=pytest.importorskip('scipy.stats').beta
    assert binomial_risk_upper(0,0,.05)==1
    assert binomial_risk_upper(10,10,.05)==1
    assert math.isclose(binomial_risk_upper(3,20,.0125),beta.ppf(1-.0125,4,17),rel_tol=1e-10)
    assert binomial_risk_upper(0,20,.0125)>.1  # zero failures is not enough evidence
    assert binomial_risk_upper(0,100,.0125)<.1


@pytest.mark.parametrize('failure,n,delta',[(True,5,.05),(6,5,.05),(0,-1,.05),(0,5,0),(0,5,1)])
def test_invalid_risk_inputs_cannot_produce_certificates(failure,n,delta):
    with pytest.raises(ValueError):binomial_risk_upper(failure,n,delta)
