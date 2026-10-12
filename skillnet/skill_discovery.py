"""Discover pinned public SKILL.md references without installing or executing them.

Only explicit GitHub blob URLs are supported. Remote text remains quarantined
reference data, not host instructions or a certified capability. GitHub API
requests are anonymous, fixed-origin, bounded and pinned to validated public IPs.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import time
from urllib.parse import quote, unquote, urlsplit

import httpx

from . import web_fetch, web_search

VERSION = 'skillnet-online-skill-discovery-v1'
MAX_RESPONSE_BYTES = 256 * 1024
MAX_SKILL_BYTES = 64 * 1024
MAX_GITHUB_REQUESTS = 8
API = 'https://api.github.com'
_LICENSES = {'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', 'CC0-1.0', 'Unlicense'}
_SECRET = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:ghp_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{32,}|tvly-[A-Za-z0-9_-]{30,})')
_CAPABILITIES = (
    ('identity verification', r'identity|身份|消歧|人物'),
    ('citation verification', r'citation|引用|文献|论文|DOI'),
    ('source verification', r'source|来源|核验|核实'),
    ('web research', r'research|调研|研究|检索|搜索'),
    ('data analysis', r'data|analysis|数据|分析|统计'),
    ('document extraction', r'document|extract|PDF|文档|提取'),
    ('software testing', r'software|testing|代码|软件|测试'),
    ('frontend development', r'front[\s-]?end|前端|界面|交互|网页|\b(?:react|vue|svelte|html|css|tailwind|UI|UX)\b|\bnext\.?js\b'),
    ('backend development', r'back[\s-]?end|后端|服务端|服务器|接口|微服务|\b(?:fastapi|django|flask|spring|REST|GraphQL|API)\b'),
    ('data visualization', r'visuali[sz]ation|可视化|图表|绘图|渲染|\b(?:chart|plot|matplotlib|seaborn)\b|\b(?:d3|three)\.?js\b'),
    ('CAD design', r'\bCAD\b|计算机辅助设计|机械设计|建筑设计|装配|工程制图|\b(?:AutoCAD|FreeCAD|SolidWorks|OpenSCAD|Revit)\b|\bFusion\s*360\b'),
)
_PUBLIC_LABEL = '|'.join(re.escape(label) for label, _ in _CAPABILITIES)
_PUBLIC_TERMS = re.compile(rf'(?:{_PUBLIC_LABEL})(?: (?:{_PUBLIC_LABEL})){{0,3}}')


def capability_terms(task: str) -> str:
    """Return at most four fixed public capability labels, never task text."""
    # Exact whitelist-only output may cross this boundary twice. Do not infer
    # another capability from a label's words (e.g. "data visualization").
    public = ' '.join(task.split())
    if _PUBLIC_TERMS.fullmatch(public):
        return public
    # Matching selects labels from the whitelist; names, private prompts, URLs,
    # file paths and credentials can never be interpolated into the result.
    words = [label for label, pattern in _CAPABILITIES if re.search(pattern, task, re.I)]
    return ' '.join(words[:4] or ['web research source verification'])


def _query(value: str) -> str:
    return 'site:github.com "SKILL.md" ' + capability_terms(value)


def _blob_url(value) -> tuple[str, str, str, str] | None:
    if not isinstance(value, str) or len(value) > 1500 or re.search(r'[\x00-\x20\x7f\\]', value):
        return None
    try:
        p = urlsplit(value)
        if (p.scheme != 'https' or p.netloc.lower() != 'github.com' or p.query
                or p.fragment or p.username is not None or p.password is not None):
            return None
        parts = [unquote(part) for part in p.path.split('/')[1:]]
        if not 5 <= len(parts) <= 16 or parts[2] != 'blob' or parts[-1] != 'SKILL.md':
            return None
        if any(not part or part in {'.', '..'} or not re.fullmatch(r'[A-Za-z0-9_.-]+', part)
               or len(part) > 200 for part in parts):
            return None
        owner, repo, _blob, ref, *path = parts
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', owner):
            return None
        return owner, repo, ref, '/'.join(path)
    except (TypeError, ValueError):
        return None


def _attempt(state, reason, *, stage='github', status=None, **fields):
    return dict(provider='github', stage=stage, state=state, reason=reason,
                status_code=status, **fields)


class _PinnedGitHubTransport(httpx.BaseTransport):
    """Use the fetcher's public-IP TCP pinning inside a no-proxy httpx client."""
    def __init__(self, deadline):
        self.deadline = deadline

    def handle_request(self, request):
        if (request.method != 'GET' or request.url.scheme != 'https'
                or request.url.host != 'api.github.com' or request.url.port not in (None, 443)):
            raise ValueError('only fixed GitHub API GET requests are allowed')
        addresses = web_fetch._resolve('api.github.com', 443, self.deadline)
        # _resolve validates every address; the actual connection uses that IP.
        address = sorted(addresses, key=lambda item: ':' in item)[0]
        connection = web_fetch._PinnedConnection('api.github.com', 443, address, 'https', self.deadline)
        try:
            connection.request('GET', request.url.raw_path.decode('ascii'), headers={
                'Accept': 'application/vnd.github+json', 'Accept-Encoding': 'identity',
                'X-GitHub-Api-Version': '2026-03-10', 'User-Agent': 'SkillNet-PinnedSkillReference/1.0',
            })
            response = connection.getresponse()
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            web_fetch._remaining(self.deadline)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError('response_size_limit')
            if response.getheader('Content-Encoding', 'identity').lower() not in ('', 'identity'):
                raise ValueError('unsupported_response_encoding')
            return httpx.Response(response.status, headers=response.getheaders(), content=raw, request=request)
        finally:
            connection.close()
            connection.finish()


def _get_json(path: str, deadline: float, attempts: list, stage: str, *, params=None):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        attempts.append(_attempt('budget_exhausted', 'total_time_budget_exhausted', stage=stage))
        return None
    try:
        with httpx.Client(timeout=remaining, trust_env=False, follow_redirects=False,
                          transport=_PinnedGitHubTransport(deadline)) as client:
            with client.stream('GET', API + path, params=params) as response:
                status = response.status_code
                raw = bytearray()
                for chunk in response.iter_bytes(chunk_size=65536):
                    raw.extend(chunk)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise ValueError('response_size_limit')
                    if time.monotonic() > deadline:
                        raise TimeoutError
                if status in (403, 429):
                    limited = status == 429 or response.headers.get('x-ratelimit-remaining') == '0'
                    attempts.append(_attempt('rate_limited' if limited else 'access_denied',
                        'github_rate_limit' if limited else 'github_access_denied', stage=stage, status=status))
                    return None
                if not 200 <= status < 300:
                    attempts.append(_attempt('unavailable', 'redirect_not_followed' if 300 <= status < 400
                                             else 'github_http_error', stage=stage, status=status))
                    return None
                body = json.loads(raw)
                if not isinstance(body, dict):
                    raise ValueError('expected_json_object')
                attempts.append(_attempt('success', 'live_github_response', stage=stage, status=status))
                return body
    except (httpx.TimeoutException, TimeoutError):
        attempts.append(_attempt('timeout', 'github_request_timeout', stage=stage))
    except (ValueError, UnicodeError, RecursionError):
        attempts.append(_attempt('rejected', 'unsafe_or_invalid_github_response', stage=stage))
    except (httpx.HTTPError, OSError):
        attempts.append(_attempt('unavailable', 'github_network_error', stage=stage))
    return None


def _file_bytes(body: dict, path: str) -> bytes | None:
    if (body.get('type') != 'file' or body.get('path') != path or body.get('encoding') != 'base64'
            or body.get('target') or body.get('submodule_git_url') or not isinstance(body.get('content'), str)
            or isinstance(body.get('size'), bool) or not isinstance(body.get('size'), int)
            or not 0 < body['size'] <= MAX_SKILL_BYTES):
        return None
    try:
        raw = base64.b64decode(''.join(body['content'].split()), validate=True)
    except (ValueError, binascii.Error):
        return None
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    return raw if len(raw) == body['size'] and blob == body.get('sha') else None


def _metadata(text: str) -> dict:
    if not text.startswith(('---\n', '---\r\n')):
        return {}
    parts = text.splitlines()[:100]
    result = {}
    for line in parts[1:]:
        if line.strip() == '---':
            return result
        match = re.fullmatch(r'(name|description|license):\s*(.*)', line)
        if match:
            value = match.group(2).strip().strip('"\'')
            # Complex/multiline metadata is not interpreted as a license grant.
            result[match.group(1)] = value if value not in ('', '|', '>', '|-', '>-') else None
    return {}


def discover(query: str, *, limit: int = 2, timeout: float = 18, existing_names=()) -> dict:
    """Search capabilities, pin SKILL.md and license bytes, return run-only references."""
    if not isinstance(query, str) or not query.strip() or len(query) > 2000:
        raise ValueError('query must contain 1 to 2000 characters')
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 2:
        raise ValueError('limit must be an integer between 1 and 2')
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or not 1 <= timeout <= 60):
        raise ValueError('timeout must be between 1 and 60 seconds')
    if (not isinstance(existing_names, (tuple, list, set, frozenset)) or len(existing_names) > 10000
            or any(not isinstance(name, str) or len(name) > 200 for name in existing_names)):
        raise ValueError('existing_names must be a bounded collection of names')
    safe_query = _query(query)
    deadline = time.monotonic() + float(timeout)
    report = dict(version=VERSION, state='empty', query=safe_query, candidates=[], attempts=[],
        installed=False, executed=False, formal_library_changed=False,
        limits=dict(candidate_limit=limit, github_requests=MAX_GITHUB_REQUESTS,
                    response_bytes=MAX_RESPONSE_BYTES, skill_bytes=MAX_SKILL_BYTES, timeout_seconds=timeout),
        boundary='Run-only untrusted references; repository stars are not skill quality. No installation, dependency resolution or execution certification.')
    try:
        search = web_search.search(safe_query, limit=6, kind='web', timeout=max(1, min(6, timeout)))
    except (httpx.HTTPError, OSError, ValueError):
        report['attempts'].append(dict(provider='tavily', stage='search', state='unavailable',
                                       reason='provider_search_error', status_code=None))
        report['state'] = 'unavailable'
        return report
    if not isinstance(search, dict):
        report['attempts'].append(dict(provider='tavily', stage='search', state='invalid_response',
                                       reason='invalid_search_response', status_code=None))
        report['state'] = 'unavailable'
        return report
    known_states = {'success', 'empty', 'disabled', 'rate_limited', 'authentication_required',
                    'access_denied', 'unavailable', 'timeout', 'budget_exhausted', 'invalid_response'}
    known_reasons = {'live_provider_response', 'provider_rate_limit', 'provider_authentication_required',
        'provider_access_denied', 'provider_redirect_not_followed', 'provider_http_error',
        'expected_json_object', 'provider_error_envelope', 'provider_request_timeout',
        'provider_network_error', 'missing_results_list', 'no_usable_public_result',
        'live_provider_returned_zero_results', 'total_time_budget_exhausted', 'response_size_limit'}
    for item in search.get('attempts', [])[:8]:
        if isinstance(item, dict):
            # Do not copy provider exception strings, query echoes or credentials.
            status = item.get('status_code')
            report['attempts'].append(dict(provider='tavily', stage='search',
                state=item.get('state') if item.get('state') in known_states else 'unknown',
                reason=item.get('reason') if item.get('reason') in known_reasons else 'provider_status',
                status_code=status if isinstance(status, int) and not isinstance(status, bool) and 100 <= status <= 599 else None))
    if search.get('state') == 'disabled':
        report['state'] = 'disabled'
        return report
    if not search.get('results'):
        report['state'] = 'empty' if search.get('state') in ('success', 'empty') else 'unavailable'
        return report
    seen, requests = set(), 0
    existing = set(existing_names)
    search_rows = search.get('results')
    if not isinstance(search_rows, list):
        report['state'] = 'unavailable'
        report['attempts'].append(_attempt('rejected', 'invalid_search_results', stage='search'))
        return report
    for row in search_rows[:10]:
        parsed = _blob_url(row.get('url')) if isinstance(row, dict) else None
        if parsed is None:
            report['attempts'].append(_attempt('skipped', 'explicit_github_skill_blob_url_required', stage='candidate'))
            continue
        owner, repo, ref, path = parsed
        key = (owner.lower(), repo.lower(), ref, path)
        if key in seen:
            continue
        seen.add(key)
        if len(report['candidates']) >= limit:
            break
        if requests + 4 > MAX_GITHUB_REQUESTS or time.monotonic() >= deadline:
            report['attempts'].append(_attempt('budget_exhausted', 'total_time_budget_exhausted'
                if time.monotonic() >= deadline else 'api_request_budget_exhausted', stage='candidate'))
            break
        base = '/repos/' + quote(owner, safe='') + '/' + quote(repo, safe='')
        repository = _get_json(base, deadline, report['attempts'], 'repository'); requests += 1
        lic = repository.get('license') if repository else None
        license_id = lic.get('spdx_id') if isinstance(lic, dict) else None
        stars = repository.get('stargazers_count') if repository else None
        if (not repository or repository.get('private') is not False or license_id not in _LICENSES
                or isinstance(stars, bool) or not isinstance(stars, int) or stars < 0):
            report['attempts'].append(_attempt('rejected', 'public_repository_and_allowed_license_required', stage='candidate'))
            continue
        commit = _get_json(base + '/commits/' + quote(ref, safe=''), deadline, report['attempts'], 'commit'); requests += 1
        sha = commit.get('sha') if commit else None
        if not isinstance(sha, str) or not re.fullmatch(r'[a-f0-9]{40}', sha):
            if commit:
                report['attempts'].append(_attempt('rejected', 'valid_commit_pin_required', stage='candidate'))
            continue
        license_body = _get_json(base + '/license', deadline, report['attempts'], 'license', params={'ref': sha}); requests += 1
        license_path = license_body.get('path') if license_body else None
        license_raw = _file_bytes(license_body, license_path) if license_body and isinstance(license_path, str) else None
        pinned_license = license_body.get('license') if license_body else None
        if (not license_raw or not isinstance(pinned_license, dict)
                or pinned_license.get('spdx_id') != license_id):
            report['attempts'].append(_attempt('rejected', 'pinned_license_unconfirmed', stage='candidate'))
            continue
        content = _get_json(base + '/contents/' + quote(path, safe='/'), deadline, report['attempts'], 'skill', params={'ref': sha}); requests += 1
        raw = _file_bytes(content, path) if content else None
        try:
            text = raw.decode('utf-8') if raw else ''
        except UnicodeError:
            text = ''
        meta = _metadata(text)
        source_name = meta.get('name')
        declared_license = meta.get('license', license_id)
        if (not text or len(text.strip()) < 80 or not isinstance(source_name, str)
                or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', source_name)
                or declared_license != license_id or _SECRET.search(text)):
            report['attempts'].append(_attempt('rejected', 'invalid_skill_metadata_license_or_sensitive_content', stage='candidate'))
            continue
        digest = hashlib.sha256(raw).hexdigest()
        name = 'online-' + source_name[:47] + '-' + digest[:8]
        if source_name in existing or name in existing or any(c['sha256'] == digest for c in report['candidates']):
            report['attempts'].append(_attempt('skipped', 'already_present_reference', stage='candidate'))
            continue
        description = meta.get('description') or f'Untrusted {source_name} capability reference from {owner}/{repo}'
        report['candidates'].append(dict(name=name, source_name=source_name, description=description[:1000],
            body=text, sha256=digest, content_sha256=digest, bytes=len(raw), repository=f'{owner}/{repo}', repo=f'{owner}/{repo}',
            commit=sha, stars=stars, license=license_id, license_sha256=hashlib.sha256(license_raw).hexdigest(),
            license_path=license_path, source_url=f'https://github.com/{owner}/{repo}/blob/{sha}/{path}',
            retrieved_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            state='quarantined_reference', source='online_reference', read_only=True,
            execution_verified=False, instructions_trusted=False,
            license_scope='Pinned repository root license plus SKILL.md declaration; nested license overrides are not resolved. Reference review only.'))
    report['github_requests'] = requests
    failures = any(item['state'] not in ('success', 'empty', 'skipped') for item in report['attempts'])
    report['state'] = ('partial' if failures else 'success') if report['candidates'] else ('unavailable' if failures else 'empty')
    return report
