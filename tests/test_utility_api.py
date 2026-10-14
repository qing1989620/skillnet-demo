from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import threading
from fastapi.testclient import TestClient
import pytest
import server
from skillnet import conditional_utility as cu,utility_ops

ROOT=Path(__file__).resolve().parents[1]
AUTH={'X-SkillNet-Token':'utility-test-token'}


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'ACCESS_TOKEN','utility-test-token')
    monkeypatch.setattr(server,'S1_SIGNING_KEY','')
    monkeypatch.setattr(server.config,'OUT_DIR',tmp_path/'out')
    monkeypatch.setattr(server,'_FRONTIER_SLOTS',threading.BoundedSemaphore(2))
    c=TestClient(server.app)
    yield c,tmp_path
    c.close()


def test_metadata_exposes_full_comparisons_and_blocks_reward(client):
    c,_=client;r=c.get('/api/frontier/utility');assert r.status_code==200,r.text
    d=r.json();assert r.headers['cache-control']=='no-store'
    assert d['summary']['tasks']==40 and d['admission']['eligible'] is False
    assert d['llm']['plain_delivery_rate']==d['llm']['evidence_delivery_rate']==1
    assert d['strong_baselines']['contract_preflight']['verified_delivery_rate']==1
    assert {'version','gain','reliable','novel'}<=set(d['admission']['blockers'])
    assert not d['reward_applied'] and not d['formal_routing_deployed']
    assert c.get('/utility').status_code==200
    new=c.get('/api/frontier/utility/boundary').json()
    assert new['feature_rule_diagnostic']['defined_after_test'] is True
    assert new['feature_rule_diagnostic']['metrics']['valid_deliveries']==20


@pytest.mark.parametrize('base',['','/boundary'])
def test_choices_and_zip_are_bounded_and_no_private_paths(client,base):
    c,root=client;r=c.get('/api/frontier/utility'+base+'/cases');assert r.status_code==200
    assert len(r.json()['cases'])==40 and str(ROOT) not in r.text and str(root) not in r.text
    z=c.get('/api/frontier/utility'+base+'/evidence');assert z.status_code==200
    assert z.content[:2]==b'PK' and len(z.content)<8*1048576


@pytest.mark.parametrize('base',['','/boundary'])
@pytest.mark.parametrize('action',['predict','execute'])
def test_prediction_and_execution_require_auth(client,base,action):
    c,_=client;r=c.post('/api/frontier/utility'+base+'/'+action,json={'case_id':'sealed-penguins-01'})
    assert r.status_code==401


@pytest.mark.parametrize('payload',[{'case_id':True},{'case_id':'../private'},
    {'case_id':'iris-sealed-20','code':'evil()'},{'case_id':'iris-sealed-20','path':'C:/private'},[],{}])
def test_no_client_code_path_or_coerced_id(client,payload,monkeypatch):
    c,_=client;monkeypatch.setattr(utility_ops,'execute',lambda *args:pytest.fail('invalid body executed'))
    r=c.post('/api/frontier/utility/boundary/execute',json=payload,headers=AUTH)
    assert r.status_code==422


def test_v1_preserves_discovery_counterexample_and_real_failure(client):
    c,root=client;p=c.post('/api/frontier/utility/predict',json={'case_id':'sealed-boundary-new-empty-group'},headers=AUTH)
    assert p.status_code==200 and p.json()['prediction']['abstain'] is False
    r=c.post('/api/frontier/utility/execute',json={'case_id':'sealed-boundary-new-empty-group'},headers=AUTH)
    assert r.status_code==200,r.text
    d=r.json();assert d['results']['conditional']['execution']['status']=='failed'
    assert not d['results']['conditional']['oracle']['deliverable']
    assert d['report_sha256']==cu.digest({k:v for k,v in d.items() if k!='report_sha256'})
    assert not d['reward_applied'] and not d['formal_library_changed']
    assert not list((root/'out').glob('utility-api-*'))


def test_v2_refuses_group_counterexample_before_execution_and_still_physically_checks_diagnostic(client):
    c,root=client;r=c.post('/api/frontier/utility/boundary/execute',json={'case_id':'iris-sealed-20'},headers=AUTH)
    assert r.status_code==200,r.text
    d=r.json();assert d['results']['candidate']['state']=='abstained'
    assert d['results']['baseline']['execution']['status']=='failed'
    assert d['results']['diagnostic']['execution']['status']=='failed'
    assert d['predicted_at_ns']<d['results']['baseline']['execution']['started_at_ns']
    assert str(root) not in r.text and str(ROOT) not in r.text
    assert not list((root/'out').glob('utility-api-*'))


def test_v2_does_not_refuse_valid_cleaning_of_empty_groups(client):
    c,_=client;r=c.post('/api/frontier/utility/boundary/execute',json={'case_id':'iris-sealed-10'},headers=AUTH)
    assert r.status_code==200,r.text
    assert all(x['oracle']['deliverable'] for x in r.json()['results'].values())
    assert all(x['artifacts']['summary.csv']['text'].startswith('group,n_rows') for x in r.json()['results'].values())


def test_wrong_model_stops_before_execution(client,tmp_path,monkeypatch):
    c,_=client;copy=tmp_path/'public'
    shutil.copytree(ROOT/'assets/conditional-utility/v1',copy/'assets/conditional-utility/v1')
    (copy/'assets/conditional-utility/v1/model.json').write_text('{}')
    monkeypatch.setattr(server,'ROOT',copy)
    monkeypatch.setattr(utility_ops,'execute',lambda *args:pytest.fail('mismatched model executed'))
    r=c.post('/api/frontier/utility/execute',json={'case_id':'sealed-penguins-01'},headers=AUTH)
    assert r.status_code==503


def test_unknown_case_and_concurrency_preserve_resource_bound(client):
    c,_=client
    r=c.post('/api/frontier/utility/boundary/execute',json={'case_id':'unknown'},headers=AUTH)
    assert r.status_code==422
    server._FRONTIER_SLOTS.acquire();server._FRONTIER_SLOTS.acquire()
    try:
        r=c.post('/api/frontier/utility/boundary/execute',json={'case_id':'iris-sealed-20'},headers=AUTH)
        assert r.status_code==429
    finally:server._FRONTIER_SLOTS.release();server._FRONTIER_SLOTS.release()


def test_transient_paths_are_scrubbed_even_with_non_ascii_encoding_loss():
    from skillnet.utility_api import public_evidence
    value={'stderr':'File "D:\\private\\����\\main.py", line 44\nValueError: group has no numeric values',
           'oracle':{'reason':"[Errno 2] No such file: 'C:/private/attempt/summary.csv'"}}
    sanitized=public_evidence(value)
    assert 'private' not in json.dumps(sanitized)
    assert 'group has no numeric values' in sanitized['stderr']
    assert value['stderr'].startswith('File "D:')
    artifact={'artifacts':{'data.csv':{'text':'value\nC:/original/cell\n','sha256':'original'}}}
    assert public_evidence(artifact)==artifact
