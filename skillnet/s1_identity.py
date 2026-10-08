"""Signed backend identity context; browser-provided user IDs are never trusted."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import hmac
import re
import time
import secrets
import httpx


@dataclass(frozen=True)
class S1Context:
    tenant: str
    user: str
    project: str

    def __post_init__(self):
        if any(not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', value) for value in (self.tenant,self.user,self.project)):
            raise ValueError('S1 identity fields must be bounded stable ASCII IDs')

    def to_dict(self):
        return dict(tenant=self.tenant,user=self.user,project=self.project)


def canonical(method, path, body, headers):
    return '\n'.join([method.upper(),path,hashlib.sha256(body).hexdigest(),headers['X-S1-Timestamp'],headers['X-S1-Nonce'],
                      headers['X-S1-Tenant'],headers['X-S1-User'],headers['X-S1-Project']]).encode()


def sign(key, method, path, body, context, timestamp=None):
    headers = {'X-S1-Timestamp':str(int(time.time()) if timestamp is None else timestamp),
               'X-S1-Nonce':secrets.token_hex(16),
               'X-S1-Tenant':context.tenant,'X-S1-User':context.user,'X-S1-Project':context.project}
    headers['X-S1-Signature'] = hmac.new(key.encode(),canonical(method,path,body,headers),hashlib.sha256).hexdigest()
    return headers


def verify(key, method, path, body, incoming):
    headers = {name:incoming.get(name,'') for name in ('X-S1-Timestamp','X-S1-Nonce','X-S1-Tenant','X-S1-User','X-S1-Project','X-S1-Signature')}
    try:
        if abs(time.time()-int(headers['X-S1-Timestamp'])) > 120:
            raise ValueError('Expired S1 identity')
        if not re.fullmatch(r'[a-f0-9]{32}', headers['X-S1-Nonce']):
            raise ValueError('Invalid nonce')
        context = S1Context(headers['X-S1-Tenant'],headers['X-S1-User'],headers['X-S1-Project'])
    except (ValueError, TypeError):
        raise ValueError('Invalid or expired S1 context') from None
    expected = hmac.new(key.encode(),canonical(method,path,body,headers),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,headers['X-S1-Signature']):
        raise ValueError('Invalid S1 signature')
    return context


class S1Auth(httpx.Auth):
    requires_request_body = True
    def __init__(self, context: S1Context, signing_key: str):
        if len(signing_key) < 32:
            raise ValueError('Signing key must contain at least 32 characters')
        self.context,self.key=context,signing_key
    def auth_flow(self, request):
        request.headers.update(sign(self.key,request.method,request.url.path,request.content,self.context))
        yield request
