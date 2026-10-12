"""Offline tests for bounded online reference acquisition; no live API/LLM calls."""
import base64
import hashlib
import json

import httpx
import pytest

from skillnet import skill_discovery as discovery


COMMIT = 'a' * 40
SKILL = (b'---\r\nname: source-check\r\ndescription: "Verify public sources with evidence."\r\n'
         b'license: MIT\r\n---\r\n# Source check\r\nRead sources and keep uncertain findings separate.\r\n')
LICENSE = b'MIT License\nCopyright Example Authors\nPermission is hereby granted, free of charge.\n'
URL = 'https://github.com/example/research/blob/main/skills/source-check/SKILL.md'


def file_record(raw, path):
    return dict(type='file', path=path, encoding='base64', size=len(raw),
                content=base64.b64encode(raw).decode(),
                sha=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest())


@pytest.fixture
def acquisition(monkeypatch):
    original = httpx.Client
    calls, options, searches = [], [], []
    search_output = dict(state='success', results=[{'url': URL}], attempts=[{
        'provider': 'tavily', 'state': 'success', 'reason': 'live_provider_response', 'status_code': 200}])

    def search(query, **kwargs):
        searches.append((query, kwargs))
        return search_output

    def standard(request):
        if request.url.path.endswith('/commits/main'):
            return httpx.Response(200, json={'sha': COMMIT})
        if request.url.path.endswith('/license'):
            body = file_record(LICENSE, 'LICENSE')
            body['license'] = {'spdx_id': 'MIT'}
            return httpx.Response(200, json=body)
        if '/contents/' in request.url.path:
            return httpx.Response(200, json=file_record(SKILL, 'skills/source-check/SKILL.md'))
        return httpx.Response(200, json={'private': False, 'stargazers_count': 4567,
                                        'license': {'spdx_id': 'MIT'}})

    def install(handler=None):
        handler = handler or standard

        def client(**kwargs):
            options.append(kwargs.copy())
            assert kwargs['trust_env'] is False and kwargs['follow_redirects'] is False
            assert isinstance(kwargs.pop('transport'), discovery._PinnedGitHubTransport)
            assert 0 < kwargs['timeout'] <= 60

            def wrapped(request):
                calls.append(request)
                assert request.method == 'GET' and request.url.host == 'api.github.com'
                assert 'authorization' not in request.headers
                return handler(request)

            return original(transport=httpx.MockTransport(wrapped), **kwargs)

        monkeypatch.setattr(discovery.httpx, 'Client', client)
        return calls, options, searches, search_output, standard

    monkeypatch.setattr(discovery.web_search, 'search', search)
    return install


def test_pin_exact_bytes_license_and_quarantine_without_execution(acquisition, tmp_path):
    calls, _, searches, _, _ = acquisition()
    report = discovery.discover('identity source citation research', limit=2)
    assert report['state'] == 'success' and len(report['candidates']) == 1
    candidate = report['candidates'][0]
    assert candidate['body'].encode('utf-8') == SKILL
    assert candidate['sha256'] == hashlib.sha256(SKILL).hexdigest()
    assert candidate['content_sha256'] == candidate['sha256']
    assert candidate['license_sha256'] == hashlib.sha256(LICENSE).hexdigest()
    assert candidate['source_url'] == URL.replace('/main/', '/' + COMMIT + '/')
    assert candidate['commit'] == COMMIT and candidate['stars'] == 4567
    assert candidate['repo'] == candidate['repository'] == 'example/research'
    assert candidate['license'] == 'MIT' and candidate['state'] == 'quarantined_reference'
    assert candidate['source'] == 'online_reference' and candidate['read_only']
    assert not candidate['execution_verified'] and not candidate['instructions_trusted']
    assert not report['installed'] and not report['executed'] and not report['formal_library_changed']
    assert 1 <= len(candidate['name']) <= 64
    assert len(calls) == 4 and report['github_requests'] == 4
    assert all(request.url.params.get('ref') == COMMIT for request in calls[-2:])
    assert searches[0][1] == {'limit': 6, 'kind': 'web', 'timeout': 6}
    assert list(tmp_path.iterdir()) == []


def test_discovery_queries_never_export_names_user_text_urls_or_credentials(acquisition):
    _, _, searches, _, _ = acquisition()
    private = '张例明 secret=sk-private-key C:/Users/qing/payroll.csv https://internal.invalid user@example.org'
    report = discovery.discover(private + ' 核验引用')
    expected = 'site:github.com "SKILL.md" citation verification source verification'
    assert searches[0][0] == expected and report['query'] == expected
    assert all(value not in json.dumps(report, ensure_ascii=False) for value in [
        '张例明', 'sk-private-key', 'payroll.csv', 'internal.invalid', 'user@example.org'])


@pytest.mark.parametrize('task,expected', [
    ('identity source citation research', 'identity verification citation verification source verification web research'),
    ('前端 React 界面和交互优化', 'frontend development'),
    ('frontend development with Vue and accessible CSS', 'frontend development'),
    ('后端 FastAPI 服务端接口优化', 'backend development'),
    ('backend development using Django REST API', 'backend development'),
    ('数据统计分析和可视化图表', 'data analysis data visualization'),
    ('data visualization using matplotlib', 'data analysis data visualization'),
    ('用 FreeCAD 做 CAD 机械设计和工程制图', 'CAD design'),
    ('设计 Fusion 360 装配模型', 'CAD design'),
    ('前端数据可视化 React 看板', 'data analysis frontend development data visualization'),
    ('无匹配能力的普通请求', 'web research source verification'),
])
def test_capability_terms_use_stable_public_labels_and_domain_specific_queries(task, expected):
    assert discovery.capability_terms(task) == expected
    assert discovery._query(task) == 'site:github.com "SKILL.md" ' + expected


def test_capability_terms_never_return_private_raw_content():
    private = ('张例明的内部项目ProjectZeta，api_key=sk-private-credential '
        'C:/Users/qing/payroll.csv https://internal.invalid/private user@example.org；'
        '员工薪酬=123456、账号987654；优化前端可视化界面')
    terms = discovery.capability_terms(private)
    assert terms == 'frontend development data visualization'
    assert all(value not in terms for value in [
        '张例明', 'ProjectZeta', 'sk-private', 'payroll.csv', 'internal.invalid',
        'user@example.org', '123456', '987654'])
    assert set(terms.split()) <= set(' '.join(label for label, _ in discovery._CAPABILITIES).split())


@pytest.mark.parametrize('task,expected', [
    ('制作可视化图表', 'data visualization'),
    ('前端 后端 渲染 CAD', 'frontend development backend development data visualization CAD design'),
    ('无匹配能力的普通请求', 'web research source verification'),
])
def test_public_capability_terms_are_idempotent_without_gaining_or_dropping_labels(task, expected):
    terms = discovery.capability_terms(task)
    assert terms == expected
    assert discovery.capability_terms(terms) == terms
    assert discovery.capability_terms(discovery.capability_terms(terms)) == terms
    assert discovery._query(terms) == discovery._query(task)


def test_canonical_terms_detection_never_passes_through_non_whitelisted_text():
    raw = 'frontend development private-project-Zeta https://internal.invalid token=private-credential'
    terms = discovery.capability_terms(raw)
    assert terms == 'frontend development' and terms != raw
    assert discovery._PUBLIC_TERMS.fullmatch(raw) is None
    assert discovery._PUBLIC_TERMS.fullmatch(terms)


@pytest.mark.parametrize('task,expected', [
    ('优化前端 React 界面', 'frontend development'),
    ('改进数据统计分析和图表可视化', 'data analysis data visualization'),
    ('优化后端 FastAPI 接口', 'backend development'),
    ('CAD 机械设计', 'CAD design'),
])
def test_discover_sends_capability_query_instead_of_unrelated_citation_terms(acquisition, task, expected):
    _, _, searches, _, _ = acquisition()
    report = discovery.discover(task)
    assert searches[0][0] == 'site:github.com "SKILL.md" ' + expected
    assert report['query'] == searches[0][0]
    assert 'citation' not in searches[0][0]


@pytest.mark.parametrize('url', [
    'http://github.com/example/research/blob/main/SKILL.md',
    'https://github.com.evil.org/example/research/blob/main/SKILL.md',
    'https://github.com@127.0.0.1/example/research/blob/main/SKILL.md',
    'https://github.com:443/example/research/blob/main/SKILL.md',
    'https://github.com/example/research',
    'https://github.com/example/research/tree/main/skills',
    'https://raw.githubusercontent.com/example/research/main/SKILL.md',
    'https://github.com/example/research/blob/main/%2e%2e/SKILL.md',
    'https://github.com/example/research/blob/main/a%2fb/SKILL.md',
    'https://github.com/example/research/blob/main/SKILL.md?token=secret',
    'https://github.com/example/research/blob/main/SKILL.md#instructions',
    'https://github.com/example/research/blob/main/main.py',
])
def test_unsafe_or_unsupported_result_urls_do_not_trigger_fetch(acquisition, url):
    calls, _, _, search, _ = acquisition()
    search['results'] = [{'url': url}]
    report = discovery.discover('source verification')
    assert report['state'] == 'empty' and report['candidates'] == [] and calls == []
    assert report['attempts'][-1]['reason'] == 'explicit_github_skill_blob_url_required'


@pytest.mark.parametrize('license_id', [None, 'NOASSERTION', 'GPL-3.0', 'proprietary'])
def test_unknown_or_disallowed_license_never_becomes_candidate(acquisition, license_id):
    calls, _, _, _, _ = acquisition(lambda request: httpx.Response(200, json={
        'private': False, 'stargazers_count': 90000, 'license': {'spdx_id': license_id}}))
    report = discovery.discover('research')
    assert report['state'] == 'unavailable' and report['candidates'] == []
    assert len(calls) == 1


def test_pinned_license_must_match_detected_repository_license(acquisition):
    calls, _, _, _, standard = acquisition()

    def handler(request):
        if request.url.path.endswith('/license'):
            body = file_record(LICENSE, 'LICENSE')
            body['license'] = {'spdx_id': 'NOASSERTION'}
            return httpx.Response(200, json=body)
        return standard(request)

    acquisition(handler)
    report = discovery.discover('research')
    assert report['candidates'] == [] and len(calls) == 3
    assert report['attempts'][-1]['reason'] == 'pinned_license_unconfirmed'


@pytest.mark.parametrize('status,headers,state', [
    (429, {}, 'rate_limited'), (403, {'X-RateLimit-Remaining': '0'}, 'rate_limited'),
    (403, {}, 'access_denied'), (404, {}, 'unavailable'),
    (302, {'Location': 'http://127.0.0.1/secrets'}, 'unavailable'),
])
def test_http_failure_is_recorded_without_redirect_or_retry(acquisition, status, headers, state):
    calls, _, _, _, _ = acquisition(lambda request: httpx.Response(status, headers=headers, json={}))
    report = discovery.discover('research')
    assert report['state'] == 'unavailable' and report['candidates'] == [] and len(calls) == 1
    assert report['attempts'][1]['state'] == state
    assert report['attempts'][1]['status_code'] == status


def test_network_errors_are_redacted_not_simulated(acquisition):
    secret = 'github_pat_never_echo_this_query_or_credential'

    def fail(request):
        raise httpx.ConnectError(secret, request=request)

    calls, _, _, _, _ = acquisition(fail)
    report = discovery.discover('research')
    assert report['state'] == 'unavailable' and not report['candidates']
    assert len(calls) == 1 and secret not in json.dumps(report)
    assert report['attempts'][1]['reason'] == 'github_network_error'


@pytest.mark.parametrize('change', [
    {'sha': '0' * 40}, {'size': 99999}, {'type': 'symlink'},
    {'submodule_git_url': 'https://evil.org/module'}, {'encoding': 'none'},
    {'path': 'different/SKILL.md'}, {'content': '!!!not-base64!!!'},
])
def test_contents_require_exact_registered_file_bytes(acquisition, change):
    _, _, _, _, standard = acquisition()

    def handler(request):
        if '/contents/' in request.url.path:
            return httpx.Response(200, json={**file_record(SKILL, 'skills/source-check/SKILL.md'), **change})
        return standard(request)

    acquisition(handler)
    report = discovery.discover('research')
    assert report['candidates'] == []
    assert report['attempts'][-1]['state'] == 'rejected'


@pytest.mark.parametrize('raw', [
    SKILL.replace(b'license: MIT', b'license: UNKNOWN'),
    SKILL.replace(b'name: source-check', b'name: ../../malicious'),
    SKILL + b'\n-----BEGIN PRIVATE KEY-----\nsecret\n',
    SKILL + b'\nghp_' + b'a' * 40,
    b'\xff' * 200,
])
def test_unknown_skill_license_and_credential_content_are_quarantined_out(acquisition, raw):
    _, _, _, _, standard = acquisition()

    def handler(request):
        return httpx.Response(200, json=file_record(raw, 'skills/source-check/SKILL.md')) if '/contents/' in request.url.path else standard(request)

    acquisition(handler)
    report = discovery.discover('research')
    assert report['candidates'] == [] and report['state'] == 'unavailable'
    assert '-----BEGIN PRIVATE KEY-----' not in json.dumps(report)


def test_duplicate_results_and_existing_names_do_not_install_duplicates(acquisition):
    calls, _, _, search, _ = acquisition()
    search['results'] = [{'url': URL}, {'url': URL}]
    report = discovery.discover('research', existing_names=['source-check'])
    assert report['candidates'] == [] and report['state'] == 'empty' and len(calls) == 4
    assert report['attempts'][-1]['reason'] == 'already_present_reference'


def test_response_size_limit_is_enforced_before_parsing(acquisition):
    calls, _, _, _, _ = acquisition(lambda request: httpx.Response(200, content=b'x' * (discovery.MAX_RESPONSE_BYTES + 1)))
    report = discovery.discover('research')
    assert report['candidates'] == [] and len(calls) == 1
    assert report['attempts'][1]['state'] == 'rejected'


def test_api_requests_remain_bounded_with_many_candidates(acquisition):
    calls, _, _, search, _ = acquisition(lambda request: httpx.Response(200, json={
        'private': False, 'stargazers_count': 1000, 'license': None}))
    search['results'] = [{'url': URL.replace('/research/', f'/research{i}/')} for i in range(100)]
    report = discovery.discover('research')
    assert len(calls) <= discovery.MAX_GITHUB_REQUESTS
    assert not report['candidates']


def test_disabled_or_unavailable_search_does_not_fake_a_reference(acquisition):
    calls, _, _, search, _ = acquisition()
    search.update(state='disabled', results=[], attempts=[])
    assert discovery.discover('research')['state'] == 'disabled' and not calls
    search.update(state='unavailable', results=[], attempts=[{
        'state': 'rate_limited', 'reason': 'provider_rate_limit', 'status_code': 429}])
    report = discovery.discover('research')
    assert report['state'] == 'unavailable' and not report['candidates'] and not calls


def test_search_budget_consumption_prevents_late_github_requests(acquisition, monkeypatch):
    calls, _, _, search, _ = acquisition()
    clock = [100.0]
    monkeypatch.setattr(discovery.time, 'monotonic', lambda: clock[0])

    def slow_search(*_args, **_kwargs):
        clock[0] += 18
        return search

    monkeypatch.setattr(discovery.web_search, 'search', slow_search)
    report = discovery.discover('research', timeout=18)
    assert report['state'] == 'unavailable' and not report['candidates'] and calls == []
    assert report['attempts'][-1]['state'] == 'budget_exhausted'


def test_search_exception_and_unexpected_status_text_cannot_leak_credentials(acquisition, monkeypatch):
    calls, _, _, search, _ = acquisition()
    secret = 'github_pat_do_not_publish_private_value'
    search['attempts'] = [{'state': secret, 'reason': secret, 'status_code': secret}]
    report = discovery.discover('research')
    assert secret not in json.dumps(report)
    assert report['attempts'][0] == dict(provider='tavily', stage='search',
        state='unknown', reason='provider_status', status_code=None)

    def broken(*_args, **_kwargs):
        raise httpx.ConnectError(secret)

    monkeypatch.setattr(discovery.web_search, 'search', broken)
    report = discovery.discover('research')
    assert report['state'] == 'unavailable' and secret not in json.dumps(report)


def test_transport_rejects_non_fixed_origin_before_dns(monkeypatch):
    monkeypatch.setattr(discovery.web_fetch, '_resolve', lambda *_: pytest.fail('DNS must not run'))
    transport = discovery._PinnedGitHubTransport(999999999)
    for url in ['https://127.0.0.1/repos/x', 'http://api.github.com/repos/x', 'https://evil.org/repos/x']:
        with pytest.raises(ValueError):
            transport.handle_request(httpx.Request('GET', url))


def test_transport_rejects_private_dns_before_connect(monkeypatch):
    monkeypatch.setattr(discovery.web_fetch.socket, 'getaddrinfo', lambda *_: [
        (2, 1, 6, '', ('127.0.0.1', 443))])
    monkeypatch.setattr(discovery.web_fetch, '_PinnedConnection', lambda *_: pytest.fail('must not connect'))
    import time
    transport = discovery._PinnedGitHubTransport(time.monotonic() + 2)
    with pytest.raises(ValueError):
        transport.handle_request(httpx.Request('GET', 'https://api.github.com/repos/example/research'))


@pytest.mark.parametrize('kwargs', [
    {'query': ''}, {'query': 42}, {'query': 'x' * 2001}, {'limit': True}, {'limit': 3},
    {'timeout': False}, {'timeout': float('nan')}, {'timeout': 0}, {'timeout': 61},
    {'existing_names': 'single'}, {'existing_names': [42]},
])
def test_invalid_arguments_never_reach_search(acquisition, kwargs):
    calls, _, searches, _, _ = acquisition()
    args = {'query': 'research', **kwargs}
    with pytest.raises(ValueError):
        discovery.discover(**args)
    assert calls == [] and searches == []
