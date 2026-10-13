"""Bounded host-owned web evidence fetching; never an agent-code network escape.

Every redirect is validated again. DNS results are pinned to the actual TCP
connection, while HTTPS still authenticates the original hostname. The returned
raw bytes are evidence, not trusted instructions or verified factual claims.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import http.client
import ipaddress
import json
import math
import queue
import re
import socket
import ssl
import threading
import time
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
import zlib

USER_AGENT = 'SkillNet-EvidenceFetcher/1.0 (+bounded public-web evidence)'
_DNS_SLOTS = threading.BoundedSemaphore(8)
_REDIRECTS = {301, 302, 303, 307, 308}
_TEXT_TYPES = {'application/json', 'application/ld+json', 'application/xml',
               'application/xhtml+xml', 'text/html', 'text/plain', 'text/csv',
               'text/xml', 'text/markdown', 'application/rss+xml',
               'application/atom+xml'}


class _Blocked(ValueError):
    pass


class _TooLarge(ValueError):
    pass


class _Unsupported(ValueError):
    pass


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('total budget exhausted')
    return remaining


def _public_ip(value: str) -> str:
    try:
        if '%' in value:
            raise ValueError('scoped address')
        address = ipaddress.ip_address(value)
    except (ValueError, TypeError):
        raise _Blocked('invalid resolved address') from None
    effective = address.ipv4_mapped if isinstance(address, ipaddress.IPv6Address) else address
    effective = effective or address
    if isinstance(address, ipaddress.IPv6Address) and (address.sixtofour is not None or address.teredo is not None):
        raise _Blocked('transition addresses are forbidden')
    if (not effective.is_global or effective.is_multicast or effective.is_reserved
            or effective.is_loopback or effective.is_link_local or effective.is_unspecified):
        raise _Blocked('non-public destination')
    return str(address)


def _redacted_url(value: object) -> str:
    """Never return URL authority credentials, including on validation failure."""
    if not isinstance(value, str) or len(value) > 8192 or re.search(r'[\x00-\x20\x7f\\]', value):
        return ''
    try:
        parsed = urlsplit(value)
        authority = parsed.netloc.rsplit('@', 1)[-1]
        return urlunsplit((parsed.scheme, authority, parsed.path, parsed.query, ''))
    except ValueError:
        return ''


def _validate_url(value: str) -> tuple[str, str, int, str]:
    if not isinstance(value, str) or not value or len(value) > 8192:
        raise _Blocked('invalid URL')
    if re.search(r'[\x00-\x20\x7f\\]', value):
        raise _Blocked('URL contains unsafe characters')
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {'http', 'https'}:
            raise _Blocked('only HTTP and HTTPS are allowed')
        if parsed.username is not None or parsed.password is not None or '@' in parsed.netloc:
            raise _Blocked('URL credentials are forbidden')
        host = parsed.hostname
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme.lower() == 'https' else 80
    except ValueError as exc:
        if isinstance(exc, _Blocked):
            raise
        raise _Blocked('invalid URL authority') from None
    if not host or '%' in host or port not in {80, 443}:
        raise _Blocked('invalid host or disallowed port')
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        host = _public_ip(host)
    else:
        try:
            host = host.rstrip('.').encode('idna').decode('ascii').lower()
        except UnicodeError:
            raise _Blocked('invalid IDNA hostname') from None
        labels = host.split('.')
        if (len(host) > 253 or len(labels) < 2 or
                any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in labels)
                or labels[-1] in {'localhost', 'local', 'internal', 'home', 'lan', 'invalid', 'test'}):
            raise _Blocked('non-public or invalid hostname')
    scheme = parsed.scheme.lower()
    authority = f'[{host}]' if ':' in host else host
    default_port = 443 if scheme == 'https' else 80
    if port != default_port:
        authority += f':{port}'
    path = quote(parsed.path or '/', safe="/%:@!$&'()*+,;=-._~")
    query = quote(parsed.query, safe="/%?:@!$&'()*+,;=-._~[]")
    canonical = urlunsplit((scheme, authority, path, query, ''))
    return canonical, host, port, path + ('?' + query if query else '')


def _resolve(host: str, port: int, deadline: float) -> list[str]:
    """Bound blocking OS DNS without letting timed-out jobs accumulate forever."""
    try:
        ipaddress.ip_address(host)
        return [_public_ip(host)]
    except ValueError as exc:
        if isinstance(exc, _Blocked):
            raise
    if not _DNS_SLOTS.acquire(timeout=_remaining(deadline)):
        raise TimeoutError('DNS capacity exhausted')
    result: queue.Queue = queue.Queue(maxsize=1)

    def lookup():
        try:
            result.put((True, socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)))
        except Exception:
            result.put((False, None))
        finally:
            _DNS_SLOTS.release()

    threading.Thread(target=lookup, name='skillnet-web-dns', daemon=True).start()
    try:
        ok, records = result.get(timeout=_remaining(deadline))
    except queue.Empty:
        raise TimeoutError('DNS timeout') from None
    if not ok or not records or len(records) > 64:
        raise OSError('DNS resolution failed')
    addresses = []
    for family, socktype, _protocol, _canonname, sockaddr in records:
        if family not in {socket.AF_INET, socket.AF_INET6} or socktype != socket.SOCK_STREAM:
            raise _Blocked('unsupported resolved address')
        address = _public_ip(sockaddr[0])
        if address not in addresses:
            addresses.append(address)
    return addresses


def validate_url(url, *, timeout=12) -> str:
    """Return a canonical public URL or raise ValueError/OSError/TimeoutError.

    This checks current DNS too, but is not a fetching permission token: callers
    must still use ``fetch_url`` to pin the connection and validate redirects.
    A third-party extractor's own DNS/redirect behavior cannot be certified here.
    """
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or not 0 < timeout <= 60):
        raise _Blocked('invalid validation budget')
    canonical, host, port, _target = _validate_url(url)
    addresses = _resolve(host, port, time.monotonic() + timeout)
    if not addresses:
        raise OSError('DNS resolution failed')
    for address in addresses:
        _public_ip(address)
    return canonical


class _PinnedConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, address: str, scheme: str, deadline: float):
        super().__init__(host, port, timeout=_remaining(deadline))
        self.address, self.scheme, self.deadline = address, scheme, deadline
        self._deadline_socket = None
        self._deadline_timer = None

    def connect(self):
        # No socket.create_connection(host), proxy, or second hostname lookup.
        address = ipaddress.ip_address(self.address)
        sock = socket.socket(socket.AF_INET6 if address.version == 6 else socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(_remaining(self.deadline))
            destination = (str(address), self.port, 0, 0) if address.version == 6 else (str(address), self.port)
            sock.connect(destination)
            if _public_ip(sock.getpeername()[0]) != str(address):
                raise _Blocked('connected peer differs from validated destination')
            # A duplicate keeps the same TCP stream available for shutdown even
            # if HTTPConnection detaches a Connection: close response socket.
            # This enforces the *total* deadline during slow header/line reads,
            # rather than resetting an idle timeout for each received packet.
            self._deadline_socket = sock.dup()
            self._deadline_timer = threading.Timer(_remaining(self.deadline), self._expire)
            self._deadline_timer.daemon = True
            self._deadline_timer.start()
            if self.scheme == 'https':
                sock.settimeout(_remaining(self.deadline))
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=self.host)
            self.sock = sock
        except BaseException:
            sock.close()
            self.finish()
            raise

    def _expire(self):
        sock = self._deadline_socket
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def finish(self):
        if self._deadline_timer is not None:
            self._deadline_timer.cancel()
        if self._deadline_socket is not None:
            self._deadline_socket.close()
            self._deadline_socket = None


def _open_connection(host: str, port: int, address: str, scheme: str, deadline: float):
    return _PinnedConnection(host, port, address, scheme, deadline)


def _close_connection(connection):
    connection.close()
    finish = getattr(connection, 'finish', None)
    if finish is not None:
        finish()


def _read_body(response, connection, deadline: float, max_bytes: int) -> bytes:
    encoding = (response.getheader('Content-Encoding') or 'identity').strip().lower()
    if encoding not in {'identity', 'gzip', 'deflate'}:
        raise _Unsupported('unsupported content encoding')
    length = response.getheader('Content-Length')
    if length:
        try:
            if int(length) < 0:
                raise ValueError()
            if int(length) > max_bytes:
                raise _TooLarge('wire body exceeds byte budget')
        except ValueError as exc:
            if isinstance(exc, _TooLarge):
                raise
            raise OSError('invalid content length') from None
    decoder = zlib.decompressobj(31 if encoding == 'gzip' else 15) if encoding != 'identity' else None
    chunks, wire_bytes, decoded_bytes = [], 0, 0
    while True:
        remaining = _remaining(deadline)
        if connection.sock is not None:
            connection.sock.settimeout(remaining)
        chunk = response.read1(min(65536, max_bytes - wire_bytes + 1))
        if not chunk:
            break
        wire_bytes += len(chunk)
        if wire_bytes > max_bytes:
            raise _TooLarge('wire body exceeds byte budget')
        decoded = decoder.decompress(chunk, max_bytes - decoded_bytes + 1) if decoder else chunk
        decoded_bytes += len(decoded)
        if decoded_bytes > max_bytes or (decoder and decoder.unconsumed_tail):
            raise _TooLarge('decoded body exceeds byte budget')
        chunks.append(decoded)
    if length and wire_bytes != int(length):
        raise OSError('incomplete response body')
    if decoder and (not decoder.eof or decoder.unused_data):
        raise OSError('incomplete or concatenated compressed body')
    _remaining(deadline)
    return b''.join(chunks)


class _HTMLText(HTMLParser):
    SKIP = {'script', 'style', 'noscript', 'template', 'svg', 'canvas', 'iframe', 'object', 'head'}
    BREAK = {'p', 'br', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'section', 'article', 'header', 'footer'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_stack: list[str] = []
        self.title_depth = 0
        self.title_parts: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.title_depth += 1
        if self.skip_stack or tag in self.SKIP:
            # Void elements have no closing tag and must not trap the parser.
            if tag not in {'meta', 'link', 'input', 'img', 'br', 'hr', 'source', 'wbr', 'base', 'area', 'embed', 'param', 'track', 'col'}:
                self.skip_stack.append(tag)
        elif tag in self.BREAK:
            self.parts.append('\n')

    def handle_startendtag(self, tag, attrs):
        if not self.skip_stack and tag == 'br':
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag == 'title' and self.title_depth:
            self.title_depth -= 1
        if self.skip_stack:
            if tag in self.skip_stack:
                index = len(self.skip_stack) - 1 - self.skip_stack[::-1].index(tag)
                del self.skip_stack[index:]
        elif tag in self.BREAK:
            self.parts.append('\n')

    def handle_data(self, data):
        if self.title_depth:
            self.title_parts.append(data)
        if not self.skip_stack and not self.title_depth:
            self.parts.append(data)


def _extract(body: bytes, content_type: str) -> tuple[str, str]:
    match = re.search(r'charset\s*=\s*["\']?([\w.:-]+)', content_type, re.I)
    charset = match.group(1) if match else 'utf-8'
    if not match and ('html' in content_type.lower()):
        meta = re.search(br'charset\s*=\s*["\']?([a-zA-Z0-9._:-]+)', body[:4096], re.I)
        if meta:
            charset = meta.group(1).decode('ascii')
    try:
        decoded = body.decode(charset, errors='replace')
    except (LookupError, UnicodeError):
        decoded = body.decode('utf-8', errors='replace')
    if 'html' in content_type.lower():
        parser = _HTMLText()
        parser.feed(decoded)
        parser.close()
        lines = [' '.join(line.split()) for line in ''.join(parser.parts).splitlines()]
        return '\n'.join(line for line in lines if line), ' '.join(''.join(parser.title_parts).split())[:1000]
    return decoded, ''


def fetch_url(url, *, timeout=12, max_bytes=1_000_000, max_redirects=3) -> dict:
    """Fetch public HTTP(S) evidence with a single deadline and bounded memory.

    ``body_sha256`` hashes the decoded HTTP entity bytes, before character/HTML
    extraction. ``raw_body`` contains exactly those bytes for a host snapshot.
    A fetched page is source evidence, never proof of its statements or identity.
    """
    result = {'state': 'failed', 'requested_url': _redacted_url(url), 'final_url': '',
              'redirect_chain': [], 'status_code': None, 'content_type': '',
              'retrieved_at': datetime.now(timezone.utc).isoformat(),
              'body_sha256': '', 'body_bytes': 0, 'text': '', 'title': '', 'reason': '',
              'raw_body': b''}
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout)
            or timeout <= 0 or timeout > 60 or isinstance(max_bytes, bool) or not isinstance(max_bytes, int)
            or not 1 <= max_bytes <= 5_000_000 or isinstance(max_redirects, bool)
            or not isinstance(max_redirects, int) or not 0 <= max_redirects <= 5):
        result.update(state='blocked', reason='invalid fetch budget')
        return result
    deadline = time.monotonic() + timeout
    current, visited = url, set()
    try:
        for hop in range(max_redirects + 1):
            canonical, host, port, target = _validate_url(current)
            if canonical in visited:
                raise _Blocked('redirect loop')
            visited.add(canonical)
            addresses = _resolve(host, port, deadline)
            # Validate even injected resolver output, keeping policy centralized.
            addresses = [_public_ip(address) for address in addresses]
            if not addresses:
                raise OSError('DNS resolution failed')
            result['final_url'] = canonical
            connection, response = None, None
            for address in addresses:
                try:
                    connection = _open_connection(host, port, address, urlsplit(canonical).scheme, deadline)
                    connection.request('GET', target, headers={
                        'User-Agent': USER_AGENT, 'Accept': 'text/html, text/plain, application/json, application/xml;q=0.9',
                        'Accept-Encoding': 'identity', 'Connection': 'close',
                    })
                    if connection.sock is not None:
                        connection.sock.settimeout(_remaining(deadline))
                    response = connection.getresponse()
                    break
                except _Blocked:
                    if connection is not None:
                        _close_connection(connection)
                    raise
                except (OSError, http.client.HTTPException):
                    if connection is not None:
                        _close_connection(connection)
                    _remaining(deadline)
            if response is None:
                raise OSError('connection failed') from None
            try:
                result['status_code'] = response.status
                result['content_type'] = (response.getheader('Content-Type') or '').strip()[:256]
                if response.status in _REDIRECTS:
                    location = response.getheader('Location')
                    if not location:
                        raise OSError('redirect without location')
                    next_url = urljoin(canonical, location)
                    result['redirect_chain'].append({'url': canonical, 'status_code': response.status,
                                                     'location': _redacted_url(next_url)})
                    if hop == max_redirects:
                        raise _Blocked('redirect limit reached')
                    current = next_url
                    continue
                if not 200 <= response.status < 300:
                    result.update(state='failed', reason=f'HTTP status {response.status}')
                    return result
                mime = result['content_type'].split(';', 1)[0].strip().lower()
                if mime not in _TEXT_TYPES and not (mime.startswith('text/') and mime != 'text/event-stream'):
                    raise _Unsupported('unsupported document type; use a reviewed document adapter')
                body = _read_body(response, connection, deadline, max_bytes)
                text, title = _extract(body, result['content_type'])
                _remaining(deadline)
                result.update(state='fetched', raw_body=body, body_sha256=hashlib.sha256(body).hexdigest(),
                              body_bytes=len(body), text=text, title=title, reason='public source snapshot fetched; claims remain unverified')
                return result
            finally:
                response.close()
                _close_connection(connection)
    except _Blocked as exc:
        result.update(state='blocked', reason=str(exc))
    except _TooLarge as exc:
        result.update(state='too_large', reason=str(exc))
    except _Unsupported as exc:
        result.update(state='unsupported', reason=str(exc))
    except (TimeoutError, socket.timeout):
        result.update(state='failed', reason='fetch deadline exceeded')
    except (OSError, http.client.HTTPException, zlib.error, ValueError):
        result.update(state='failed', reason='network, TLS, or response validation failed')
    return result


def public_record(result: dict, include_text=True) -> dict:
    """JSON-safe projection; raw response bytes stay with host evidence storage."""
    public = {key: value for key, value in result.items() if key != 'raw_body' and (include_text or key != 'text')}
    return json.loads(json.dumps(public, ensure_ascii=False, allow_nan=False))
