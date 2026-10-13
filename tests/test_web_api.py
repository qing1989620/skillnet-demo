"""Offline API contracts for network mode and explicit history provenance.

No worker, model, DNS, or provider transport is run. Each queued request and
copied artifact is inspected at the real create_run integration boundary.
"""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
import httpx
from pydantic import ValidationError
import pytest

import server
from skillnet import integration, runtime, web_fetch, web_search


TOKEN = 'web-api-offline-test-token'
AUTH = {'X-SkillNet-Token': TOKEN}


def test_s1_capsule_preserves_reference_only_discovery_without_exporting_remote_body(tmp_path):
    from skillnet.evidence import capsule
    run = runtime.Run(run_id='reference-only-12345678', task='计算给定数据', task_fp='reference', status='COMPLETED')
    run.staged['web_research'] = dict(needed=False, reference_only=True, state='not_needed',
        reason='仅补充方法参考', sources=[], discovery=dict(state='success', candidates=[dict(
            name='online-method', sha256='a'*64, state='quarantined_reference', body='untrusted remote instructions')]))
    result = capsule(run, tmp_path)
    projected = result['web_research']
    assert projected['reference_only'] is True and projected['needed'] is False
    assert projected['reason'] == '仅补充方法参考' and projected['sources'] == []
    assert projected['discovery']['candidates'][0]['sha256'] == 'a'*64
    assert 'body' not in projected['discovery']['candidates'][0]
    assert 'untrusted remote instructions' not in json.dumps(result)


@pytest.fixture
def api(tmp_path, monkeypatch):
    root = tmp_path / 'out'
    store = runtime.RunStore(root / 'runs')
    queued = []
    monkeypatch.setattr(server.config, 'OUT_DIR', root)
    monkeypatch.setattr(server, 'STATE', {'lib': [], 'run_store': store})
    monkeypatch.setattr(server, 'ACCESS_TOKEN', TOKEN)
    monkeypatch.setattr(server, 'S1_SIGNING_KEY', '')
    monkeypatch.setattr(server, 'WORKER_MODE', 'external')
    monkeypatch.setattr(server, '_RUN_THREADS', {})
    monkeypatch.setattr(server, 'require_llm', lambda: None)
    monkeypatch.setattr(server, 'job_queue', lambda: SimpleNamespace(enqueue=lambda rid, payload: queued.append((rid, payload))))
    monkeypatch.setattr(server, '_bounded_run_worker', lambda *_: pytest.fail('worker must never run'))
    monkeypatch.setattr(web_search, 'search', lambda *_a, **_k: pytest.fail('provider must never run'))
    monkeypatch.setattr(web_search, 'extract', lambda *_a, **_k: pytest.fail('extractor must never run'))
    monkeypatch.setattr(web_fetch, 'fetch_url', lambda *_a, **_k: pytest.fail('source fetch must never run'))
    monkeypatch.setattr(web_fetch.socket, 'getaddrinfo', lambda *_a, **_k: pytest.fail('DNS must never run'))
    with TestClient(server.app) as client:
        yield client, root, store, queued


def previous_run(root, store):
    run = runtime.Run(run_id='previous-run-12345678', task='上一轮只分析本地给定数据', task_fp='previous', status='COMPLETED')
    directory = root / 'runs' / run.run_id / 'artifacts'
    directory.mkdir(parents=True)
    for index, body in enumerate((b'value\n1\n', b'value\n2\n'), 1):
        name = f'step{index}_data.csv'
        (directory / name).write_bytes(body)
        run.artifacts.append(runtime.Artifact(name=name, logical_name='data.csv', kind='csv',
            bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), from_step=index-1, version=index))
    store.save(run)
    return run


@pytest.mark.parametrize('model', [server.RunReq, integration.RunInput])
def test_network_mode_defaults_to_auto(model):
    assert model(task='public research').web_mode == 'auto'


@pytest.mark.parametrize('model', [server.RunReq, integration.RunInput])
@pytest.mark.parametrize('mode', ['auto', 'on', 'off'])
def test_network_mode_enum_is_serialized(model, mode):
    assert model(task='public research', web_mode=mode).model_dump()['web_mode'] == mode


@pytest.mark.parametrize('model', [server.RunReq, integration.RunInput])
@pytest.mark.parametrize('mode', [None, True, False, 1, 'ON', 'enabled', '', 'auto,on'])
def test_invalid_network_mode_rejected_before_worker(model, mode):
    with pytest.raises(ValidationError):
        model(task='public research', web_mode=mode)


@pytest.mark.parametrize('mode', ['auto', 'on', 'off'])
def test_create_api_queues_selected_network_mode(api, mode):
    client, _root, store, queued = api
    response = client.post('/api/runs', json={'task':'public research', 'web_mode':mode}, headers=AUTH)
    assert response.status_code == 200, response.text
    rid = response.json()['run_id']
    assert queued == [(rid, server.RunReq(task='public research', web_mode=mode).model_dump())]
    assert store.get(rid).status == runtime.STATUS_CREATED
    assert not server._RUN_THREADS


def test_create_api_defaults_and_rejects_invalid_mode_without_queue(api):
    client, _root, _store, queued = api
    response = client.post('/api/runs', json={'task':'public research'}, headers=AUTH)
    assert response.status_code == 200
    assert queued[-1][1]['web_mode'] == 'auto'
    before = len(queued)
    response = client.post('/api/runs', json={'task':'public research', 'web_mode':'always'}, headers=AUTH)
    assert response.status_code == 422
    assert len(queued) == before


@pytest.mark.parametrize('configured', [False, True])
def test_capabilities_are_configuration_only_and_never_reveal_key(api, monkeypatch, configured):
    client, _root, _store, queued = api
    secret = 'tavily-private-credential-must-not-leak'
    if configured:
        monkeypatch.setenv('TAVILY_API_KEY', secret)
    else:
        monkeypatch.delenv('TAVILY_API_KEY', raising=False)
    monkeypatch.setenv('SKILLNET_WEB_ENABLED', '1')
    response = client.get('/api/web/capabilities')
    assert response.status_code == 200
    data = response.json()
    assert data['availability'] == 'unprobed'
    assert data['key_configured'] is configured
    assert data['keyless'] is not configured
    assert data['source_verification_required'] is True
    assert secret not in response.text
    assert not queued


def test_new_topic_never_implicitly_copies_prior_artifact(api):
    client, root, store, queued = api
    previous = previous_run(root, store)
    response = client.post('/api/runs', json={'task':'介绍张例明的著作和机构', 'history':[
        {'q':previous.task, 'a':'先前完成了本地数据表', 'run_id':previous.run_id}]}, headers=AUTH)
    assert response.status_code == 200, response.text
    current = store.get(response.json()['run_id'])
    assert current.artifacts == []
    assert current.staged['history_artifacts'] == []
    assert queued[-1][1]['artifact_refs'] == []
    assert not (root / 'runs' / current.run_id / 'artifacts').exists()
    assert len(previous.artifacts) == 2


def test_explicit_previous_data_reference_copies_latest_sha_version(api):
    client, root, store, queued = api
    previous = previous_run(root, store)
    latest = previous.artifacts[-1]
    response = client.post('/api/runs', json={'task':'基于上一轮数据继续计算均值', 'history':[
        {'q':previous.task, 'a':'已有 data.csv', 'run_id':previous.run_id}]}, headers=AUTH)
    assert response.status_code == 200, response.text
    current = store.get(response.json()['run_id'])
    assert len(current.artifacts) == 1
    copied = current.artifacts[0]
    assert copied.kind == '跨轮输入'
    assert copied.source_run_id == previous.run_id
    assert copied.logical_name == 'data.csv'
    assert copied.version == 2
    assert copied.sha256 == latest.sha256
    raw = (root / 'runs' / current.run_id / 'artifacts' / copied.name).read_bytes()
    assert raw == b'value\n2\n'
    assert hashlib.sha256(raw).hexdigest() == latest.sha256
    expected = {'run_id':previous.run_id, 'name':latest.name, 'sha256':latest.sha256}
    assert current.staged['history_artifacts'] == [expected]
    assert queued[-1][1]['artifact_refs'] == [expected]


def test_explicit_artifact_reference_is_respected_even_for_new_topic(api):
    client, root, store, queued = api
    previous = previous_run(root, store)
    old = previous.artifacts[0]
    reference = {'run_id':previous.run_id, 'name':old.name, 'sha256':old.sha256}
    response = client.post('/api/runs', json={'task':'为本次独立实验绘制指定数据', 'artifact_refs':[reference],
        'history':[{'q':previous.task, 'run_id':previous.run_id}]}, headers=AUTH)
    assert response.status_code == 200, response.text
    current = store.get(response.json()['run_id'])
    assert len(current.artifacts) == 1
    copied = current.artifacts[0]
    assert copied.version == 1
    assert copied.sha256 == old.sha256
    assert copied.source_run_id == previous.run_id
    assert (root / 'runs' / current.run_id / 'artifacts' / copied.name).read_bytes() == b'value\n1\n'
    assert queued[-1][1]['artifact_refs'] == [reference]


def test_original_inputs_survive_multiple_followups_and_latest_output_wins(api):
    client, root, store, _queued = api
    previous = previous_run(root, store)
    history = [{'q':previous.task, 'run_id':previous.run_id}]
    names = []
    for index in range(5):
        response = client.post('/api/runs', json={'task':'继续读取上一轮的 data.csv',
            'history':history}, headers=AUTH)
        assert response.status_code == 200, response.text
        current = store.get(response.json()['run_id'])
        assert len(current.artifacts) == 1
        copied = current.artifacts[0]
        assert copied.logical_name == 'data.csv' and copied.version == 2
        assert copied.sha256 == previous.artifacts[-1].sha256
        names.append(copied.name)
        downloaded = client.get(f'/api/runs/{current.run_id}/artifacts/{copied.name}', headers=AUTH)
        assert downloaded.status_code == 200 and downloaded.content == b'value\n2\n'
        history.append({'q':current.task, 'run_id':current.run_id})
    assert max(map(len, names)) == min(map(len, names))
    # An updated output with the same logical name replaces its inherited version.
    data = b'value\n3\n'
    name = 'step1_data.csv'
    (root/'runs'/current.run_id/'artifacts'/name).write_bytes(data)
    current.artifacts.append(runtime.Artifact(name=name, logical_name='data.csv', kind='csv',
        bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),from_step=0,version=3))
    store.save(current)
    response = client.post('/api/runs',json={'task':'继续读取上一轮的 data.csv','history':history},headers=AUTH)
    final = store.get(response.json()['run_id'])
    assert len(final.artifacts) == 1 and final.artifacts[0].version == 3
    assert (root/'runs'/final.run_id/'artifacts'/final.artifacts[0].name).read_bytes() == data


def test_failed_latest_turn_does_not_hide_earlier_explicit_context_files(api):
    client, root, store, _queued = api
    previous = previous_run(root, store)
    failed = runtime.Run(run_id='failed-turn-12345678',task='上一轮排版失败',task_fp='failed',status='FAILED')
    store.save(failed)
    response = client.post('/api/runs',json={'task':'继续使用上一轮数据','history':[
        {'q':previous.task,'run_id':previous.run_id},{'q':failed.task,'run_id':failed.run_id}]},headers=AUTH)
    assert response.status_code == 200, response.text
    current = store.get(response.json()['run_id'])
    assert len(current.artifacts) == 1
    assert current.artifacts[0].sha256 == previous.artifacts[-1].sha256


def test_modified_inherited_file_is_rejected_before_another_job_is_queued(api):
    client, root, store, queued = api
    previous = previous_run(root, store)
    response = client.post('/api/runs',json={'task':'继续使用上一轮数据','history':[
        {'q':previous.task,'run_id':previous.run_id}]},headers=AUTH)
    inherited = store.get(response.json()['run_id'])
    (root/'runs'/inherited.run_id/'artifacts'/inherited.artifacts[0].name).write_bytes(b'tampered')
    before = len(queued)
    response = client.post('/api/runs',json={'task':'继续使用上一轮数据','history':[
        {'q':inherited.task,'run_id':inherited.run_id}]},headers=AUTH)
    assert response.status_code == 409 and len(queued) == before


def test_explicit_stale_sha_never_copies_or_enqueues(api):
    client, root, store, queued = api
    previous = previous_run(root, store)
    response = client.post('/api/runs', json={'task':'new topic', 'artifact_refs':[
        {'run_id':previous.run_id, 'name':previous.artifacts[0].name, 'sha256':'0'*64}]}, headers=AUTH)
    assert response.status_code == 409
    assert not queued
    assert store.list_recent()[0]['run_id'] == previous.run_id


@pytest.mark.parametrize('mode', ['auto', 'on', 'off'])
def test_integration_client_preserves_network_mode_in_real_request(mode):
    captured = []
    def handle(request):
        captured.append(json.loads(request.content))
        assert request.url.path == '/api/runs'
        return httpx.Response(200, json={'run_id':'created-run', 'status':'CREATED'})
    with integration.SkillNetClient(integration.ClientConfig(), transport=httpx.MockTransport(handle)) as client:
        assert client.create_run('public research', web_mode=mode)['run_id'] == 'created-run'
    assert captured[0]['web_mode'] == mode
