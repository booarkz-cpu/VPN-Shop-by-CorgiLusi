import base64
import hashlib
import hmac
import json
import socket
import time
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select
from app import outbound
from app.models import Operator

@pytest.mark.asyncio
async def test_sso_post_preserves_role_and_rejects_replay(env,monkeypatch):
    monkeypatch.setenv('SSO_SECRET','secret-for-test-0123456789-abcdefghij')
    now=int(time.time())
    payload={'login':'shop-viewer','role':'viewer','iat':now,'exp':now+60,'jti':'one-use'}
    raw=base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    token=raw+'.'+hmac.new(b'secret-for-test-0123456789-abcdefghij',raw.encode(),hashlib.sha256).hexdigest()
    assert (await env['client'].get('/sso',params={'token':token})).status_code==405
    response=await env['client'].post('/sso',data={'token':token})
    assert response.status_code==303
    assert token not in response.headers.get('location','')
    async with env['session']() as db:
        op=await db.scalar(select(Operator).where(Operator.login=='shop-viewer'))
        assert op.role=='viewer'
    assert (await env['client'].post('/sso',data={'token':token})).status_code==403

@pytest.mark.asyncio
async def test_sso_does_not_inherit_existing_admin_role(env,monkeypatch):
    monkeypatch.setenv('SSO_SECRET','secret-for-test-0123456789-abcdefghij')
    now=int(time.time())
    raw=base64.urlsafe_b64encode(json.dumps({'login':'admin','role':'viewer','iat':now,'exp':now+60,'jti':'mismatch'}).encode()).decode().rstrip('=')
    token=raw+'.'+hmac.new(b'secret-for-test-0123456789-abcdefghij',raw.encode(),hashlib.sha256).hexdigest()
    assert (await env['client'].post('/sso',data={'token':token})).status_code==403

@pytest.mark.asyncio
@pytest.mark.parametrize('ip',['127.0.0.1','10.0.0.1','169.254.169.254','::1','fd00::1','::ffff:127.0.0.1'])
async def test_webhook_transport_rejects_private_dns_and_literals(monkeypatch,ip):
    transport=outbound._PinnedPublicDNSBackend()
    connect=AsyncMock()
    transport._backend.connect_tcp=connect
    monkeypatch.setattr(socket,'getaddrinfo',lambda *args,**kw:[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443))])
    for host in (ip,'allowed.example.com'):
        with pytest.raises(OSError): await transport.connect_tcp(host,443)
    connect.assert_not_awaited()

@pytest.mark.asyncio
async def test_webhook_transport_connects_validated_literal_without_second_lookup(monkeypatch):
    transport=outbound._PinnedPublicDNSBackend()
    connect=AsyncMock()
    transport._backend.connect_tcp=connect
    lookups=[]
    def resolve(*args,**kwargs):
        lookups.append(args)
        return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))]
    monkeypatch.setattr(socket,'getaddrinfo',resolve)
    await transport.connect_tcp('allowed.example.com',443)
    assert len(lookups)==1
    assert connect.call_args.args[0]=='8.8.8.8'


@pytest.mark.asyncio
async def test_sso_rejects_public_placeholder_secret(env, monkeypatch):
    monkeypatch.setenv('SSO_SECRET', 'change-me-support-sso')
    now = int(time.time())
    raw = base64.urlsafe_b64encode(json.dumps({'login':'attacker','role':'admin','iat':now,'exp':now+60,'jti':'forged'}).encode()).decode().rstrip('=')
    token = raw + '.' + hmac.new(b'change-me-support-sso', raw.encode(), hashlib.sha256).hexdigest()
    assert (await env['client'].post('/sso', data={'token':token})).status_code == 403
