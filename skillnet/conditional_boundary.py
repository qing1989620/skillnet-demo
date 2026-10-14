"""Counterexample-guided observation repair plus a learned failure classifier.

Feature design is human guided, not autonomous causal discovery. Coefficients
are fitted ONLY to earlier training executions, never to the discovery test.
Projected row conditions are predictions; actual artifacts remain the oracle.
"""
from __future__ import annotations
import csv
from decimal import Decimal,InvalidOperation
import io
import math
import numpy as np
from . import conditional_utility as cu

VERSION='conditional-boundary-v2'
FEATURES=('no_projected_test_rows','any_projected_group_without_number','bad_projected_number')


def observe(raw:bytes,intent:dict,mask:int)->dict:
    base=cu.features(raw,intent)
    if not base['supported_contract']:
        return {'supported':False,'vector':None,'conditions':{},'input_sha256':base['input_sha256']}
    if type(mask) is not int or not 0<=mask<=7:raise ValueError('unregistered mask')
    rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'),newline=''),strict=True))[1:]
    if mask&1:
        seen=set();selected=[]
        for r in rows:
            if r[0] not in seen:selected.append(r);seen.add(r[0])
        rows=selected
    if mask&2:
        splits={}
        for r in rows:splits.setdefault(r[1],set()).add(r[2])
        rows=[r for r in rows if len(splits[r[1]])==1]
    if mask&4:rows=[r for r in rows if r[4].strip()]
    test=[r for r in rows if r[2]=='test'];groups={}
    bad=False
    for r in test:
        groups.setdefault(r[3],[]).append(r[4])
        if r[4].strip():
            try:
                v=Decimal(r[4].strip());bad=bad or not v.is_finite() or abs(v)>Decimal('1e12')
            except InvalidOperation:bad=True
    empty_groups=sorted(k for k,vs in groups.items() if not any(v.strip() for v in vs))
    vector=[int(not test),int(bool(empty_groups)),int(bad)]
    return {'supported':True,'vector':vector,'conditions':dict(zip(FEATURES,vector)),
            'empty_groups':empty_groups,'projected_test_rows':len(test),
            'input_sha256':base['input_sha256'],'mask':mask,
            'observation_kind':'pre-execution projection under reviewed row transforms; not an executed result'}


def fit(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float)
    if x.ndim!=2 or x.shape[1]!=3 or y.shape!=(len(x),) or not np.isin(x,[0,1]).all() or not np.isin(y,[0,1]).all():
        raise ValueError('invalid executed training labels')
    z=np.column_stack([np.ones(len(x)),x]);w=np.zeros(4);curve=[]
    for step in range(1200):
        p=1/(1+np.exp(-np.clip(z@w,-30,30)))
        regularizer=np.r_[0,w[1:]]*.002
        w-=.2*(z.T@(p-y)/len(x)+regularizer)
        if step%20==0 or step==1199:
            loss=-np.mean(y*np.log(np.maximum(p,1e-12))+(1-y)*np.log(np.maximum(1-p,1e-12)))+.001*float(w[1:]@w[1:])
            curve.append({'step':step,'loss':float(loss)})
    return {'version':VERSION,'features':list(FEATURES),'coefficients':w.tolist(),
            'training_execution_rows':len(x),'training_failures':int(y.sum()),'curve':curve,
            'optimizer':{'steps':1200,'learning_rate':.2,'l2':.002},
            'feature_origin':'human-guided repair of group observability after v1 counterexample',
            'formal_routing_deployed':False,'reward_applied':False}


def validate(model):
    if model.get('version')!=VERSION or model.get('features')!=list(FEATURES):raise ValueError('wrong boundary model')
    w=model.get('coefficients')
    if type(w) is not list or len(w)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>100 for v in w):
        raise ValueError('invalid boundary coefficients')


def predict(model,observed,threshold):
    validate(model)
    if type(threshold) not in (float,int) or not 0<threshold<1:raise ValueError('invalid threshold')
    probability=None
    if observed['supported']:
        score=sum(a*b for a,b in zip(model['coefficients'],[1]+observed['vector']))
        probability=1/(1+math.exp(-max(-30,min(30,score))))
    abstain=probability is None or probability>=threshold
    return {'version':VERSION,'model_sha256':cu.digest(model),'observed':observed,
            'failure_score':probability,'threshold':threshold,'abstain':abstain,
            'reason':'unsupported_contract' if probability is None else 'learned_failure_boundary' if abstain else 'no_learned_boundary_triggered',
            'probability_warning':'logistic score is not a calibrated probability or a safety certificate',
            'reward_applied':False,'formal_routing_deployed':False}
