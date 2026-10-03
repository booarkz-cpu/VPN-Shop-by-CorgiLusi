import asyncio
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
from sqlalchemy import select,func
from sqlalchemy.ext.asyncio import AsyncSession

from app import content_publishing as content
from app.db import get_db
from app.models import ContentPage,ContentRevision,AuditLog
from app.security import current_admin
from test_subscription_commerce import database

ADMIN=SimpleNamespace(email='editor@example.test',role='admin')
DATA={'slug':'terms','kind':'legal','title':'Terms','blocks':[{'kind':'text','title':'Read this','text':'<script>alert(1)</script>'}]}


def test_content_bounds_links_and_timezone():
    assert content.PageIn(**DATA).locale=='ru'
    for url in ('javascript:alert(1)','data:text/html,hi','//other.test','/\\other.test','https://user:password@example.test','https://example.test/\nhi','https://'):
        with pytest.raises(ValidationError):content.Block(kind='cta',url=url,label='Open')
    for url in ('#plans','/help','https://example.test/help'):
        assert content.Block(kind='cta',url=url,label='Open').url==url
    for patch in ({'title':' '},{'blocks':[]},{'blocks':[{'kind':'faq'}]},{'starts_at':'2026-10-03T12:00:00'},{'ends_at':'2026-10-02T12:00:00Z','starts_at':'2026-10-03T12:00:00Z'}, {'slug':'../admin'},{'locale':'xx'},{'html':'<script/>'}):
        with pytest.raises(ValidationError):content.PageIn(**{**DATA,**patch})
    with pytest.raises(ValidationError):content.PageIn(**{**DATA,'blocks':[{'kind':'text','text':'a'*10000}]*30})
    data=content.PageIn(**{**DATA,'starts_at':'2030-01-02T12:00:00+03:00'})
    assert content.payload(data)['starts_at']=='2030-01-02T09:00:00Z'


@pytest.mark.asyncio
async def test_draft_publish_edit_restore_archive_and_stale_versions(database):
    db=database;p=await content.create(content.PageIn(**DATA),db,ADMIN)
    assert await content.catalog(offset=0,limit=50,db=db)==[]
    with pytest.raises(HTTPException):await content.public_page('terms',db=db)
    p=await content.publish(p['id'],content.VersionIn(version=1),db,ADMIN)
    public=await content.public_page('terms',db=db)
    assert public['revision']==2 and public['blocks'][0]['text']=='<script>alert(1)</script>'
    assert not {'actor','draft','id','archived'}&public.keys()
    # Editing never changes the immutable published snapshot.
    p=await content.save(p['id'],content.SaveIn(**{**DATA,'title':'New terms','version':2}),db,ADMIN)
    assert (await content.public_page('terms',db=db))['title']=='Terms'
    with pytest.raises(HTTPException) as e:await content.publish(p['id'],content.VersionIn(version=2),db,ADMIN)
    assert e.value.status_code==409
    p=await content.publish(p['id'],content.VersionIn(version=3),db,ADMIN)
    assert (await content.public_page('terms',db=db))['title']=='New terms'
    revisions=await content.revisions(p['id'],offset=0,limit=50,db=db)
    assert [r['version'] for r in revisions]==[4,2]
    p=await content.restore(p['id'],content.RestoreIn(version=4,revision=2),db,ADMIN)
    assert p['draft']['title']=='Terms' and (await content.public_page('terms',db=db))['title']=='New terms'
    p=await content.archive(p['id'],content.VersionIn(version=5),db,ADMIN)
    assert p['archived'] and await content.catalog(offset=0,limit=50,db=db)==[]
    with pytest.raises(HTTPException):await content.public_page('terms',db=db)
    p=await content.publish(p['id'],content.VersionIn(version=6),db,ADMIN)
    assert (await content.public_page('terms',db=db))['title']=='Terms'
    with pytest.raises(HTTPException):await content.save(p['id'],content.SaveIn(**{**DATA,'slug':'other','version':7}),db,ADMIN)
    assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action.like('content.%')))==7


@pytest.mark.asyncio
async def test_schedule_locale_and_slug_uniqueness(database):
    db=database;tomorrow=datetime.now(timezone.utc)+timedelta(days=1)
    p=await content.create(content.PageIn(**{**DATA,'starts_at':tomorrow,'ends_at':tomorrow+timedelta(days=1)}),db,ADMIN)
    await content.publish(p['id'],content.VersionIn(version=1),db,ADMIN)
    assert await content.catalog(offset=0,limit=50,db=db)==[]
    with pytest.raises(HTTPException):await content.public_page('terms',db=db)
    p=await content.create(content.PageIn(**{**DATA,'locale':'en'}),db,ADMIN)
    await content.publish(p['id'],content.VersionIn(version=1),db,ADMIN)
    assert (await content.catalog(locale='en',offset=0,limit=50,db=db))[0]['slug']=='terms'
    with pytest.raises(HTTPException) as e:await content.create(content.PageIn(**DATA),db,ADMIN)
    assert e.value.status_code==409
    # Past-end publication cannot be activated; source drafts remain editable.
    p=await content.create(content.PageIn(**{**DATA,'slug':'expired','ends_at':tomorrow-timedelta(days=2)}),db,ADMIN)
    with pytest.raises(HTTPException):await content.publish(p['id'],content.VersionIn(version=1),db,ADMIN)


@pytest.mark.asyncio
async def test_http_permissions_and_private_drafts(database):
    app=FastAPI();app.include_router(content.admin_router);app.include_router(content.public_router)
    actor=SimpleNamespace(email=ADMIN.email,role='viewer')
    async def db():yield database
    async def admin():return actor
    app.dependency_overrides[get_db]=db;app.dependency_overrides[current_admin]=admin
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        assert (await client.get('/api/admin/pages')).status_code==403
        assert (await client.post('/api/admin/pages',json=DATA)).status_code==403
        actor.role='operator'
        response=await client.post('/api/admin/pages',json=DATA);assert response.status_code==200,response.text
        p=response.json();assert response.headers['cache-control']=='private, no-store'
        assert (await client.get('/api/public/pages/terms')).status_code==404
        response=await client.post(f"/api/admin/pages/{p['id']}/publish",json={'version':1});assert response.status_code==200,response.text
        actor.role='viewer'
        assert (await client.get(f"/api/admin/pages/{p['id']}/revisions")).status_code==403
        response=await client.get('/api/public/pages/terms');assert response.status_code==200
        assert response.headers['cache-control']=='private, no-store' and 'actor' not in response.json()


@pytest.mark.asyncio
async def test_postgres_two_editors_cannot_publish_same_version(database):
    if database.bind.dialect.name!='postgresql':pytest.skip('PostgreSQL row-lock race')
    page=await content.create(content.PageIn(**DATA),database,ADMIN)
    async def publish():
        async with AsyncSession(database.bind,expire_on_commit=False) as db:
            try:return await content.publish(page['id'],content.VersionIn(version=1),db,ADMIN)
            except HTTPException as e:await db.rollback();return e.status_code
    results=await asyncio.gather(publish(),publish())
    assert sum(isinstance(x,dict) for x in results)==1 and 409 in results
    assert await database.scalar(select(func.count(ContentRevision.id)))==1
