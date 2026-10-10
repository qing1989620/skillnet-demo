"""Research correctness and host handoff at actual file/HTTP trust boundaries."""
import copy
import hashlib
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import server
from skillnet import assessment, evidence, research, reward_gates, runtime
from skillnet.catalog import SkillLibrary
from skillnet.integration import ClientConfig, IntegrationError, SkillNetClient
from skillnet.s1_identity import S1Context, sign
from skillnet.schema import Skill

CLEAN = '''sample_id,subject_id,split,label,score
s02,p02,train,1,0.90
s03,p03,train,1,0.80
s04,p04,validation,0,0.20
s05,p05,validation,1,0.70
s06,p06,test,1,0.90
s07,p07,test,0,0.20
s08,p08,test,1,0.40
s09,p09,test,0,0.80
s10,p10,test,1,0.70
s11,p11,test,0,0.30
'''
AUDIT = 'check,count\nraw_rows,14\nduplicate_rows,1\ncross_split_subjects,1\ncross_split_rows,2\nmissing_score_rows,1\neligible_test_rows,6\n'
METRICS = 'metric,value\nn,6\ntp,2\nfp,1\ntn,2\nfn,1\naccuracy,0.6666666666666666\nprecision,0.6666666666666666\nrecall,0.6666666666666666\nf1,0.6666666666666666\n'


def make_run(workspace):
    case = research.research_scenario()
    run = runtime.Run('research-evidence-test', case['task'], 'research', status='COMPLETED',
        started_at_ms=1000, ended_at_ms=5000, cost_yuan=.2, llm_calls=5)
    run.staged['evaluation_contract'] = assessment.prepare_contract(run.task)
    run.model = run.staged['evaluation_contract']['profile']['model']
    files = [(0,'clean_predictions.csv',CLEAN), (0,'cohort_audit.csv',AUDIT),
        (1,'heldout_metrics.csv',METRICS), (2,'report.md','模拟数据，固定阈值；不代表临床有效性。'),
        (2,'figure.svg','<svg>'+(' '*150)+'</svg>')]
    for idx, name, text in files:
        target = workspace/'artifacts'/f'step{idx+1}_{name}'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8', newline='\n')
        run.artifacts.append(runtime.Artifact(name=target.name, logical_name=name, from_step=idx,
            sha256=hashlib.sha256(target.read_bytes()).hexdigest(), bytes=target.stat().st_size))
    for idx, name in enumerate(['clean','metrics','report']):
        step = runtime.RunStep(idx, name, skill=name, status='done', depends_on=[idx-1] if idx else [],
            artifacts=[a for a in run.artifacts if a.from_step == idx], code='print("private code")',
            checks=[runtime.ProgrammaticCheck('exists', True)])
        if idx:
            step.input_artifacts = [dict(name=a.name, logical_name=a.logical_name, sha256=a.sha256,
                from_step=a.from_step) for a in run.steps[idx-1].artifacts]
        run.steps.append(step)
    return run


def library():
    return SkillLibrary([Skill(name, name, 'research') for name in ['clean','metrics','report']])


def test_research_oracle_rejects_patient_leakage_and_recomputes_fixed_threshold():
    actual = research.oracle()
    assert actual['cohort_audit'] == dict(raw_rows=14,duplicate_rows=1,cross_split_subjects=1,
        cross_split_rows=2,missing_score_rows=1,eligible_test_rows=6)
    assert actual['heldout_metrics'] == dict(n=6,tp=2,fp=1,tn=2,fn=1,
        accuracy=2/3,precision=2/3,recall=2/3,f1=2/3)
    assert {r['subject_id'] for r in actual['clean_predictions']} == {f'p{i:02}' for i in range(2,12)}


def test_research_credits_only_measured_producers_and_never_claims_network_gain(tmp_path):
    run = make_run(tmp_path)
    run.staged['quality_assessment'] = result = assessment.assess(run, tmp_path, library())
    assert result['scope_verdict'] == 'passed' and result['candidate_eligible']
    assert len(result['independent_reference']['checks']) == 20
    assert [r['observed_score'] for r in result['observations']] == [1,1,None]
    assert result['overall_verdict'] == 'unconfirmed' and not result['network']['applied']
    gates = reward_gates.observation_gates(run, result)
    assert gates['passed'] == 4 and not gates['eligible'] and not gates['reward_applied']


@pytest.mark.parametrize('replacement', ['f1,NaN','f1,inf','f1,1','f1,0.66','f1,0.6666666666666666\nf1,0.6666666666666666'])
def test_reported_metric_or_schema_cannot_replace_independent_reference(tmp_path, replacement):
    run = make_run(tmp_path)
    path = tmp_path/'artifacts/step2_heldout_metrics.csv'
    path.write_text(METRICS.replace('f1,0.6666666666666666',replacement),encoding='utf-8')
    # Even a correctly registered but mathematically wrong file must fail.
    a = run.artifacts[2]
    a.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    a.bytes = path.stat().st_size
    result = assessment.assess(run,tmp_path,library())
    assert result['scope_verdict'] == 'failed' and not result['candidate_eligible']
    assert len(result['independent_reference']['checks']) == 20


def test_same_logical_file_rewritten_later_does_not_credit_original_producer(tmp_path):
    run = make_run(tmp_path)
    source = run.artifacts[2]
    target = tmp_path/'artifacts/step3_heldout_metrics.csv'
    target.write_text(METRICS,encoding='utf-8',newline='\n')
    later = runtime.Artifact(name=target.name,logical_name=source.logical_name,from_step=2,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size)
    run.artifacts.append(later)
    run.steps[2].artifacts.append(later)
    result = assessment.assess(run,tmp_path,library())
    assert result['observations'][1]['observed_score'] is None
    assert result['observations'][2]['observed_score'] == 1


def test_capsule_rehashes_files_is_readonly_and_preserves_exact_lineage(tmp_path):
    run = make_run(tmp_path)
    run.staged['quality_assessment'] = assessment.assess(run,tmp_path,library())
    run.staged['skill_versions'] = {'metrics':{'sha256':'a'*64}}
    run.staged['s1_identity'] = {'secret_scope':'do not export'}
    before = copy.deepcopy(run.to_dict())
    data = evidence.capsule(run,tmp_path)
    assert run.to_dict() == before
    assert data['handoff_ready'] and data['scope_verified']
    assert data['files'][0]['consumed_by'] == [1]
    assert data['chain'][1]['skill_sha256'] == 'a'*64
    assert data['chain'][1]['version_capture'] == 'before_execution'
    assert 'private code' not in json.dumps(data) and 'secret_scope' not in json.dumps(data)
    assert data['reuse']['improvement_proven'] is False and not data['host_product']['production_connection_verified']
    supplied = data.pop('capsule_sha256')
    assert evidence.digest(data) == supplied
    (tmp_path/'artifacts'/run.artifacts[0].name).write_text('tampered',encoding='utf-8')
    data = evidence.capsule(run,tmp_path)
    assert not data['handoff_ready'] and not data['scope_verified']
    assert data['files'][0]['integrity'] == 'failed'


def test_capsule_never_reads_file_outside_registered_workspace(tmp_path):
    run = make_run(tmp_path)
    outside=tmp_path/'outside.txt'
    outside.write_text('secret',encoding='utf-8')
    run.artifacts[0].name = '../outside.txt'
    data = evidence.capsule(run,tmp_path)
    assert data['files'][0]['actual_sha256'] is None
    assert not data['handoff_ready']


def test_capsule_preserves_selection_reasons_and_distinguishes_generic_execution(tmp_path):
    run = make_run(tmp_path)
    run.skills = ['metrics','report']
    run.retrieval = {'fabric':{'selected':['metrics'], 'selection':{'method':'task_utility','library_size':1881},
        'candidates':[{'name':'metrics','note':'计算指标','source':'seed','private_identity':'never export'}]}}
    run.staged['orchestration'] = {'candidate_names':['metrics','report'],
        'decisions':[{'name':'metrics','reason':'固定阈值重算','selected':True}]}
    run.steps[0].skill = 'manual'
    before = copy.deepcopy(run.to_dict())
    result = evidence.capsule(run,tmp_path)['routing']
    assert result['recommended'] == ['metrics']
    assert result['adopted'] == ['metrics','report']
    assert result['generic_steps'] == [0]
    assert 'manual' not in result['entered_execution']
    assert result['decisions'][0]['reason'] == '固定阈值重算'
    assert 'private_identity' not in json.dumps(result)
    assert result['reason_kind'] == 'model_advisory_not_contribution_proof'
    assert run.to_dict() == before


def test_capsule_partial_and_historical_records_do_not_gain_a_quality_claim(tmp_path):
    run = make_run(tmp_path)
    run.status = 'PARTIAL'
    run.steps[2].status = 'skipped'
    data = evidence.capsule(run,tmp_path)
    assert data['handoff_ready'] and not data['scope_verified']
    assert data['status'] == 'PARTIAL' and data['acceptance']['verdict'] == 'unknown'
    assert all(c['version_capture'] == 'unrecorded' for c in data['chain'])
    run.status = 'EXECUTING'
    assert not evidence.capsule(run,tmp_path)['handoff_ready']


def test_s1_evidence_endpoint_checks_service_token_and_signed_project_scope(tmp_path, monkeypatch):
    store = runtime.RunStore(tmp_path/'runs')
    run = make_run(tmp_path/'runs'/'research-evidence-test')
    identity = S1Context('tenant','user','project')
    run.staged['s1_identity'] = identity.to_dict()
    store.save(run)
    monkeypatch.setattr(server,'STATE',{'lib':library(),'run_store':store})
    monkeypatch.setattr(server.config,'OUT_DIR',tmp_path)
    monkeypatch.setattr(server,'ACCESS_TOKEN','test-token')
    monkeypatch.setattr(server,'S1_SIGNING_KEY','s1-test-key')
    path='/api/runs/research-evidence-test/evidence'
    client = TestClient(server.app)
    try:
        assert client.get(path).status_code == 401
        headers=sign('s1-test-key','GET',path,b'',identity)
        assert client.get(path,headers=headers).status_code == 401
        headers['X-SkillNet-Token']='test-token'
        assert client.get(path,headers=headers).json()['handoff_ready']
        other=sign('s1-test-key','GET',path,b'',S1Context('tenant','user','other'))
        other['X-SkillNet-Token']='test-token'
        assert client.get(path,headers=other).status_code == 404
    finally:
        client.close()


@pytest.mark.parametrize('damage',['none','digest','run','nonfinite'])
def test_sdk_validates_evidence_digest_and_run_binding(tmp_path,damage):
    run=make_run(tmp_path)
    data=evidence.capsule(run,tmp_path)
    if damage=='digest':data['task']='changed'
    if damage=='run':
        data['run_id']='other'
        data['capsule_sha256']=evidence.digest({k:v for k,v in data.items() if k!='capsule_sha256'})
    if damage=='nonfinite':data['delivery']['cost_yuan']=float('nan')
    def handler(request):
        assert request.url.path == f'/api/runs/{run.run_id}/evidence'
        return httpx.Response(200,content=json.dumps(data).encode())
    with SkillNetClient(ClientConfig(),transport=httpx.MockTransport(handler)) as client:
        if damage=='none':assert client.get_evidence(run.run_id)['run_id']==run.run_id
        else:
            with pytest.raises(IntegrationError) as error:client.get_evidence(run.run_id)
            assert error.value.code=='digest_mismatch'
