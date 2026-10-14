from __future__ import annotations
import json
from pathlib import Path
import threading
import numpy as np
import pytest
from fastapi.testclient import TestClient
import server
from skillnet import semantic_routing as sr,semantic_study,reviewed_execution as re,utility_ops
from tools.verify_semantic_routing import public_audit
from tools.verify_reviewed_guard import public_audit as guard_audit

ROOT=Path(__file__).resolve().parents[1]
AUTH={'X-SkillNet-Token':'semantic-test'}


def test_complete_physical_evidence_is_independently_recomputed():
    result=public_audit(ROOT/'assets/semantic-routing/v1')
    assert result['ok'] and result['api_requests']==144 and result['physical_executions']==139
    assert result['verified_output_files']==257
    g=guard_audit(ROOT/'assets/semantic-routing/guard-v1')
    assert g['ok'] and g['physical_executions']==96
    assert g['false_blocks']==g['missed_execution_failures']==g['oracle_mismatches']==0


@pytest.mark.parametrize('text',['{"mask":0,"reject":true}','{"mask":true,"reject":false}',
    '{"mask":8,"reject":false}','{"mask":null,"reject":"true"}',
    '{"mask":0,"reject":false,"code":"evil"}','```json\n{}\n```'])
def test_malformed_actions_cannot_reach_execution(text):
    with pytest.raises(ValueError):sr.parse_action(text)


def test_nonfinite_model_is_not_loadable():
    m={'version':sr.VERSION,'classes':list(range(9)),'weights':np.zeros((384,9)).tolist(),'intercept':[0]*9}
    m['weights'][0][0]=float('nan')
    with pytest.raises(ValueError):sr.predict(m,np.zeros((1,384)))


def test_failed_preflight_never_creates_workspace_or_runs_program(tmp_path,monkeypatch):
    raw=b'sample_id,subject_id,split,group,value\na,a,test,A,1\nb,b,test,B,\n'
    monkeypatch.setattr(utility_ops,'execute',lambda *_:pytest.fail('invalid groups reached execution'))
    out=tmp_path/'run';r=re.execute(raw,0,out)
    assert r['state']=='preflight_rejected' and not out.exists()
    assert not r['preflight']['semantic_scope_validated']


def test_guard_uses_exact_snapshot_and_allows_blank_deletion(tmp_path):
    raw=b'sample_id,subject_id,split,group,value\na,a,test,A,1\nb,b,test,B,\n'
    r=re.execute(raw,4,tmp_path/'run')
    assert r['state']=='completed'
    assert r['execution']['input_sha256']==r['preflight']['input_sha256']
    assert r['preflight']['checked_at_ns']<r['execution']['started_at_ns']
    assert not r['preflight']['semantic_scope_validated']


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'ACCESS_TOKEN','semantic-test');monkeypatch.setattr(server,'S1_SIGNING_KEY','')
    monkeypatch.setattr(server.config,'OUT_DIR',tmp_path/'out')
    monkeypatch.setattr(server,'_FRONTIER_SLOTS',threading.BoundedSemaphore(2))
    c=TestClient(server.app)
    yield c,tmp_path
    c.close()


def test_public_projection_preserves_negative_results_and_all_failures(client):
    c,_=client;r=c.get('/api/frontier/utility/semantic');assert r.status_code==200,r.text
    d=r.json();a=d['report']['admission']
    assert d['report']['metrics']['plain']['valid_deliveries']==32
    assert d['report']['metrics']['trained_hint']['valid_deliveries']==30
    assert d['report']['metrics']['trained_hint']['failed_calls']==1
    assert not a['eligible'] and not a['reward_applied'] and a['points']==0
    assert {'complete','fair','version','regression','gain','reliable','novel'}<=set(a['blockers'])
    assert len(d['cases'])==24 and r.headers['cache-control']=='no-store'
    assert c.get('/api/frontier/utility/semantic/evidence').content[:2]==b'PK'


def test_replay_authentication(client):
    c,_=client;assert c.post('/api/frontier/utility/semantic/replay',json={'case_id':'wine-sealed-0-0'}).status_code==401


@pytest.mark.parametrize('payload',[{'case_id':'../secret'},{'case_id':'wine-sealed-0-0','repeat':True},
    {'case_id':'wine-sealed-0-0','repeat':2},{'case_id':'wine-sealed-0-0','code':'evil'},
    {'case_id':'wine-sealed-0-0','path':'C:/private'}])
def test_no_client_code_path_or_invalid_repeat(client,payload,monkeypatch):
    c,_=client;monkeypatch.setattr(semantic_study,'replay',lambda *_:pytest.fail('invalid body replayed'))
    assert c.post('/api/frontier/utility/semantic/replay',json=payload,headers=AUTH).status_code==422


def test_actual_replay_stops_invalid_data_before_program_and_cleans_temporary_files(client):
    c,root=client;r=c.post('/api/frontier/utility/semantic/replay',json={'case_id':'wine-boundary-5'},headers=AUTH)
    assert r.status_code==200,r.text;d=r.json()
    assert d['recorded_api_decisions'] and d['new_api_calls']==0 and d['points']==0
    assert d['results']['plain']['execution']['status']=='failed'
    assert d['results']['guarded_plain']['state']=='preflight_rejected'
    assert 'execution' not in d['results']['guarded_plain']
    assert not list((root/'out').glob('semantic-replay-*'))
    assert str(root) not in r.text and str(ROOT) not in r.text


def test_second_recorded_batch_preserves_malformed_decision_and_guard_semantic_limit(client):
    c,_=client;r=c.post('/api/frontier/utility/semantic/replay',json={'case_id':'wine-boundary-2','repeat':1},headers=AUTH)
    assert r.status_code==200,r.text;d=r.json()
    assert d['results']['trained_hint']['state']=='invalid_recorded_action'
    # Data-valid does not entail that keeping first is allowed when last was requested.
    d=c.post('/api/frontier/utility/semantic/replay',json={'case_id':'wine-boundary-2','repeat':0},headers=AUTH).json()
    assert d['results']['guarded_plain']['preflight']['allowed']
    assert d['results']['guarded_plain']['state']=='rejected'


def test_missing_or_changed_bundle_fails_closed(client,monkeypatch):
    c,_=client
    from skillnet import utility_api
    original=utility_api._read
    def changed(path,max_bytes):
        raw=original(path,max_bytes)
        return raw+b' ' if str(path).replace('\\','/').endswith('semantic-routing/v1/report.json') else raw
    monkeypatch.setattr(utility_api,'_read',changed)
    assert c.get('/api/frontier/utility/semantic').status_code==503


def test_unknown_case_and_full_slots(client,monkeypatch):
    c,_=client
    assert c.post('/api/frontier/utility/semantic/replay',json={'case_id':'unknown'},headers=AUTH).status_code==422
    slots=threading.BoundedSemaphore(1);slots.acquire();monkeypatch.setattr(server,'_FRONTIER_SLOTS',slots)
    r=c.post('/api/frontier/utility/semantic/replay',json={'case_id':'wine-sealed-0-0'},headers=AUTH)
    assert r.status_code==429 and r.headers['retry-after']=='2'
