from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading

from fastapi.testclient import TestClient
import pytest

import server
from skillnet import frontier_runtime, frontier_scenarios, runtime
from skillnet.s1_identity import S1Context, sign


TOKEN = 'frontier-test-token'
AUTH = {'X-SkillNet-Token': TOKEN}
S1_KEY = 'frontier-signed-test-key-32-characters'


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'ACCESS_TOKEN', TOKEN)
    monkeypatch.setattr(server, 'S1_SIGNING_KEY', '')
    monkeypatch.setattr(server, '_FRONTIER_SLOTS', threading.BoundedSemaphore(2))
    monkeypatch.setattr(server.config, 'OUT_DIR', tmp_path / 'out')
    monkeypatch.setattr(server, 'ROOT', tmp_path)
    store = runtime.RunStore(tmp_path / 'runs')
    monkeypatch.setattr(server, 'STATE', {'run_store': store})
    client = TestClient(server.app)
    yield client, tmp_path, store
    client.close()


def write_lab(root: Path, **extra):
    report = {'version': 'skillnet-frontier-lab-v1', 'scope': 'test protocol', **extra}
    report['report_sha256'] = frontier_runtime.digest(report)
    path = root / 'docs' / 'evidence' / 'frontier-lab.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
    return path, report


def test_public_scenarios_are_named_choices_with_explicit_boundary(api):
    client, _, _ = api
    response = client.get('/api/frontier/scenarios')
    assert response.status_code == 200
    data = response.json()
    assert data['boundary'] == frontier_runtime.BOUNDARY
    assert {s['id'] for s in data['scenarios']} == {s['id'] for s in frontier_scenarios.scenarios()}
    assert all(set(s) == {'id', 'label', 'description'} for s in data['scenarios'])


def test_real_scenario_is_authenticated_independently_verified_and_cleans_up(api):
    client, root, _ = api
    assert client.post('/api/frontier/execute', json={'scenario_id': 'combined'}).status_code == 401
    response = client.post('/api/frontier/execute', json={'scenario_id': 'combined'}, headers=AUTH)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report['status'] == 'observed_success'
    assert report['scenario_id'] == 'combined'
    assert report['summary']['independently_verified'] is True
    assert report['reward_applied'] is False and report['formal_library_changed'] is False
    assert report['report_sha256'] == frontier_runtime.digest({k: v for k, v in report.items() if k != 'report_sha256'})
    assert str(root) not in response.text
    assert report['trace'] and all(row['execution']['artifacts'] for row in report['trace'])
    assert 'metric,value' in report['trace'][-1]['execution']['artifacts']['metrics']['text']
    assert all('workspace' not in row['execution'] and 'output_path' not in row['execution']
               and 'metrics_path' not in row['execution'] for row in report['trace'])
    assert not list((root / 'out').glob('frontier-api-*'))


@pytest.mark.parametrize('payload', [
    {'scenario_id': 'combined', 'code': 'print(1)'},
    {'scenario_id': 'combined', 'input_path': 'C:/secret.csv'},
    {'scenario_id': 'combined', 'workspace': '../outside'},
    {'scenario_id': 'combined', 'strategy': 'flat'},
    {'scenario_id': '../combined'},
    {'scenario_id': 'combined;echo'},
    {'scenario_id': 'unknown-scenario'},
    {'scenario_id': True}, {'scenario_id': 1}, {}, [],
])
def test_execute_accepts_only_one_known_string_scenario(api, monkeypatch, payload):
    client, root, _ = api
    monkeypatch.setattr(frontier_scenarios, 'run_scenario', lambda *args: pytest.fail('invalid input executed'))
    response = client.post('/api/frontier/execute', json=payload, headers=AUTH)
    assert response.status_code == 422
    assert not (root / 'out').exists()


def test_lab_rejects_absence_and_returns_only_verified_protocol(api):
    client, root, _ = api
    assert client.get('/api/frontier/lab').status_code == 503
    assert client.get('/api/frontier/evidence').status_code == 503
    _, report = write_lab(root, summary={'observed_success': 5},
                          records=[{'large': 'runtime traces'}], basis_records=[{'large': 'basis traces'}],
                          probe_records=[{'large': 'probe traces'}], protocol={'private_to_evidence': True})
    response = client.get('/api/frontier/lab')
    assert response.status_code == 200
    projection = response.json()
    assert set(projection) == {'version', 'scope', 'summary', 'experiments', 'active_probe',
                               'basis', 'protocol_sha256', 'boundary', 'source_report_sha256',
                               'evidence_url', 'report_sha256'}
    assert projection['summary'] == report['summary']
    assert projection['source_report_sha256'] == report['report_sha256']
    assert projection['report_sha256'] != report['report_sha256']
    assert projection['report_sha256'] == frontier_runtime.digest({k: v for k, v in projection.items() if k != 'report_sha256'})
    assert projection['evidence_url'] == '/api/frontier/evidence'
    assert all(key not in projection for key in ('records', 'basis_records', 'probe_records', 'protocol'))
    assert response.headers['cache-control'] == 'no-store'
    complete = client.get(projection['evidence_url'])
    assert complete.status_code == 200 and complete.json() == report
    assert complete.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('damage', ['digest', 'contents', 'old-version', 'missing-digest', 'not-object', 'nonfinite', 'invalid-json'])
@pytest.mark.parametrize('endpoint', ['/api/frontier/lab', '/api/frontier/evidence'])
def test_lab_does_not_serve_corrupt_or_old_experiments(api, damage, endpoint):
    client, root, _ = api
    path, report = write_lab(root, observed_success=5)
    if damage == 'digest':
        report['report_sha256'] = '0' * 64
    elif damage == 'contents':
        report['observed_success'] = 6
    elif damage == 'old-version':
        report['version'] = 'capability-probes-v1'
        report['report_sha256'] = frontier_runtime.digest({k: v for k, v in report.items() if k != 'report_sha256'})
    elif damage == 'missing-digest':
        report.pop('report_sha256')
    elif damage == 'not-object':
        report = []
    elif damage == 'nonfinite':
        report['observed_success'] = float('nan')
    if damage == 'invalid-json':
        path.write_text('{invalid', encoding='utf-8')
    else:
        path.write_text(json.dumps(report), encoding='utf-8')
    response = client.get(endpoint)
    assert response.status_code == 503
    assert 'observed_success' not in response.text
    assert str(root) not in response.text


def test_lab_reads_up_to_32_mib_while_projection_stays_small(api):
    client, root, _ = api
    assert server._FRONTIER_LAB_MAX_BYTES == 32 * 1024 * 1024
    path, _ = write_lab(root, padding='')
    overhead = path.stat().st_size
    path, report = write_lab(root, padding='x' * (server._FRONTIER_LAB_MAX_BYTES - overhead))
    assert path.stat().st_size == server._FRONTIER_LAB_MAX_BYTES
    response = client.get('/api/frontier/lab')
    assert response.status_code == 200
    assert len(response.content) < 2048
    assert response.json()['source_report_sha256'] == report['report_sha256']
    # Whitespace would not change the parsed canonical digest, but the actual
    # byte-read limit must independently reject a file exceeding 32 MiB.
    with path.open('ab') as stream:
        stream.write(b' ')
    for endpoint in ('/api/frontier/lab', '/api/frontier/evidence'):
        assert client.get(endpoint).status_code == 503


def test_two_concurrent_invocations_are_isolated_third_is_rejected_and_slots_release(api, monkeypatch):
    client, root, _ = api
    ready = threading.Event()
    finish = threading.Event()
    lock = threading.Lock()
    folders = []
    def blocked_run(scenario_id, workspace):
        workspace = Path(workspace)
        with lock:
            folders.append(workspace)
            if len(folders) == 2:
                ready.set()
        (workspace / 'local-input.csv').write_text('private to this invocation', encoding='utf-8')
        if not finish.wait(timeout=10):
            raise RuntimeError('test did not release concurrent requests')
        return {'status': 'test-controlled', 'scenario_id': scenario_id}
    monkeypatch.setattr(frontier_scenarios, 'run_scenario', blocked_run)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(client.post, '/api/frontier/execute',
                               json={'scenario_id': 'combined'}, headers=AUTH) for _ in range(2)]
        try:
            assert ready.wait(timeout=5)
            third = client.post('/api/frontier/execute', json={'scenario_id': 'combined'}, headers=AUTH)
            assert third.status_code == 429 and third.headers['retry-after'] == '2'
            assert len(set(folders)) == 2 and all(folder.is_dir() for folder in folders)
        finally:
            finish.set()
        assert all(future.result(timeout=10).status_code == 200 for future in futures)
    assert all(not folder.exists() for folder in folders)
    assert not list((root / 'out').glob('frontier-api-*'))
    assert client.post('/api/frontier/execute', json={'scenario_id': 'combined'}, headers=AUTH).status_code == 200


def test_execution_exception_does_not_leak_paths_or_keep_slot_or_disk_files(api, monkeypatch):
    client, root, _ = api
    def broken(scenario_id, workspace):
        (Path(workspace) / 'created.csv').write_text('retained only until context exit')
        raise RuntimeError(str(workspace / 'secret'))
    monkeypatch.setattr(frontier_scenarios, 'run_scenario', broken)
    for _ in range(3):
        response = client.post('/api/frontier/execute', json={'scenario_id': 'combined'}, headers=AUTH)
        assert response.status_code == 503
        assert str(root) not in response.text and 'secret' not in response.text
    assert not list((root / 'out').glob('frontier-api-*'))
    monkeypatch.setattr(frontier_scenarios, 'run_scenario', lambda *args: {'status': 'test-controlled'})
    assert client.post('/api/frontier/execute', json={'scenario_id': 'combined'}, headers=AUTH).status_code == 200


def test_s1_protects_entire_frontier_prefix_and_signed_body_nonce(api, monkeypatch):
    client, root, _ = api
    monkeypatch.setattr(server, 'S1_SIGNING_KEY', S1_KEY)
    mine = S1Context('tenant-a', 'user-a', 'project-a')
    for path in ('/api/frontier/scenarios', '/api/frontier/lab', '/api/frontier/evidence', '/api/frontier/not-present'):
        assert client.get(path).status_code == 401
    assert client.post('/api/frontier/execute', json={'scenario_id': 'combined'}, headers=AUTH).status_code == 401
    path = '/api/frontier/scenarios'
    headers = sign(S1_KEY, 'GET', path, b'', mine)
    assert client.get(path, headers=headers).status_code == 200
    tampered = dict(headers, **{'X-S1-Tenant': 'tenant-b'})
    assert client.get(path, headers=tampered).status_code == 401
    monkeypatch.setattr(frontier_scenarios, 'run_scenario', lambda *args: {'status': 'test-controlled'})
    path = '/api/frontier/execute'
    body = b'{"scenario_id":"combined"}'
    headers = sign(S1_KEY, 'POST', path, body, mine) | AUTH | {'Content-Type': 'application/json'}
    assert client.post(path, content=body, headers=headers).status_code == 200
    assert client.post(path, content=body, headers=headers).status_code == 409
    changed = b'{"scenario_id":"restored-provider"}'
    assert client.post(path, content=changed, headers=headers).status_code == 401
    # A valid S1 signature still does not replace the separately configured service token.
    fresh = sign(S1_KEY, 'POST', path, body, mine) | {'Content-Type': 'application/json'}
    assert client.post(path, content=body, headers=fresh).status_code == 401
    assert not list((root / 'out').glob('frontier-api-*'))


def test_frontier_route_addition_preserves_existing_run_project_isolation(api, monkeypatch):
    client, _, store = api
    monkeypatch.setattr(server, 'S1_SIGNING_KEY', S1_KEY)
    mine = S1Context('tenant-a', 'user-a', 'project-a')
    other = S1Context('tenant-b', 'user-a', 'project-a')
    run = runtime.Run('frontier-isolation-run', 'private task', 'task-fp')
    run.staged['s1_identity'] = mine.to_dict()
    store.save(run)
    path = '/api/runs/frontier-isolation-run'
    assert client.get(path, headers=sign(S1_KEY, 'GET', path, b'', mine)).status_code == 200
    assert client.get(path, headers=sign(S1_KEY, 'GET', path, b'', other)).status_code == 404
    assert client.get('/api/runs', headers=sign(S1_KEY, 'GET', '/api/runs', b'', other)).json()['total'] == 0


def test_s1_frontier_body_limit_precedes_experiment_execution(api, monkeypatch):
    client, _, _ = api
    monkeypatch.setattr(server, 'S1_SIGNING_KEY', S1_KEY)
    monkeypatch.setattr(frontier_scenarios, 'run_scenario', lambda *args: pytest.fail('oversized body executed'))
    response = client.post('/api/frontier/execute', content=b'x' * 131073, headers=AUTH)
    assert response.status_code == 413
