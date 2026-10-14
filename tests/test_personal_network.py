from __future__ import annotations
import hashlib,json,threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import numpy as np
import pytest
from fastapi.testclient import TestClient
import server
from skillnet.catalog import SkillLibrary
from skillnet.schema import Skill
from skillnet.personal_network import PersonalNetworkStore,Conflict
from skillnet.learned_network import NetworkAdapter,neighbour_features
from skillnet.network_service import NetworkModelService,train_private_preference_candidate,preview_private_candidate
from skillnet.s1_identity import sign,S1Context

A=dict(tenant='company',user='alice',project='research')
B=dict(tenant='company',user='bob',project='research')
KNOWN=['alpha','beta']

@pytest.fixture
def store(tmp_path):return PersonalNetworkStore(tmp_path/'private.sqlite3')

def test_questions_and_runs_never_supply_quality_labels_or_rewards(store):
    x=store.observe(A,'query','一条尚无结果的问题',{'reward':99,'quality_label':True},event_id='same')
    assert x['reward']==0 and x['quality_label'] is None
    assert not store.observe(A,'query','一条尚无结果的问题',{},event_id='same')['recorded']
    assert store.profile(A)['observations']=={'query':1}
    assert store.observations(A)[0]['quality_label'] is None
    assert store.profile(A)['weight_updates']==store.profile(A)['rewards_applied']==0
    assert not store.observations(B)

def test_settings_versions_rollback_and_disabled_learning(store):
    p=store.update(A,0,{'pinned':['alpha'],'enabled':False},KNOWN)
    assert p['version']==1 and p['pinned']==['alpha']
    assert not store.observe(A,'query','private',{})['recorded']
    with pytest.raises(Conflict):store.update(A,0,{},KNOWN)
    p=store.rollback(A,1,0,KNOWN)
    assert p['version']==2 and p['enabled'] and not p['pinned']
    with pytest.raises(ValueError):store.rollback(B,0,1,KNOWN)

def test_concurrent_owner_edits_are_not_lost(store):
    def edit(name):
        try:return store.update(A,0,{'pinned':[name]},KNOWN)['version']
        except Conflict:return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(edit,KNOWN))
    assert results.count(1)==results.count('conflict')==1
    assert store.profile(A)['version']==1

@pytest.mark.parametrize('patch',[
    {'pinned':['unknown']},{'pinned':['alpha'],'disabled':['alpha']},
    {'pinned':['alpha','alpha']},{'learning_mode':'automatic_deploy'},
    {'enabled':'yes'},{'retention':True},{'identity':B},
    {'edges':[{'source':'alpha','target':'beta','type':'depend_on'},{'source':'beta','target':'alpha','type':'depend_on'}]},
    {'edges':[{'source':'alpha','target':'../foreign','type':'compose_with'}]},
])
def test_invalid_edits_do_not_mutate_profile(store,patch):
    with pytest.raises(ValueError):store.update(A,0,patch,KNOWN)
    assert store.profile(A)['version']==0

def test_private_skill_and_edges_do_not_enter_shared_catalog(store):
    lib=SkillLibrary([Skill(n,n,'data') for n in KNOWN]);before=json.dumps([s.to_dict() for s in lib.all()],sort_keys=True)
    skill={'name':'personal-audit','description':'我的交付约定','instructions':'先核对真实文件；<script>alert(1)</script> 是文本。'}
    store.update(A,0,{'custom_skills':[skill],'edges':[{'source':'personal-audit','target':'alpha','type':'depend_on'}]},KNOWN)
    ga=store.graph(A,lib);gb=store.graph(B,lib)
    assert any(n['private'] for n in ga['nodes']) and not any(n['private'] for n in gb['nodes'])
    assert json.dumps([s.to_dict() for s in lib.all()],sort_keys=True)==before
    assert lib.get('personal-audit') is None

def test_explicit_preferences_do_not_label_unchosen_skills(store):
    store.feedback(A,'清洗数据','alpha','beta',KNOWN)
    row=store.observations(A)[0]
    assert row['kind']=='preference_pair' and row['preferred']=='alpha' and row['rejected']=='beta'
    assert row['execution_quality_claim'] is False and row['quality_label'] is None
    with pytest.raises(ValueError):store.feedback(A,'q','alpha','alpha',KNOWN)
    rows=[dict(name='beta',score=.9),dict(name='alpha',score=.8)]
    store.update(A,0,{'pinned':['alpha']},KNOWN)
    assert store.apply_preferences(A,rows)[0]['name']=='alpha'
    assert store.apply_preferences(B,rows)[0]['name']=='beta'

def test_retention_is_per_scope_and_replays_are_idempotent(store):
    store.update(A,0,{'retention':100},KNOWN)
    for i in range(105):store.observe(A,'query',str(i),{},event_id=str(i))
    store.observe(B,'query','other',{},event_id='0')
    assert len(store.observations(A,2000))==100 and len(store.observations(B,2000))==1

def test_checkpoint_is_data_only_validated_and_shadow_only(tmp_path):
    model=NetworkAdapter.identity();model.save(tmp_path)
    loaded=NetworkAdapter.load(tmp_path);x=np.eye(384,dtype=np.float32)[:3]
    np.testing.assert_allclose(loaded.query(x),x)
    np.testing.assert_allclose(loaded.skills(x),x)
    service=NetworkModelService(tmp_path)
    assert not service.status()['available'] and service.status()['shadow_only']
    p=tmp_path/'model.npz';p.write_bytes(p.read_bytes()+b'tampered')
    with pytest.raises(ValueError,match='fingerprint'):NetworkAdapter.load(tmp_path)
    weights=NetworkAdapter.identity().weights;weights['q_up'][0,0]=float('nan')
    with pytest.raises(ValueError):NetworkAdapter(weights,{})

def test_typed_neighbours_are_directional_and_do_not_count_duplicate_edges():
    x=np.eye(384,dtype=np.float32)[:2];edge={'source':'a','target':'b','type':'depend_on'}
    g=neighbour_features(x,['a','b'],[edge,edge])
    np.testing.assert_allclose(g[0,0],x[1]);assert not g[1].any()

class Encoder:
    status={'kind':'dense-onnx','revision':'test-encoder'}
    def embed(self,texts,prefix):
        result=[]
        for text in texts:
            v=np.zeros(384,np.float32)
            for word in text.lower().split():v[int(hashlib.sha256(word.encode()).hexdigest()[:8],16)%384]+=1
            v/=max(float(np.linalg.norm(v)),1e-8);result.append(v)
        return np.stack(result)

def test_real_private_gradient_fit_is_owned_and_never_deployed(store,tmp_path):
    lib=SkillLibrary([Skill('alpha','alpha data method','data'),Skill('beta','beta research method','data')]);enc=Encoder()
    train=[];hold=[]
    for i in range(50):
        q=f'alpha data query {i}'
        (hold if int(hashlib.sha256(q.encode()).hexdigest()[:8],16)%5==0 else train).append(q)
    for q in train[:4]+hold[:2]:store.feedback(A,q,'beta','alpha',KNOWN)
    report=train_private_preference_candidate(store,A,enc,lib,tmp_path/'models')
    assert report['trained'] and report['parameter_delta_l2']>0 and report['loss_after']<report['loss_before']
    assert report['holdout_queries']==2 and report['train_queries']==4
    assert report['deployed'] is False and report['reward']==0 and not report['gate']['eligible']
    ranking=[dict(name=n,score=1) for n in KNOWN]
    preview=preview_private_candidate(store,A,enc,lib,ranking,'alpha data query',tmp_path/'models')
    assert preview['available'] and not preview['applied']
    assert preview_private_candidate(store,B,enc,lib,ranking,'alpha data query',tmp_path/'models') is None
    with pytest.raises(ValueError):store.update(B,0,{'active_personal_model':report['model_id']},KNOWN)
    store.update(A,0,{'active_personal_model':report['model_id']},KNOWN)
    assert store.profile(A)['active_personal_model']==report['model_id']
    assert preview_private_candidate(store,A,enc,lib,ranking,'alpha data query',tmp_path/'models',report['model_id'])['available']
    store.update(A,1,{'pinned':['alpha']},KNOWN)
    assert store.profile(A)['active_personal_model'] is None
    assert preview_private_candidate(store,A,enc,lib,ranking,'alpha',tmp_path/'models')['available'] is False

@pytest.fixture
def api(tmp_path,monkeypatch):
    lib=SkillLibrary([Skill(n,n,'data') for n in KNOWN]);enc=Encoder()
    retriever=SimpleNamespace(vec=enc,search=lambda *a,**k:SimpleNamespace(candidates=[SimpleNamespace(name=n,score=1.,source='seed') for n in KNOWN]))
    monkeypatch.setattr(server,'STATE',{'lib':lib,'retriever':retriever})
    monkeypatch.setattr(server.config,'OUT_DIR',tmp_path/'out');monkeypatch.setattr(server.config,'DATA_DIR',tmp_path/'data')
    monkeypatch.setattr(server,'ACCESS_TOKEN','owned-test-token');monkeypatch.setattr(server,'S1_SIGNING_KEY','')
    c=TestClient(server.app,client=('127.0.0.1',50000));yield c;c.close()

AUTH={'X-SkillNet-Token':'owned-test-token'}

def test_api_identity_cannot_be_spoofed_and_private_responses_are_not_cached(api):
    assert api.get('/api/personal').status_code==401
    r=api.get('/api/personal',headers={**AUTH,'X-S1-User':'bob'})
    assert r.status_code==200 and r.json()['profile']['identity']['user']=='local'
    assert r.headers['Cache-Control']=='private, no-store'
    assert api.put('/api/personal/profile',headers=AUTH,json={'expected_version':0,'patch':{'identity':B}}).status_code==400
    assert api.post('/api/personal/search',headers=AUTH,json={'query':'q','user':'bob'}).status_code==422

def test_search_records_unlabeled_query_and_preserves_formal_weights(api):
    r=api.post('/api/personal/search',headers=AUTH,json={'query':'alpha data','compare_candidate':False})
    assert r.status_code==200 and r.json()['observation']['quality_label'] is None
    assert not r.json()['formal_model_weights_changed']
    assert api.get('/api/personal',headers=AUTH).json()['profile']['observations']['query']==1

def test_owner_can_try_and_withdraw_trained_preference_version_without_rewards(api):
    queries=[]
    for i in range(40):
        q=f'alpha data question {i}'
        if int(hashlib.sha256(q.encode()).hexdigest()[:8],16)%5!=0:queries.append(q)
    for q in queries[:4]:
        assert api.post('/api/personal/feedback',headers=AUTH,json={'query':q,'preferred':'beta','rejected':'alpha'}).status_code==200
    assert api.post('/api/personal/train',headers=AUTH,json={'model_path':'../outside'}).status_code==422
    trained=api.post('/api/personal/train',headers=AUTH,json={})
    assert trained.status_code==200 and trained.json()['trained']
    model_id=trained.json()['model_id']
    assert api.put('/api/personal/profile',headers=AUTH,json={'expected_version':0,'patch':{'active_personal_model':model_id}}).status_code==200
    routed=api.post('/api/personal/search',headers=AUTH,json={'query':queries[0],'compare_candidate':False}).json()
    assert routed['manual_personal_model_applied'] and not routed['formal_model_weights_changed']
    assert routed['source']=='owner_selected_preference_adapter'
    assert api.get('/api/personal/observations',headers=AUTH).json()['rows'][0]['selected']==[x['name'] for x in routed['selected']]
    assert api.put('/api/personal/profile',headers=AUTH,json={'expected_version':1,'patch':{'active_personal_model':None}}).status_code==200
    assert not api.post('/api/personal/search',headers=AUTH,json={'query':queries[0],'compare_candidate':False}).json()['manual_personal_model_applied']
    assert api.get('/api/personal',headers=AUTH).json()['profile']['rewards_applied']==0

def test_owner_defined_method_participates_in_trained_personal_ranking(api):
    private={'name':'personal-method','description':'beta research method','instructions':'compare actual data before reporting'}
    assert api.put('/api/personal/profile',headers=AUTH,json={'expected_version':0,'patch':{'custom_skills':[private]}}).status_code==200
    queries=[f'alpha data question {i}' for i in range(40)]
    queries=[q for q in queries if int(hashlib.sha256(q.encode()).hexdigest()[:8],16)%5!=0]
    for q in queries[:4]:
        assert api.post('/api/personal/feedback',headers=AUTH,json={'query':q,'preferred':'personal-method','rejected':'alpha'}).status_code==200
    trained=api.post('/api/personal/train',headers=AUTH,json={}).json()
    assert trained['trained'] and trained['parameter_delta_l2']>0
    assert api.put('/api/personal/profile',headers=AUTH,json={'expected_version':1,'patch':{'active_personal_model':trained['model_id']}}).status_code==200
    routed=api.post('/api/personal/search',headers=AUTH,json={'query':queries[0],'k':5,'compare_candidate':False}).json()
    assert routed['manual_personal_model_applied']
    personal=[r for r in routed['selected'] if r['name']=='personal-method']
    assert len(personal)==1 and personal[0]['private'] and not personal[0]['execution_verified']
    assert api.get('/api/personal',headers=AUTH).json()['profile']['rewards_applied']==0


def test_shared_label_body_change_invalidates_private_candidate(store,tmp_path):
    lib=SkillLibrary([Skill('alpha','alpha data method','data'),Skill('beta','beta research method','data')]);enc=Encoder()
    qs=[f'alpha question {i}' for i in range(40)]
    qs=[q for q in qs if int(hashlib.sha256(q.encode()).hexdigest()[:8],16)%5!=0]
    for q in qs[:3]:store.feedback(A,q,'beta','alpha',KNOWN)
    train_private_preference_candidate(store,A,enc,lib,tmp_path/'models')
    changed=SkillLibrary([Skill('alpha','different revised instructions','data'),lib.get('beta')])
    preview=preview_private_candidate(store,A,enc,changed,[dict(name='alpha')],qs[0],tmp_path/'models')
    assert not preview['available'] and '正文已经变化' in preview['reason']


def test_unlabeled_queries_do_not_displace_retained_preference_training(store,tmp_path):
    lib=SkillLibrary([Skill('alpha','alpha data method','data'),Skill('beta','beta research method','data')]);enc=Encoder()
    qs=[f'alpha question {i}' for i in range(40)]
    qs=[q for q in qs if int(hashlib.sha256(q.encode()).hexdigest()[:8],16)%5!=0]
    for q in qs[:3]:store.feedback(A,q,'beta','alpha',KNOWN)
    for i in range(205):store.observe(A,'query',f'unlabeled {i}',{})
    report=train_private_preference_candidate(store,A,enc,lib,tmp_path/'models')
    assert report['trained'] and report['examples']==3 and report['train_queries']==3


def test_preference_scope_rejects_an_unrelated_query_without_disabling_owner_version(api):
    queries=[f'alpha data question {i}' for i in range(40)]
    queries=[q for q in queries if int(hashlib.sha256(q.encode()).hexdigest()[:8],16)%5!=0]
    for q in queries[:3]:api.post('/api/personal/feedback',headers=AUTH,json={'query':q,'preferred':'beta','rejected':'alpha'})
    trained=api.post('/api/personal/train',headers=AUTH,json={}).json()
    api.put('/api/personal/profile',headers=AUTH,json={'expected_version':0,'patch':{'active_personal_model':trained['model_id']}})
    familiar=api.post('/api/personal/search',headers=AUTH,json={'query':queries[0],'compare_candidate':False}).json()
    unrelated=api.post('/api/personal/search',headers=AUTH,json={'query':'astronomy exoplanet orbital transit','compare_candidate':False}).json()
    assert familiar['manual_personal_model_applied'] and familiar['personal_candidate']['within_support']
    assert not unrelated['manual_personal_model_applied'] and not unrelated['personal_candidate']['within_support']
    assert [r['name'] for r in unrelated['selected']]==KNOWN
    assert api.get('/api/personal',headers=AUTH).json()['profile']['active_personal_model']==trained['model_id']


def test_supported_preference_targets_can_enter_personal_pool_outside_shared_top20(store,tmp_path):
    lib=SkillLibrary([Skill('alpha','alpha data method','data'),Skill('beta','beta method','data')]);enc=Encoder()
    qs=[f'alpha question {i}' for i in range(40)]
    qs=[q for q in qs if int(hashlib.sha256(q.encode()).hexdigest()[:8],16)%5!=0]
    for q in qs[:3]:store.feedback(A,q,'beta','alpha',KNOWN)
    train_private_preference_candidate(store,A,enc,lib,tmp_path/'models')
    result=preview_private_candidate(store,A,enc,lib,[dict(name='alpha',score=1)],qs[0],tmp_path/'models')
    assert result['within_support'] and {r['name'] for r in result['ranking']}=={'alpha','beta'}


def test_two_pairs_for_one_question_do_not_count_as_two_training_questions(store,tmp_path):
    lib=SkillLibrary([Skill(n,n,'data') for n in ['alpha','beta','gamma']]);q='one question'
    store.feedback(A,q,'beta','alpha',['alpha','beta','gamma']);store.feedback(A,q,'gamma','alpha',['alpha','beta','gamma'])
    with pytest.raises(ValueError,match='不同问题'):
        train_private_preference_candidate(store,A,Encoder(),lib,tmp_path/'models')


def test_owned_history_and_installed_candidate_versions_are_explicit(api):
    api.put('/api/personal/profile',headers=AUTH,json={'expected_version':0,'patch':{'pinned':['alpha']}})
    state=api.get('/api/personal',headers=AUTH).json()
    assert state['history_versions']==[0] and set(state['model_candidates'])=={'v1','v2'}
    assert api.post('/api/personal/search',headers=AUTH,json={'query':'q','candidate_version':'../foreign'}).status_code==422
    missing=api.post('/api/personal/search',headers=AUTH,json={'query':'q','candidate_version':'v2'}).json()
    assert missing['candidate'] is None and missing['candidate_error'] and missing['candidate_version']=='v2'
    assert api.post('/api/personal/rollback',headers=AUTH,json={'expected_version':1,'target_version':0}).status_code==200
    assert not api.get('/api/personal',headers=AUTH).json()['profile']['pinned']


def test_corrupted_research_reports_are_not_presented_as_verified(tmp_path):
    from skillnet.personal_api import read_research_report
    p=tmp_path/'report.json';p.write_text('[]')
    assert read_research_report(p) is None
    p.write_text('{"report_sha256":"forged","gain":1}')
    assert read_research_report(p) is None


def test_model_with_wrong_study_version_cannot_be_presented_as_the_reported_candidate(api):
    folder=server.config.DATA_DIR/'network-model-v2';folder.mkdir(parents=True)
    NetworkAdapter.identity().save(folder,encoder={'revision':'test-encoder'})
    np.savez_compressed(folder/'catalog.npz',features=np.eye(384,dtype=np.float32)[:2],neighbours=np.zeros((2,4,384),np.float32))
    (folder/'catalog.json').write_text(json.dumps({'names':KNOWN,'body_sha256':['x','y'],
        'file_sha256':hashlib.sha256((folder/'catalog.npz').read_bytes()).hexdigest()}))
    state=api.get('/api/personal',headers=AUTH).json()
    assert state['model_candidates']['v2']['available'] and not state['evidence_bindings']['v2']['verified']
    result=api.post('/api/personal/search',headers=AUTH,json={'query':'alpha','candidate_version':'v2'}).json()
    assert result['candidate'] is None and '版本不一致' in result['candidate_error']
    assert result['observation']['quality_label'] is None


def test_pausing_collection_preserves_owner_settings(store):
    store.update(A,0,{'enabled':False,'pinned':['beta']},KNOWN)
    assert store.apply_preferences(A,[dict(name='alpha'),dict(name='beta')])[0]['name']=='beta'
    assert not store.observe(A,'query','not collected',{})['recorded']

def test_remote_unsigned_client_cannot_access_local_profile(api):
    with TestClient(server.app,client=('10.0.0.2',50000)) as remote:
        assert remote.get('/api/personal',headers=AUTH).status_code==403

def test_signed_users_have_distinct_profiles_and_cannot_replay_writes(api,monkeypatch):
    key='personal-network-test-signing-key-with-32-characters';monkeypatch.setattr(server,'S1_SIGNING_KEY',key)
    nonces=set()
    def consume(n):
        if n in nonces:return False
        nonces.add(n);return True
    monkeypatch.setattr(server,'job_queue',lambda:SimpleNamespace(consume_nonce=consume))
    body=json.dumps({'expected_version':0,'patch':{'pinned':['alpha']}},separators=(',',':')).encode();path='/api/personal/profile'
    headers={**AUTH,**sign(key,'PUT',path,body,S1Context(**A)),'Content-Type':'application/json'}
    assert api.put(path,headers=headers,content=body).status_code==200
    assert api.put(path,headers=headers,content=body).status_code==409
    get='/api/personal';other={**AUTH,**sign(key,'GET',get,b'',S1Context(**B))}
    assert not api.get(get,headers=other).json()['profile']['pinned']
    assert api.get(get,headers=AUTH).status_code==401
