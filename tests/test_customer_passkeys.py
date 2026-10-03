"""Customer credentials are verified cryptographically, never accepted as IDs."""
import secrets
from datetime import datetime, timedelta
from http.cookies import SimpleCookie

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException, Response
from sqlalchemy import func, select
from starlette.requests import Request

from app import customer_passkeys as keys
from app.models import CustomerPasskey, CustomerPasskeyChallenge, FeatureFlag, User, UserSession
from app.security import hash_password
from test_admin_passkeys import assertion, attestation
from test_subscription_commerce import database

ORIGIN = 'https://cabinet.example.test'
PASSWORD = 'customer-passkey-password'


def request(binding='', origin=ORIGIN):
    return Request({'type': 'http', 'method': 'POST', 'scheme': 'https', 'path': '/api/auth/passkeys/login/verify',
        'headers': [(b'origin', origin.encode()), (b'cookie', f'{keys.COOKIE}={binding}'.encode())],
        'client': ('127.0.0.1', 123)})


def binding(response):
    cookies = SimpleCookie();cookies.load(response.headers['set-cookie'])
    return cookies[keys.COOKIE].value


async def registered(db, monkeypatch):
    monkeypatch.setattr(keys.settings, 'customer_webauthn_origin', ORIGIN)
    user = await db.get(User, 1)
    user.email_password_hash = hash_password(PASSWORD)
    db.add(FeatureFlag(key='passkeys', enabled=True));await db.commit()
    private = ec.generate_private_key(ec.SECP256R1());identifier = secrets.token_bytes(32)
    response = Response()
    options = await keys.registration_options(keys.RegisterIn(password=PASSWORD), request(), response, db)
    await keys.registration_verify(keys.VerifyIn(ticket=options['ticket'],
        credential=attestation(options['options'], private, identifier, origin=ORIGIN)),
        request(binding(response)), Response(), db)
    return user, private, identifier


@pytest.mark.asyncio
async def test_customer_passkey_real_crypto_session_and_replay(database, monkeypatch):
    user, private, identifier = await registered(database, monkeypatch)
    response = Response();options = await keys.login_options(request(), response, database)
    payload = keys.VerifyIn(ticket=options['ticket'], credential=assertion(options['options'], private,
        identifier, user.passkey_user_handle, origin=ORIGIN))
    assert (await keys.login_verify(payload, request(binding(response)), Response(), database))['auth_method'] == 'passkey'
    assert await database.scalar(select(func.count()).select_from(UserSession)) == 1
    with pytest.raises(HTTPException):
        await keys.login_verify(payload, request(binding(response)), Response(), database)
    assert await database.scalar(select(func.count()).select_from(UserSession)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['origin', 'uv', 'handle', 'cookie', 'expired', 'restricted', 'counter'])
async def test_customer_assertion_rejects_attacks(database, monkeypatch, failure):
    user, private, identifier = await registered(database, monkeypatch)
    response = Response();options = await keys.login_options(request(), response, database)
    credential = assertion(options['options'], private, identifier,
        'bad-handle' if failure == 'handle' else user.passkey_user_handle,
        origin='https://evil.test' if failure == 'origin' else ORIGIN,
        flags=1 if failure == 'uv' else 5)
    if failure == 'expired':
        (await database.scalar(select(CustomerPasskeyChallenge))).expires_at = datetime.utcnow()-timedelta(seconds=1)
    if failure == 'restricted':user.restricted_at = datetime.utcnow()
    if failure == 'counter':(await database.scalar(select(CustomerPasskey))).sign_count = 1
    await database.commit()
    with pytest.raises(HTTPException):
        await keys.login_verify(keys.VerifyIn(ticket=options['ticket'], credential=credential),
            request('wrong' if failure == 'cookie' else binding(response)), Response(), database)
    assert await database.scalar(select(func.count()).select_from(UserSession)) == 0


@pytest.mark.asyncio
async def test_inventory_and_delete_are_owner_scoped(database, monkeypatch):
    await registered(database, monkeypatch)
    row = await database.scalar(select(CustomerPasskey))
    foreign = CustomerPasskey(user_id=2, credential_id='foreign', public_key='key', name='Other')
    database.add(foreign);await database.commit()
    listed = await keys.inventory(request(), Response(), database)
    assert [x['id'] for x in listed] == [row.id]
    assert not {'public_key', 'credential_id'} & listed[0].keys()
    with pytest.raises(HTTPException):
        await keys.remove(foreign.id, keys.RegisterIn(password=PASSWORD), request(), database)
    with pytest.raises(HTTPException):
        await keys.remove(row.id, keys.RegisterIn(password='wrong'), request(), database)
    await keys.remove(row.id, keys.RegisterIn(password=PASSWORD), request(), database)
    assert await database.get(CustomerPasskey, row.id) is None
