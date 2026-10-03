import asyncio
import io
import json
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, HTTPException, UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app import admin_customer_operations as operations
from app import customer_workspace_api as workspace
from app.models import AutoRenewMethod, CustomerImportJob, CustomerImportIdentity, CustomerBatchOperation, FinancialLedger, Notification, Subscription, User, UserSession
from app.sqlite_import import MappingIn, extract
from test_subscription_commerce import database

ADMIN = SimpleNamespace(email='admin@example.test', role='admin')
MAPPING = {'namespace':'old-bot','table':'users','source_id':'id','telegram_id':'telegram_id','username':'username',
    'balance':'balance','currency':'RUB','credit_balances':True}


def snapshot(tmp_path, rows=((7, 9001, 'New', '12.34'),), sql='CREATE TABLE users(id INTEGER, telegram_id INTEGER, username TEXT, balance TEXT)'):
    path=tmp_path/'source.db'
    if path.exists():path.unlink()
    with sqlite3.connect(path) as connection:
        connection.execute(sql)
        if rows:connection.executemany('INSERT INTO users VALUES (?,?,?,?)',rows)
    return path.read_bytes()


def upload(data):return UploadFile(file=io.BytesIO(data),filename='users.db')
def request(key='one'):return Request({'type':'http','headers':[(b'idempotency-key',key.encode())]})


async def preview(db,data,mapping=None,admin=ADMIN):
    return await operations.import_preview(upload(data),json.dumps(mapping or MAPPING),db,admin)


def test_sqlite_mapping_readonly_bounds_and_minor_currency(tmp_path):
    data=snapshot(tmp_path,((7,9001,'New','1234'),))
    assert extract(data,'users')['columns']==['id','telegram_id','username','balance']
    rows=extract(data,'users',MappingIn(**{**MAPPING,'balance_unit':'minor'}))
    assert rows[0]['balance']=='12.34'
    for bad in (b'not sqlite',data[:100],b'SQLite format 3\0'+b'x'*(5*1024*1024)):
        with pytest.raises(HTTPException):extract(bad,'users')
    for field in ('telegram_id); DROP TABLE users;--','missing'):
        with pytest.raises(HTTPException):extract(data,'users',MappingIn(**{**MAPPING,'telegram_id':field}))
    with pytest.raises(HTTPException):extract(data,'users;ATTACH database')


@pytest.mark.parametrize('rows', [((1,9001,'N','NaN'),),((1,9001,'N','-1'),),((1,9001,'N','0.001'),),
    ((1,9001,'N','1000001'),),((1,9001,'N','2'),(1,9002,'M','3')),
    ((1,9001,'N','2'),(2,9001,'M','3')),((1,0,'N','1'),),((1,2**63-1,'N','1'),(2,2**63-1,'M','2'))])
def test_invalid_import_rows_rejected_whole_file(tmp_path,rows):
    with pytest.raises(HTTPException):extract(snapshot(tmp_path,rows),'users',MappingIn(**MAPPING))


def test_views_virtual_tables_generated_columns_and_large_exports_denied(tmp_path):
    path=tmp_path/'unsafe.db'
    with sqlite3.connect(path) as db:
        db.executescript('CREATE TABLE ordinary(id INTEGER, telegram_id INTEGER, calculated TEXT GENERATED ALWAYS AS (hex(telegram_id)));CREATE VIEW users AS SELECT * FROM ordinary;')
    with pytest.raises(HTTPException):extract(path.read_bytes(),'users')
    with pytest.raises(HTTPException):extract(path.read_bytes(),'ordinary',MappingIn(**{**MAPPING,'table':'ordinary','username':'calculated','balance':None}))
    data=snapshot(tmp_path,tuple((i,i+10000,'User','0') for i in range(1,1002)))
    with pytest.raises(HTTPException):extract(data,'users',MappingIn(**MAPPING))


@pytest.mark.asyncio
async def test_import_credits_new_user_once_with_history_and_clears_staging(database,tmp_path,monkeypatch):
    data=snapshot(tmp_path);stage=await preview(database,data)
    job=await database.get(CustomerImportJob,stage['id'])
    assert '9001' not in job.payload_encrypted and stage['counts']['new']==1 and stage['total_credit']=='12.34'
    result=await operations.import_apply(job.id,operations.ApplyIn(fingerprint=stage['fingerprint']),database,ADMIN)
    assert result['created']==1 and result['credited']=='12.34' and job.payload_encrypted==''
    assert await operations.import_apply(job.id,operations.ApplyIn(fingerprint=stage['fingerprint']),database,ADMIN)==result
    repeat=await preview(database,data)
    assert repeat['counts']['already_imported']==1 and repeat['total_credit']=='0.00'
    await operations.import_apply(repeat['id'],operations.ApplyIn(fingerprint=repeat['fingerprint']),database,ADMIN)
    assert await database.scalar(select(func.count()).select_from(FinancialLedger))==1
    user=await database.scalar(select(User).where(User.telegram_id==9001))
    assert user.wallet_balance==Decimal('12.34')
    from app import main as shop
    async def owner(*args):return user
    monkeypatch.setattr(shop,'user_from_token',owner)
    assert (await workspace.wallet_history(request(),database))['items'][0]['kind']=='wallet_import'


@pytest.mark.asyncio
async def test_existing_accounts_keep_names_balance_and_identities(database,tmp_path):
    user=await database.get(User,1);user.telegram_id=9001;user.email='verified@example.test';await database.commit()
    stage=await preview(database,snapshot(tmp_path));assert stage['counts']['existing']==1 and stage['total_credit']=='0.00'
    result=await operations.import_apply(stage['id'],operations.ApplyIn(fingerprint=stage['fingerprint']),database,ADMIN)
    assert result['linked_existing']==1 and user.wallet_balance==1000 and user.username=='Owner' and user.email=='verified@example.test'
    assert await database.scalar(select(func.count()).select_from(FinancialLedger))==0


@pytest.mark.asyncio
async def test_secret_rotation_preserves_active_preview_and_identity_dedupe(database,tmp_path,monkeypatch):
    data=snapshot(tmp_path);stage=await preview(database,data)
    original=operations.settings.app_secret
    monkeypatch.setattr(operations.settings,'app_secret_previous',original)
    monkeypatch.setattr(operations.settings,'app_secret','rotated-secret-for-import-tests')
    result=await operations.import_apply(stage['id'],operations.ApplyIn(fingerprint=stage['fingerprint']),database,ADMIN)
    assert result['credited']=='12.34'
    repeat=await preview(database,data)
    assert repeat['counts']['already_imported']==1 and repeat['total_credit']=='0.00'


@pytest.mark.asyncio
async def test_import_stale_preview_owner_expiry_cancellation_and_binding_conflict(database,tmp_path):
    data=snapshot(tmp_path);stage=await preview(database,data)
    with pytest.raises(HTTPException):await operations.import_apply(stage['id'],operations.ApplyIn(fingerprint=stage['fingerprint']),database,SimpleNamespace(email='other'))
    user=await database.get(User,1);user.telegram_id=9001;await database.commit()
    with pytest.raises(HTTPException) as error:await operations.import_apply(stage['id'],operations.ApplyIn(fingerprint=stage['fingerprint']),database,ADMIN)
    assert error.value.status_code==409
    fresh=await preview(database,data);await operations.import_apply(fresh['id'],operations.ApplyIn(fingerprint=fresh['fingerprint']),database,ADMIN)
    changed=await preview(database,snapshot(tmp_path,((7,9002,'Changed','2'),)))
    assert changed['counts']['blocked']==1
    with pytest.raises(HTTPException):await operations.import_apply(changed['id'],operations.ApplyIn(fingerprint=changed['fingerprint']),database,ADMIN)
    cancelled=await preview(database,data);await operations.cancel_import(cancelled['id'],database,ADMIN)
    assert (await database.get(CustomerImportJob,cancelled['id'])).payload_encrypted==''
    with pytest.raises(HTTPException):await operations.import_apply(cancelled['id'],operations.ApplyIn(fingerprint=cancelled['fingerprint']),database,ADMIN)
    job=await database.get(CustomerImportJob,stage['id']);job.expires_at=datetime.utcnow()-timedelta(seconds=1);await database.commit()
    await operations.cleanup_import_previews(database);await database.commit()
    assert job.status=='expired' and job.payload_encrypted==''


@pytest.mark.asyncio
async def test_import_disabled_balances_currency_and_atomic_ledger_failure(database,tmp_path):
    data=snapshot(tmp_path)
    with pytest.raises(HTTPException):await preview(database,data,{**MAPPING,'currency':'USD'})
    stage=await preview(database,data)
    key=operations.identity_key('old-bot','7')
    database.add(FinancialLedger(operation_key='customer-import:'+key,user_id=1,kind='wallet_import',direction='credit',amount=1,currency='RUB'));await database.commit()
    with pytest.raises(HTTPException):await operations.import_apply(stage['id'],operations.ApplyIn(fingerprint=stage['fingerprint']),database,ADMIN)
    assert await database.scalar(select(User.id).where(User.telegram_id==9001)) is None
    assert await database.scalar(select(func.count()).select_from(CustomerImportIdentity))==0
    safe=await preview(database,data,{**MAPPING,'credit_balances':False})
    await operations.import_apply(safe['id'],operations.ApplyIn(fingerprint=safe['fingerprint']),database,ADMIN)
    assert (await database.scalar(select(User).where(User.telegram_id==9001))).wallet_balance==0


@pytest.mark.asyncio
@pytest.mark.parametrize('action',['notify','revoke_sessions','disable_auto_renew'])
async def test_bulk_preview_atomic_apply_replay_and_conflicting_key(database,action):
    user=await database.get(User,1);user.auto_renew_enabled=True
    sub=await database.get(Subscription,1);sub.auto_renew_enabled=True;sub.next_renewal_at=datetime.utcnow()
    database.add_all([UserSession(user_id=1,jti_hash='one',expires_at=datetime.utcnow()+timedelta(days=1)),
        AutoRenewMethod(user_id=1,provider='yookassa',external_token_encrypted='secret',enabled=True)])
    await database.commit()
    payload=operations.BulkIn(user_ids=[1,2],action=action,reason='Operational change',title='Notice',body='Plain message')
    stage=await operations.bulk_preview(payload,database,ADMIN);exact=payload.model_copy(update={'fingerprint':stage['fingerprint']})
    result=await operations.bulk_apply(exact,request(),database,ADMIN)
    assert await operations.bulk_apply(exact,request(),database,ADMIN)==result
    with pytest.raises(HTTPException):await operations.bulk_apply(exact.model_copy(update={'reason':'Other reason'}),request(),database,ADMIN)
    assert await database.scalar(select(func.count()).select_from(CustomerBatchOperation))==1
    if action=='notify':assert await database.scalar(select(func.count()).select_from(Notification))==2
    elif action=='revoke_sessions':assert (await database.scalar(select(UserSession))).revoked_at
    else:
        assert not user.auto_renew_enabled and not sub.auto_renew_enabled and sub.next_renewal_at is None
        assert (await database.scalar(select(AutoRenewMethod))).enabled
        from app import main as shop
        result=await shop.set_auto_renew({'enabled':True},request(),database)
        assert result['enabled'] and sub.auto_renew_enabled


@pytest.mark.asyncio
async def test_bulk_stale_duplicate_unknown_deleted_and_blank_inputs(database):
    payload=operations.BulkIn(user_ids=[1],action='notify',reason='Notice',title='Title',body='Body')
    stage=await operations.bulk_preview(payload,database,ADMIN)
    database.add(UserSession(user_id=1,jti_hash='new-login',expires_at=datetime.utcnow()+timedelta(days=1)));await database.commit()
    with pytest.raises(HTTPException):await operations.bulk_apply(payload.model_copy(update={'fingerprint':stage['fingerprint']}),request(),database,ADMIN)
    for changes in ({'user_ids':[1,1]},{'user_ids':[999]},{'user_ids':[-1]},{'title':' '},{'reason':'   '}):
        with pytest.raises(HTTPException):await operations.bulk_preview(payload.model_copy(update=changes),database,ADMIN)
    user=await database.get(User,1);user.deleted_at=datetime.utcnow();await database.commit()
    with pytest.raises(HTTPException):await operations.bulk_preview(payload,database,ADMIN)
    assert await database.scalar(select(func.count()).select_from(Notification))==0


@pytest.mark.asyncio
async def test_auto_renew_rechecks_disabled_method_and_deleted_owner(database):
    from app import main as shop
    method=AutoRenewMethod(user_id=1,provider='yookassa',external_token_encrypted='secret',enabled=True)
    database.add(method);await database.commit()
    await database.execute(update(AutoRenewMethod).where(AutoRenewMethod.id==method.id).values(enabled=False).execution_options(synchronize_session=False));await database.commit()
    assert method.enabled  # The old instance must not authorize a new renewal.
    with pytest.raises(HTTPException) as error:await shop.set_auto_renew({'enabled':True},request(),database)
    assert error.value.status_code==409
    user=await database.get(User,1);user.deleted_at=datetime.utcnow();await database.commit()
    with pytest.raises(HTTPException):await shop.remove_auto_renew_method(request(),database)
    assert await database.get(AutoRenewMethod,method.id) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize('role',['viewer','operator','admin'])
async def test_import_routes_require_dedicated_admin_permissions(database,role):
    from app.db import get_db
    from app.security import current_admin
    app=FastAPI();app.include_router(operations.router)
    async def db():yield database
    async def admin():return SimpleNamespace(email=ADMIN.email,role=role)
    app.dependency_overrides[get_db]=db;app.dependency_overrides[current_admin]=admin
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response=await client.get('/api/admin/customer-operations/import/history')
        bulk=await client.post('/api/admin/customer-operations/bulk/preview',json={'user_ids':[1],'action':'revoke_sessions','reason':'Support request'})
    assert response.status_code==(200 if role=='admin' else 403)
    assert bulk.status_code==(200 if role=='admin' else 403)
    if role=='admin':assert response.headers['cache-control']=='private, no-store'


@pytest.mark.asyncio
async def test_postgres_parallel_previews_apply_only_one_import_credit(database,tmp_path):
    if database.bind.dialect.name!='postgresql':pytest.skip('PostgreSQL import serialization')
    data=snapshot(tmp_path);stages=[await preview(database,data),await preview(database,data)]
    async def apply(stage):
        async with AsyncSession(database.bind,expire_on_commit=False) as db:
            try:return await operations.import_apply(stage['id'],operations.ApplyIn(fingerprint=stage['fingerprint']),db,ADMIN)
            except HTTPException as error:return error.status_code
    results=await asyncio.gather(*(apply(stage) for stage in stages))
    assert sum(isinstance(result,dict) for result in results)==1 and 409 in results
    assert await database.scalar(select(func.count()).select_from(FinancialLedger))==1


@pytest.mark.asyncio
async def test_postgres_parallel_bulk_retry_delivers_each_notice_once(database):
    if database.bind.dialect.name!='postgresql':pytest.skip('PostgreSQL journal serialization')
    payload=operations.BulkIn(user_ids=[1,2],action='notify',reason='Service notice',title='Notice',body='Text')
    stage=await operations.bulk_preview(payload,database,ADMIN);await database.commit()
    exact=payload.model_copy(update={'fingerprint':stage['fingerprint']})
    async def apply():
        async with AsyncSession(database.bind,expire_on_commit=False) as db:
            return await operations.bulk_apply(exact,request('retry'),db,ADMIN)
    results=await asyncio.gather(apply(),apply())
    assert results[0]==results[1]
    assert await database.scalar(select(func.count()).select_from(Notification))==2
    assert await database.scalar(select(func.count()).select_from(CustomerBatchOperation))==1


@pytest.mark.asyncio
async def test_bulk_shop_restriction_revokes_auth_disables_renew_and_restore_preserves_vpn(database):
    from app import main as shop
    user=await database.get(User,1);sub=await database.get(Subscription,1)
    user.auto_renew_enabled=True;sub.auto_renew_enabled=True;sub.next_renewal_at=datetime.utcnow()
    database.add(UserSession(user_id=1,jti_hash='restrict-session',expires_at=datetime.utcnow()+timedelta(days=1)))
    await database.commit()
    for action in ('restrict_shop','restore_shop'):
        payload=operations.BulkIn(user_ids=[1],action=action,reason='Owner-reviewed shop access')
        stage=await operations.bulk_preview(payload,database,ADMIN)
        exact=payload.model_copy(update={'fingerprint':stage['fingerprint']})
        result=await operations.bulk_apply(exact,request(action),database,ADMIN)
        assert await operations.bulk_apply(exact,request(action),database,ADMIN)==result
        assert sub.lifecycle_status=='active' and sub.remnawave_uuid=='remote-1'
        assert not user.auto_renew_enabled and not sub.auto_renew_enabled and sub.next_renewal_at is None
        if action=='restrict_shop':
            assert user.restricted_at and (await database.scalar(select(UserSession))).revoked_at
            with pytest.raises(HTTPException) as e:await shop.create_user_session(database,user,request())
            assert e.value.status_code==403
        else:assert user.restricted_at is None
