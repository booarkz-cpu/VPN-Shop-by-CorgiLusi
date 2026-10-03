"""Import integrity, preview ownership/staleness, and atomic bulk actions."""
import asyncio
import sqlite3
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app import customer_operations as ops
from app import main as shop
ORIGINAL_USER_FROM_TOKEN = shop.user_from_token
from app.db import get_db
from app.models import CustomerOperation, User, UserImportIdentity, UserSession
from app.security import current_admin
from test_subscription_commerce import database

ADMIN = SimpleNamespace(email='operator@example.test', role='operator')


def sqlite_data(rows=((123, 'Alice'),), ddl='CREATE TABLE users (tid, name)'):
    db = sqlite3.connect(':memory:')
    try:
        db.execute(ddl)
        db.executemany('INSERT INTO users VALUES (?, ?)', rows)
        db.commit()
        return db.serialize()
    finally:
        db.close()


def upload(data):
    async def receive():
        return {'type': 'http.request', 'body': data, 'more_body': False}
    return Request({'type': 'http', 'method': 'POST', 'headers': []}, receive)


async def preview(db, data=None):
    return await ops.preview_import(upload(data or sqlite_data()), 'old-bot', 'users', 'tid', 'name', db, ADMIN)


def test_sqlite_mapping_and_identifier_escaping():
    data = sqlite_data()
    assert ops.read_sqlite(data) == {'tables': {'users': ['tid', 'name']}, 'max_rows': 5000}
    assert ops.read_sqlite(data, 'users', 'tid', 'name') == [{'telegram_id': 123, 'username': 'Alice'}]
    assert ops.read_sqlite(data, 'users', 'tid')[0]['username'] is None
    with pytest.raises(HTTPException):ops.read_sqlite(data, 'users; DROP TABLE users', 'tid')
    quoted = sqlite_data(ddl='CREATE TABLE users ("t""id", name)')
    assert ops.read_sqlite(quoted, 'users', 't"id')[0]['telegram_id'] == 123


@pytest.mark.parametrize('rows', [[(0,'a')], [(-12,'a')], [(1.5,'a')], [('1e3','a')], [(2**52,'a')], [(123,'a'),(123,'b')], [(1,'x'*256)], [(1,b'blob')], [(1,'bad\nname')]])
def test_invalid_rows_rejected_as_whole_file(rows):
    with pytest.raises(HTTPException):ops.read_sqlite(sqlite_data(rows), 'users', 'tid', 'name')


def test_limits_corruption_and_views():
    for data in (b'not sqlite', b'SQLite format 3\x00'+b'x'*100, b'x'*(ops.MAX_BYTES+1)):
        with pytest.raises(HTTPException):ops.read_sqlite(data)
    with pytest.raises(HTTPException):ops.read_sqlite(sqlite_data([]), 'users', 'tid')
    with pytest.raises(HTTPException):ops.read_sqlite(sqlite_data([(i+1,'a') for i in range(5001)]), 'users', 'tid')
    db=sqlite3.connect(':memory:')
    db.executescript('CREATE TABLE users(tid,name); CREATE VIEW danger AS SELECT * FROM users;')
    assert 'danger' not in ops.read_sqlite(db.serialize())['tables']
    db.close()


@pytest.mark.asyncio
async def test_stream_limit():
    with pytest.raises(HTTPException) as error:await ops.upload_bytes(upload(b'x'*(ops.MAX_BYTES+1)))
    assert error.value.status_code == 413


@pytest.mark.asyncio
async def test_import_repeat_existing_and_deleted_identity(database):
    existing=await database.get(User,1);existing.telegram_id=456
    await database.commit()
    before=existing.wallet_balance
    p=await preview(database,sqlite_data([(123,'New'),(456,'Do not overwrite')]))
    assert [r['action'] for r in p['rows']] == ['create','skip']
    assert await database.scalar(select(func.count()).select_from(User)) == 2
    result=await ops.apply_operation(p['id'],database,ADMIN)
    assert await ops.apply_operation(p['id'],database,ADMIN) == result
    assert existing.username == 'Owner' and existing.wallet_balance == before
    new=await database.scalar(select(User).where(User.telegram_id==123))
    assert new.email is None and new.email_password_hash is None and new.wallet_balance == 0
    assert await database.scalar(select(func.count()).select_from(UserImportIdentity)) == 1
    # An erased Telegram identity cannot be recreated by replaying the old dump.
    new.telegram_id=None;new.deleted_at=datetime.utcnow();await database.commit()
    p2=await preview(database)
    assert p2['rows'][0]['action']=='skip'
    assert 'rows' not in (await database.get(CustomerOperation,p['id'])).payload


@pytest.mark.asyncio
async def test_expiry_ownership_stale_import_and_journal(database):
    p=await preview(database)
    other=SimpleNamespace(email='other@example.test')
    with pytest.raises(HTTPException) as error:await ops.apply_operation(p['id'],database,other)
    assert error.value.status_code == 404
    assert await ops.journal(database,other) == []
    database.add(User(telegram_id=123));await database.commit()
    with pytest.raises(HTTPException) as error:await ops.apply_operation(p['id'],database,ADMIN)
    assert error.value.status_code == 409
    row=await database.get(CustomerOperation,p['id']);row.expires_at=datetime.utcnow()-timedelta(seconds=1)
    await database.commit()
    with pytest.raises(HTTPException):await ops.apply_operation(p['id'],database,ADMIN)
    assert (await ops.journal(database,ADMIN))[0]['status']=='expired'
    await preview(database)
    await database.refresh(row)
    assert row.payload=={} and row.status=='expired'


@pytest.mark.asyncio
async def test_bulk_revokes_sessions_and_retries_atomically(database):
    session=UserSession(user_id=1,jti_hash='a'*64,expires_at=datetime.utcnow()+timedelta(days=1))
    database.add(session);await database.commit()
    data=ops.BulkIn(action='restrict',user_ids=[2,1],reason='Operator review')
    p=await ops.preview_bulk(data,database,ADMIN)
    result=await ops.apply_operation(p['id'],database,ADMIN)
    for i in [1,2]:assert (await database.get(User,i)).restricted_at
    await database.refresh(session);assert session.revoked_at
    assert await ops.apply_operation(p['id'],database,ADMIN)==result
    p2=await ops.preview_bulk(ops.BulkIn(action='unrestrict',user_ids=[1,2],reason='Review complete'),database,ADMIN)
    await ops.apply_operation(p2['id'],database,ADMIN)
    for i in [1,2]:assert (await database.get(User,i)).restricted_at is None
    await database.refresh(session);assert session.revoked_at


@pytest.mark.asyncio
async def test_bulk_missing_duplicate_deleted_and_stale_all_or_nothing(database):
    for ids in ([1,999],[1,1],[-1]):
        with pytest.raises(HTTPException):await ops.preview_bulk(ops.BulkIn(action='restrict',user_ids=ids,reason='Review'),database,ADMIN)
    p=await ops.preview_bulk(ops.BulkIn(action='restrict',user_ids=[1,2],reason='Review'),database,ADMIN)
    user=await database.get(User,2);user.deleted_at=datetime.utcnow();await database.commit()
    with pytest.raises(HTTPException):await ops.apply_operation(p['id'],database,ADMIN)
    assert (await database.get(User,1)).restricted_at is None


@pytest.mark.asyncio
async def test_viewer_forbidden_http_routes(database):
    app=FastAPI();app.include_router(ops.router)
    async def session():yield database
    app.dependency_overrides[get_db]=session
    app.dependency_overrides[current_admin]=lambda:SimpleNamespace(email='viewer@example.test',role='viewer')
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post('/api/admin/customer-operations/import/inspect',content=sqlite_data())
        assert response.status_code==403
        assert (await client.get('/api/admin/customer-operations/journal')).status_code==403
        assert (await client.post('/api/admin/customer-operations/x/apply')).status_code==403


@pytest.mark.asyncio
async def test_postgres_competing_imports_only_one_applies(database):
    if database.bind.dialect.name!='postgresql':pytest.skip('Requires PostgreSQL row locking')
    p1=await preview(database);p2=await preview(database)
    async def apply(id):
        async with AsyncSession(database.bind,expire_on_commit=False) as session:
            try:return await ops.apply_operation(id,session,ADMIN)
            except HTTPException as error:return error.status_code
    results=await asyncio.gather(apply(p1['id']),apply(p2['id']))
    assert sum(isinstance(r,dict) for r in results)==1 and 409 in results
    assert await database.scalar(select(func.count()).select_from(User).where(User.telegram_id==123))==1


@pytest.mark.asyncio
async def test_operator_http_upload_mapping_and_apply(database):
    app=FastAPI();app.include_router(ops.router)
    async def session():yield database
    app.dependency_overrides[get_db]=session
    app.dependency_overrides[current_admin]=lambda:ADMIN
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        data=sqlite_data()
        assert (await client.post('/api/admin/customer-operations/import/inspect',content=data)).status_code==200
        response=await client.post('/api/admin/customer-operations/import/preview',params={'source':'old','table':'users','telegram_column':'tid','username_column':'name'},content=data)
        assert response.status_code==200
        operation_id=response.json()['id']
        response=await client.post(f'/api/admin/customer-operations/{operation_id}/apply')
        assert response.status_code==200 and response.json()['rows'][0]['action']=='created'


@pytest.mark.asyncio
async def test_postgres_same_preview_retry_returns_same_result(database):
    if database.bind.dialect.name!='postgresql':pytest.skip('Requires PostgreSQL row locking')
    p=await preview(database)
    async def apply():
        async with AsyncSession(database.bind,expire_on_commit=False) as session:
            return await ops.apply_operation(p['id'],session,ADMIN)
    results=await asyncio.gather(apply(),apply())
    assert results[0]==results[1]
    assert await database.scalar(select(func.count()).select_from(UserImportIdentity))==1


@pytest.mark.asyncio
async def test_restricted_user_rejected_by_common_session_guard(database,monkeypatch):
    user=await database.get(User,1);user.restricted_at=datetime.utcnow();await database.commit()
    monkeypatch.setattr(shop,'decode_token',lambda value:{'sub':'1','type':'user'})
    request=Request({'type':'http','method':'GET','headers':[(b'authorization',b'Bearer test')]})
    with pytest.raises(HTTPException) as error:await ORIGINAL_USER_FROM_TOKEN(request,database)
    assert error.value.status_code==403
