from __future__ import annotations

import gzip
import hashlib
import io
import json
import socket
import ssl
import threading
import time

import pytest

from skillnet import web_fetch as web


PUBLIC = '93.184.216.34'


class Response:
    def __init__(self, body=b'', status=200, headers=None):
        self.status = status
        self.headers = {'Content-Type': 'text/html; charset=utf-8', **(headers or {})}
        self.body = io.BytesIO(body)
        self.closed = False

    def getheader(self, name):
        return next((value for key, value in self.headers.items() if key.lower() == name.lower()), None)

    def read1(self, size):
        return self.body.read(size)

    def close(self):
        self.closed = True


class Connection:
    sock = None

    def __init__(self, response):
        self.response = response
        self.requests = []
        self.closed = False

    def request(self, method, target, headers):
        self.requests.append((method, target, headers))

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


def network(monkeypatch, *responses, resolver=None):
    calls, connections = [], []
    monkeypatch.setattr(web, '_resolve', resolver or (lambda *_: [PUBLIC]))
    remaining = iter(responses)

    def connect(host, port, address, scheme, deadline):
        calls.append((host, port, address, scheme))
        connection = Connection(next(remaining))
        connections.append(connection)
        return connection

    monkeypatch.setattr(web, '_open_connection', connect)
    return calls, connections


@pytest.mark.parametrize('url', [
    'file:///etc/passwd', 'ftp://example.com/x', 'data:text/html,hi', 'gopher://example.com',
    'http://localhost', 'http://foo.localhost', 'http://metadata.google.internal',
    'http://127.0.0.1', 'http://0.0.0.0', 'http://10.0.0.1', 'http://172.16.0.1',
    'http://192.168.0.1', 'http://169.254.169.254/latest/meta-data', 'http://100.64.0.1',
    'http://224.0.0.1', 'http://[::1]', 'http://[::]', 'http://[fe80::1]',
    'http://[::ffff:127.0.0.1]', 'http://[2002:7f00:1::]', 'http://[fe80::1%25eth0]',
    'https://user:password@example.com/', 'https://user@example.com/',
    'http://example.com:22', 'http://example.com:8000', 'http://example.com:0',
    'http://example.com:65536', 'http://example.com:bad', 'http://exa_mple.com',
    'http://example..com', 'http://example.com\n/', 'http://example.com\\@evil.com/',
    'https:///example.com', '', None,
])
def test_static_block_before_network(monkeypatch, url):
    monkeypatch.setattr(web, '_resolve', lambda *_: pytest.fail('must not resolve'))
    monkeypatch.setattr(web, '_open_connection', lambda *_: pytest.fail('must not connect'))
    result = web.fetch_url(url)
    assert result['state'] == 'blocked'
    assert result['raw_body'] == b''
    assert 'password' not in json.dumps(web.public_record(result))


def test_cold_start_no_keys_proxies_or_cookies(monkeypatch):
    monkeypatch.setenv('HTTPS_PROXY', 'http://secret:password@127.0.0.1:8000')
    monkeypatch.setenv('HTTP_PROXY', 'http://127.0.0.1:8000')
    calls, connections = network(monkeypatch, Response(b'<h1>Research evidence</h1>'))
    result = web.fetch_url('https://example.com/paper')
    assert result['state'] == 'fetched'
    assert calls == [('example.com', 443, PUBLIC, 'https')]
    headers = connections[0].requests[0][2]
    assert set(headers) == {'User-Agent', 'Accept', 'Accept-Encoding', 'Connection'}
    assert headers['Accept-Encoding'] == 'identity'
    assert connections[0].closed
    assert connections[0].response.closed


def test_body_hash_is_exact_snapshot_and_html_is_text(monkeypatch):
    body = ('<!doctype html><html><head><meta charset="utf-8"><title>  Scholar &amp; Work </title>'
            '<style>evil css</style></head><body><h1>学术机构</h1><p>Real &amp; evidence.</p>'
            '<script>evil script</script><noscript>evil fallback</noscript>'
            '<template>hidden template</template><svg><text>svg injection</text></svg>'
            '<iframe>iframe text</iframe><p>Last line.</p></body></html>\r\n').encode()
    network(monkeypatch, Response(body))
    result = web.fetch_url('https://example.com')
    assert result['state'] == 'fetched'
    assert result['title'] == 'Scholar & Work'
    assert result['text'] == '学术机构\nReal & evidence.\nLast line.'
    assert result['raw_body'] == body
    assert result['body_bytes'] == len(body)
    assert result['body_sha256'] == hashlib.sha256(body).hexdigest()
    assert 'raw_body' not in web.public_record(result)
    assert 'text' not in web.public_record(result, include_text=False)
    assert json.loads(json.dumps(web.public_record(result)))['body_sha256'] == result['body_sha256']


@pytest.mark.parametrize('mime,body,expected', [
    ('text/plain; charset=gb18030', '研究证据'.encode('gb18030'), '研究证据'),
    ('application/json', b'{"items":[1,2]}', '{"items":[1,2]}'),
    ('application/xml', b'<entry>data</entry>', '<entry>data</entry>'),
    ('text/plain; charset=doesnotexist', b'hello', 'hello'),
])
def test_text_formats_and_character_decoding(monkeypatch, mime, body, expected):
    network(monkeypatch, Response(body, headers={'Content-Type': mime}))
    result = web.fetch_url('https://example.com/data')
    assert result['state'] == 'fetched'
    assert result['text'] == expected


def test_html_meta_charset(monkeypatch):
    body = '<head><meta charset=gb18030><title>科学</title></head><p>证据</p>'.encode('gb18030')
    network(monkeypatch, Response(body, headers={'Content-Type': 'text/html'}))
    result = web.fetch_url('https://example.com')
    assert result['text'] == '证据'
    assert result['title'] == '科学'


@pytest.mark.parametrize('url', [
    'http://127.0.0.1/secret', 'http://[::ffff:10.0.0.1]/', 'http://metadata.google.internal/',
    'file:///etc/passwd', 'https://user:password@example.com/', 'https://example.com:8000/',
])
def test_redirect_revalidates_static_policy(monkeypatch, url):
    calls, connections = network(monkeypatch, Response(status=302, headers={'Location': url}))
    result = web.fetch_url('https://example.com/start')
    assert result['state'] == 'blocked'
    assert len(calls) == 1
    assert connections[0].closed
    assert 'password' not in json.dumps(web.public_record(result))


def test_redirect_revalidates_dns(monkeypatch):
    def resolver(host, *_):
        return [PUBLIC] if host == 'example.com' else ['10.0.0.1']
    calls, _ = network(monkeypatch, Response(status=302, headers={'Location': 'https://private.example.net'}), resolver=resolver)
    result = web.fetch_url('https://example.com')
    assert result['state'] == 'blocked'
    assert len(calls) == 1


def test_relative_redirect_loop_and_limit(monkeypatch):
    calls, _ = network(monkeypatch, Response(status=302, headers={'Location': '/next'}), Response(b'<p>ok</p>'))
    result = web.fetch_url('https://example.com/start')
    assert result['state'] == 'fetched'
    assert result['final_url'] == 'https://example.com/next'
    assert len(calls) == 2
    assert result['redirect_chain'][0]['location'] == result['final_url']
    network(monkeypatch, Response(status=301, headers={'Location': '/start'}))
    assert web.fetch_url('https://example.com/start')['reason'] == 'redirect loop'
    network(monkeypatch, Response(status=301, headers={'Location': '/next'}))
    assert web.fetch_url('https://example.com/start', max_redirects=0)['reason'] == 'redirect limit reached'


def test_idna_and_unicode_path(monkeypatch):
    calls, connections = network(monkeypatch, Response(b'ok', headers={'Content-Type': 'text/plain'}))
    result = web.fetch_url('https://例子.公司.cn/研究?q=学术#anchor')
    assert result['state'] == 'fetched'
    assert calls[0][0] == 'xn--fsqu00a.xn--55qx5d.cn'
    assert connections[0].requests[0][1] == '/%E7%A0%94%E7%A9%B6?q=%E5%AD%A6%E6%9C%AF'


def test_resolver_blocks_any_mixed_private_answer(monkeypatch):
    def resolve(*_):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (PUBLIC, 443)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]
    monkeypatch.setattr(socket, 'getaddrinfo', resolve)
    with pytest.raises(ValueError, match='non-public'):
        web.validate_url('https://example.com')


def test_dns_timeout_returns_within_total_budget(monkeypatch):
    release = threading.Event()
    def resolve(*_):
        release.wait(2)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (PUBLIC, 443))]
    monkeypatch.setattr(socket, 'getaddrinfo', resolve)
    start = time.monotonic()
    result = web.fetch_url('https://example.com', timeout=0.03)
    elapsed = time.monotonic() - start
    release.set()
    assert result['state'] == 'failed'
    assert elapsed < 1


def test_actual_connection_pins_validated_ip_and_tls_hostname(monkeypatch):
    events = []
    class Sock:
        def settimeout(self, value):
            events.append(('timeout', value))
        def connect(self, address):
            events.append(('connect', address))
        def getpeername(self):
            return (PUBLIC, 443)
        def dup(self):
            return Sock()
        def close(self):
            events.append(('close',))
        def shutdown(self, *_):
            events.append(('shutdown',))
    class Context:
        def wrap_socket(self, sock, server_hostname):
            events.append(('tls', server_hostname))
            return sock
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *_: pytest.fail('no DNS during connect'))
    monkeypatch.setattr(socket, 'socket', lambda family, kind: Sock())
    monkeypatch.setattr(ssl, 'create_default_context', lambda: Context())
    connection = web._PinnedConnection('example.com', 443, PUBLIC, 'https', time.monotonic() + 2)
    connection.connect()
    connection.close()
    connection.finish()
    assert ('connect', (PUBLIC, 443)) in events
    assert ('tls', 'example.com') in events
    assert sum(event[0] == 'connect' for event in events) == 1


def test_real_connect_peer_mismatch_is_blocked(monkeypatch):
    class Sock:
        def settimeout(self, _):
            pass
        def connect(self, _):
            pass
        def getpeername(self):
            return ('127.0.0.1', 443)
        def close(self):
            pass
    monkeypatch.setattr(socket, 'socket', lambda *_: Sock())
    connection = web._PinnedConnection('example.com', 443, PUBLIC, 'https', time.monotonic() + 2)
    with pytest.raises(ValueError, match='non-public'):
        connection.connect()


@pytest.mark.parametrize('body,headers', [
    (b'a' * 101, {'Content-Length': '101'}),
    (b'a' * 101, {}),
    (gzip.compress(b'a' * 20_000), {'Content-Encoding': 'gzip'}),
])
def test_wire_and_compression_bomb_limits(monkeypatch, body, headers):
    network(monkeypatch, Response(body, headers=headers))
    result = web.fetch_url('https://example.com', max_bytes=100)
    assert result['state'] == 'too_large'
    assert result['raw_body'] == b''
    assert result['body_sha256'] == ''


def test_compressed_entity_hash_and_truncated_stream(monkeypatch):
    body = b'<p>Real source\r\n snapshot.</p>'
    compressed = gzip.compress(body)
    network(monkeypatch, Response(compressed, headers={'Content-Encoding': 'gzip'}))
    result = web.fetch_url('https://example.com')
    assert result['state'] == 'fetched'
    assert result['raw_body'] == body
    assert result['body_sha256'] == hashlib.sha256(body).hexdigest()
    network(monkeypatch, Response(compressed[:-3], headers={'Content-Encoding': 'gzip'}))
    assert web.fetch_url('https://example.com')['state'] == 'failed'


@pytest.mark.parametrize('headers', [
    {'Content-Type': 'application/pdf'}, {'Content-Type': 'image/png'},
    {'Content-Type': ''}, {'Content-Encoding': 'br'}, {'Content-Type': 'text/event-stream'},
])
def test_unsupported_documents_are_explicit(monkeypatch, headers):
    network(monkeypatch, Response(b'not text evidence', headers=headers))
    result = web.fetch_url('https://example.com')
    assert result['state'] == 'unsupported'
    assert result['raw_body'] == b''


def test_failed_http_no_untrusted_body(monkeypatch):
    network(monkeypatch, Response(b'private server details', status=403))
    result = web.fetch_url('https://example.com')
    assert result['state'] == 'failed'
    assert result['status_code'] == 403
    assert result['text'] == ''


def test_transport_error_redaction(monkeypatch):
    monkeypatch.setattr(web, '_resolve', lambda *_: [PUBLIC])
    def fail(*_):
        raise OSError('credential=super-secret https://username:password@example.com')
    monkeypatch.setattr(web, '_open_connection', fail)
    result = web.fetch_url('https://example.com')
    assert result['state'] == 'failed'
    assert 'super-secret' not in json.dumps(web.public_record(result))
    assert 'password' not in json.dumps(web.public_record(result))


@pytest.mark.parametrize('kwargs', [
    {'timeout': float('nan')}, {'timeout': float('inf')}, {'timeout': True},
    {'timeout': 0}, {'timeout': 61}, {'max_bytes': 0}, {'max_bytes': True},
    {'max_bytes': 5_000_001}, {'max_redirects': -1}, {'max_redirects': 6},
])
def test_invalid_budgets_fail_closed(kwargs):
    assert web.fetch_url('https://example.com', **kwargs)['state'] == 'blocked'


def test_validation_does_not_certify_later_fetch(monkeypatch):
    monkeypatch.setattr(web, '_resolve', lambda *_: [PUBLIC])
    canonical = web.validate_url('https://EXAMPLE.com:443/path#ignored')
    assert canonical == 'https://example.com/path'
    monkeypatch.setattr(web, '_resolve', lambda *_: ['127.0.0.1'])
    assert web.fetch_url(canonical)['state'] == 'blocked'


def test_truncated_content_length_is_not_valid_evidence(monkeypatch):
    network(monkeypatch, Response(b'partial', headers={'Content-Length': '15'}))
    result = web.fetch_url('https://example.com')
    assert result['state'] == 'failed'
    assert result['body_sha256'] == ''


def test_slow_headers_cannot_reset_total_deadline(monkeypatch):
    # Socketpair is only a transport test seam. Production URL/DNS policy is
    # still checked and the production connection receives a fixed public IP.
    client_sock, server_sock = socket.socketpair()
    targets = []
    class Sock:
        def __getattr__(self, key):
            return getattr(client_sock, key)
        def connect(self, target):
            targets.append(target)
        def getpeername(self):
            return (PUBLIC, 80)
    monkeypatch.setattr(web, '_resolve', lambda *_: [PUBLIC])
    monkeypatch.setattr(socket, 'socket', lambda *_args, **_kwargs: Sock())
    def trickle():
        try:
            server_sock.recv(65536)
            server_sock.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nX-Slow: ')
            for _ in range(100):
                server_sock.sendall(b'a')
                time.sleep(0.01)
        except OSError:
            pass
        finally:
            server_sock.close()
    thread = threading.Thread(target=trickle, daemon=True)
    thread.start()
    start = time.monotonic()
    result = web.fetch_url('http://example.com', timeout=0.06)
    elapsed = time.monotonic() - start
    thread.join(timeout=1)
    assert result['state'] == 'failed'
    assert elapsed < 0.8
    assert targets == [(PUBLIC, 80)]
