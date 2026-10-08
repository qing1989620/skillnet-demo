"""Regression tests for failures observed in the full-product audit."""
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace

import httpx
import pytest

from skillnet import checks, executor, llm, pipeline, runtime
from skillnet.catalog import SkillLibrary
from skillnet.governance import quarantine, promote
from skillnet.jobs import JobQueue
from skillnet.schema import Skill
from skillnet.scenarios import scenarios, oracle
from skillnet.s1_identity import S1Context, S1Auth, sign, verify

ROOT = Path(__file__).resolve().parents[1]


def test_planner_observes_csv_without_inventing_cleaned_counts():
    from skillnet.contracts import planning_data_facts
    facts = planning_data_facts(scenarios()[0]['task'])
    assert facts['rows'] == 15
    assert facts['exact_duplicate_rows'] == 1
    assert facts['missing_cells'] == dict(order_id=0, month=0, revenue=1, cost=1)
    assert 'cleaned_rows' not in facts
    assert planning_data_facts('CSV：\na,b\n1,2,3') == {}
    assert planning_data_facts('These words merely mention CSV') == {}


def test_community_packages_are_real_unique_attributed_skills():
    rows = json.loads((ROOT/'seed/community/catalog.json').read_text(encoding='utf-8'))
    assert len(rows) >= 1000
    assert len({r['metadata']['body_sha256'] for r in rows}) == len(rows)
    assert len({r['name'] for r in rows}) == len(rows)
    for row in rows:
        skill = Skill.from_dict(row)
        assert not skill.validate()
        assert int(skill.metadata['stars']) >= 1000
        assert skill.metadata['execution_verified'] == 'false'
        raw=(ROOT/skill.metadata['package_path']/'SKILL.md').read_bytes()
        assert hashlib.sha256(raw).hexdigest() == skill.metadata['content_sha256']
        assert len(skill.reference_body()) > 200


def test_community_is_not_counted_or_persisted_as_evolution(tmp_path):
    community = Skill('community','reference','data',source='github')
    evolved = Skill('learned','method','data',source='distill',generation=1)
    library = SkillLibrary([community,evolved])
    assert library.stats()['evolved'] == 1
    assert library.stats()['community'] == 1
    path=tmp_path/'library.json';library.save(path)
    assert [s['name'] for s in json.loads(path.read_text())['evolved']] == ['learned']


def test_step_dataflow_overrides_same_skill_graph_root():
    steps=pipeline.build_steps({'steps':[
        {'skill':'stats','action':'write summary.csv','output_files':['summary.csv']},
        {'skill':'stats','action':'read summary.csv and check it','input_files':['summary.csv']},
        {'skill':'plot','action':'plot summary.csv','input_files':['summary.csv']} ]},[['stats','plot']])
    assert steps[1].depends_on == [0]
    assert 0 in steps[2].depends_on
    assert '真实文件' in steps[1].dependency_reason or '连续' in steps[1].dependency_reason


def test_explicit_step_contract_preserves_parallel_roots():
    steps=pipeline.build_steps({'steps':[{'action':'a','depends_on':[]},{'action':'b','depends_on':[]},
        {'action':'merge','depends_on':[0,1]}]})
    assert [s.depends_on for s in steps] == [[],[],[0,1]]
    with pytest.raises(ValueError):
        pipeline.build_steps({'steps':[{'action':'bad','depends_on':[1]}]})


def test_verifier_sees_complete_code_and_actual_csv_and_abstains(monkeypatch,tmp_path):
    csvfile=tmp_path/'summary.csv';csvfile.write_text('group,mean\nA,3\n',encoding='utf-8')
    captured=[]
    def judge(messages,**kwargs):
        captured.append(messages[-1]['content'])
        return {'checks':[{'item':'tail saved','passed':'false','evidence':'ambiguous'}]}
    monkeypatch.setattr(llm,'chat_json',judge)
    skill=Skill('test','test','test',verification=['tail saved','actual numbers'])
    results=executor._verify_with_skill(skill,'task','summarize','# x\n'*2000+'tail_saved=True','',['summary.csv'],artifact_paths=[csvfile])
    assert 'tail_saved=True' in captured[0]
    assert '"mean": "3"' in captured[0]
    assert len(results)==2
    assert all(r['state']=='unknown' and not r['passed'] for r in results)


def test_missing_artifact_type_cannot_silently_pass_assertion():
    result=checks.checks_from_skill(['[csv_columns] month,revenue'],[])
    assert result and not result[0]['passed']


def test_acceptance_failure_enters_repair_and_records_diff(monkeypatch,tmp_path):
    library=SkillLibrary([Skill('csv-job','write csv','data',verification=['[csv_columns] value'])])
    code=iter(["from pathlib import Path\nPath('data.csv').write_text('wrong\\n1\\n')\nprint('initial')",
               "from pathlib import Path\nPath('data.csv').write_text('value\\n1\\n')\nprint('repaired')"])
    monkeypatch.setattr(llm,'chat',lambda *a,**k:next(code))
    monkeypatch.setattr(executor,'_record_execution',lambda *a:None)
    run=runtime.Run(runtime.new_run_id('fix'),'write data','fix')
    with llm.ledger_scope(llm.UsageLedger()):
        pipeline.execute_run(run,library,tmp_path,{'steps':[{'skill':'csv-job','action':'write csv'}]},max_steps=1)
    step=run.steps[0]
    assert len(step.attempts)==2
    assert step.attempts[0].ok and step.attempts[0].acceptance['state']=='failed'
    assert 'wrong' in step.attempts[1].code_diff and 'value' in step.attempts[1].code_diff
    assert step.attempts[1].repair_reason
    assert all(c.passed for c in step.checks if c.required)


def test_durable_queue_claim_cancel_and_lost_worker_recovery(tmp_path):
    q=JobQueue(tmp_path/'jobs.db');q.enqueue('run-a',{'task':'a'})
    job=q.claim('worker-a',lease_seconds=-1)
    assert job['id']=='run-a' and JobQueue(q.path).claim('worker-b') is None
    assert q.recover()==['run-a']
    assert q.snapshot()['interrupted']==1
    q.enqueue('run-b',{'task':'b'});q.cancel('run-b')
    assert q.cancelled('run-b') and q.claim('worker-c') is None


def test_signed_identity_covers_body_user_project_and_expiry():
    key='x'*32;context=S1Context('tenant-a','user-a','project-a')
    headers=sign(key,'POST','/api/runs',b'{}',context)
    assert verify(key,'POST','/api/runs',b'{}',headers)==context
    for body,modified in [(b'{"task":"different"}',headers),(b'{}',headers|{'X-S1-Project':'other'}),
                          (b'{}',sign(key,'POST','/api/runs',b'{}',context,timestamp=1))]:
        with pytest.raises(ValueError):verify(key,'POST','/api/runs',body,modified)


def test_httpx_identity_signs_the_actual_serialized_request():
    key='y'*32;context=S1Context('tenant','user','project')
    def handler(request):
        assert verify(key,request.method,request.url.path,request.content,request.headers)==context
        return httpx.Response(200,json={'ok':True})
    with httpx.Client(transport=httpx.MockTransport(handler),auth=S1Auth(context,key)) as client:
        assert client.post('https://example.org/api/runs',json={'task':'中文'}).status_code==200


def test_candidate_is_quarantined_and_zero_gain_cannot_promote(tmp_path):
    skill=Skill('candidate','new method','data',steps=['a','b','c'])
    record=quarantine(skill,tmp_path)
    candidate=tmp_path/'candidate.json'
    report=tmp_path/'report.json';report.write_text(json.dumps(dict(candidate_sha256=record['sha256'],
        evaluation_kind='paired-real-execution',pairs=[dict(task_sha256=str(i%2),frozen=True,
        before_run_id='before'+str(i),after_run_id='after'+str(i),before=1.,after=1.) for i in range(4)])))
    with pytest.raises(ValueError,match='No measured improvement'):
        promote(candidate,report,SkillLibrary([]))
    assert json.loads(candidate.read_text())['state']=='candidate'


def test_frozen_business_cases_have_independent_correct_totals():
    for case in scenarios():
        values=oracle(case)
        for key in ('orders','revenue','cost'):
            assert sum(v[key] for v in values.values()) == case['expected'][key]
        assert case['frozen'] and len(case['task_sha256'])==64


def test_nonce_replay_is_durably_rejected(tmp_path):
    queue=JobQueue(tmp_path/'jobs.db')
    assert queue.consume_nonce('nonce-a')
    assert not JobQueue(queue.path).consume_nonce('nonce-a')


def test_s1_scope_and_queued_cancel_without_model_calls(monkeypatch,tmp_path):
    import server
    from fastapi.testclient import TestClient
    monkeypatch.setattr(server,'S1_SIGNING_KEY','z'*32)
    monkeypatch.setattr(server,'ACCESS_TOKEN','')
    monkeypatch.setattr(server,'WORKER_MODE','external')
    monkeypatch.setenv('SKILLNET_WORKER_MODE','external')
    monkeypatch.setattr(server.config,'OUT_DIR',tmp_path)
    monkeypatch.setattr(server.config,'API_KEY','test-local-only')
    monkeypatch.setattr(server,'STATE',{})
    mine=S1Context('tenant','user','project');other=S1Context('tenant','other','project')
    def headers(method,path,body=b'',context=mine):return sign('z'*32,method,path,body,context)
    client=TestClient(server.app)
    body=b'{"task":"make a csv","max_steps":1}'
    h=headers('POST','/api/runs',body)|{'Content-Type':'application/json'}
    response=client.post('/api/runs',content=body,headers=h)
    assert response.status_code==200,response.text
    rid=response.json()['run_id'];path='/api/runs/'+rid
    assert client.post('/api/runs',content=body,headers=h).status_code==409
    assert client.get(path,headers=headers('GET',path,context=other)).status_code==404
    assert client.get('/api/runs',headers=headers('GET','/api/runs',context=other)).json()['total']==0
    cancel=path+'/cancel'
    assert client.post(cancel,headers=headers('POST',cancel)).status_code==200
    stored=client.get(path,headers=headers('GET',path)).json()
    assert stored['status']=='CANCELLED' and stored['llm_calls']==0
    # Real physical artifact version crosses a signed API request and is read by the next step.
    prior=runtime.Run('prior-run','first question','prior')
    prior.staged['s1_identity']=mine.to_dict();prior.status='COMPLETED'
    folder=tmp_path/'runs/prior-run/artifacts';folder.mkdir(parents=True)
    raw=b'month,revenue\n2026-01,10\n'
    (folder/'step1_monthly_summary.csv').write_bytes(raw)
    sha=hashlib.sha256(raw).hexdigest()
    prior.artifacts=[runtime.Artifact(name='step1_monthly_summary.csv',sha256=sha,bytes=len(raw),logical_name='monthly_summary.csv')]
    server.run_store().save(prior)
    payload=json.dumps({'task':'read previous file','max_steps':1,'artifact_refs':[
        dict(run_id='prior-run',name='step1_monthly_summary.csv',sha256=sha)]}).encode()
    response=client.post('/api/runs',content=payload,headers=headers('POST','/api/runs',payload)|{'Content-Type':'application/json'})
    assert response.status_code==200,response.text
    follow=server.run_store().load(response.json()['run_id'])
    assert follow.artifacts[0].sha256==sha and follow.artifacts[0].source_run_id=='prior-run'
    monkeypatch.setattr(llm,'chat',lambda *a,**k:"from pathlib import Path\ns=Path('monthly_summary.csv').read_bytes()\nPath('risk.csv').write_bytes(s)\nprint('copied actual previous version')")
    monkeypatch.setattr(executor,'_record_execution',lambda *a:None)
    workspace=tmp_path/'runs'/follow.run_id
    with llm.ledger_scope(llm.UsageLedger()):
        pipeline.execute_run(follow,None,workspace,{'steps':[dict(action='read previous file',input_files=['monthly_summary.csv'],output_files=['risk.csv'])]},max_steps=1)
    assert (workspace/'artifacts/step1_risk.csv').read_bytes()==raw
    assert 'monthly_summary.csv' in follow.steps[0].inputs


def test_malformed_summary_keeps_oracle_denominator(tmp_path):
    from skillnet.scenarios import evaluate_artifacts
    case=scenarios()[0]
    run=runtime.Run('test-oracle','test','test')
    result=evaluate_artifacts(case,run,tmp_path)
    assert len(result['checks'])==3+5*len(oracle(case))
    assert result['score']==0


def test_range_rejects_nan_and_infinity(tmp_path):
    path=tmp_path/'values.csv';path.write_text('score\nnan\ninf\n')
    assert not checks.check_numeric_ranges(path,{'score':(0,1)})[0][1]


def test_community_reference_enters_executor_and_framework_export(tmp_path):
    from skillnet.adapters import export_agent_skills
    rows=json.loads((ROOT/'seed/community/catalog.json').read_text(encoding='utf-8'))
    skill=next(Skill.from_dict(r) for r in rows if int(r['metadata']['resource_count'])>1)
    from skillnet.contracts import scoped_skill
    scoped=scoped_skill(skill,runtime.RunStep(idx=0,action='use reference'))
    assert skill.reference_body()[:100] in executor._skill_brief(scoped)
    export_agent_skills(SkillLibrary([skill]),tmp_path,targets={'test':'skills'})
    exported=tmp_path/'agent_skills/skills'/skill.name
    original=ROOT/skill.metadata['package_path']
    assert {p.relative_to(original) for p in original.rglob('*') if p.is_file()} <= {p.relative_to(exported) for p in exported.rglob('*') if p.is_file()}


def test_docker_requested_without_runtime_never_falls_back(monkeypatch,tmp_path):
    from skillnet import sandbox
    monkeypatch.setenv('SKILLNET_SANDBOX','docker')
    monkeypatch.setattr(sandbox.shutil,'which',lambda name:None)
    with pytest.raises(RuntimeError,match='拒绝降级'):
        sandbox.run_python("from pathlib import Path;Path('ran.txt').write_text('ran')",workdir=tmp_path)
    assert not (tmp_path/'ran.txt').exists()


def test_same_candidate_is_idempotent_and_different_origins_are_separate(tmp_path):
    skill=Skill('new-candidate','new method','data',steps=['a','b','c'])
    quarantine(skill,tmp_path,origin_run_id='run-a')
    quarantine(skill,tmp_path,origin_run_id='run-a')
    quarantine(skill,tmp_path,origin_run_id='run-b')
    assert len(list(tmp_path.glob('*.json')))==2
