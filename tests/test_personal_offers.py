from types import SimpleNamespace
from datetime import datetime,timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select,func
from sqlalchemy.ext.asyncio import AsyncSession

from app import main as shop,personal_offers as offers
from app.models import PromoCode,PromoAudience,PromoGroup,PromoReservation,User,Subscription
from test_subscription_commerce import database
from test_admin_customer_operations import request

ADMIN=SimpleNamespace(email='marketing@example.test',role='admin')


@pytest.mark.asyncio
async def test_personal_offer_price_reservation_scope_and_disable(database):
    db=database
    result=await offers.create_offer(offers.NewOfferIn(code='ONLY_OWNER',value=25,title='Special',user_ids=[1],version=0),db,ADMIN)
    assert result['version']==1
    promo,discount=await shop.promo_discount(db,'ONLY_OWNER',1,100,1)
    assert discount==25
    for uid in (2,None):
        with pytest.raises(HTTPException):await shop.promo_discount(db,'ONLY_OWNER',1,100,uid)
    listed=await offers.offers(request(),offset=0,limit=30,db=db)
    assert listed['items'][0]['code']=='ONLY_OWNER' and 'user_ids' not in listed['items'][0]
    await offers.set_audience(result['promo_id'],offers.AudienceIn(title='Special',user_ids=[1],version=1,enabled=False),db,ADMIN)
    # A quote made before revocation cannot reserve a now-disabled audience.
    with pytest.raises(HTTPException):await shop.reserve_promo(db,promo,1,'stale-order')
    assert await db.scalar(select(func.count(PromoCode.id)))==1
    with pytest.raises(HTTPException):await offers.create_offer(offers.NewOfferIn(code='ONLY_OWNER',value=20,title='Other',user_ids=[2],version=0),db,ADMIN)
    assert await db.scalar(select(func.count(PromoAudience.promo_id)))==1


@pytest.mark.asyncio
async def test_group_updates_segment_eligibility_and_stale_configuration(database):
    db=database
    group=await offers.create_group(offers.GroupIn(name='VIP',user_ids=[1]),db,ADMIN)
    result=await offers.create_offer(offers.NewOfferIn(code='VIP',value=10,title='VIP offer',group_id=group['id'],version=0),db,ADMIN)
    assert await offers.audience_allowed(db,result['promo_id'],1)
    assert not await offers.audience_allowed(db,result['promo_id'],2)
    group=await offers.update_group(group['id'],offers.GroupIn(name='VIP',user_ids=[2],version=1),db,ADMIN)
    assert not await offers.audience_allowed(db,result['promo_id'],1)
    assert await offers.audience_allowed(db,result['promo_id'],2)
    with pytest.raises(HTTPException):await offers.update_group(group['id'],offers.GroupIn(name='Stale',user_ids=[1],version=1),db,ADMIN)
    with pytest.raises(HTTPException):await offers.set_audience(result['promo_id'],offers.AudienceIn(title='Stale',user_ids=[1],version=0),db,ADMIN)
    for segment,owner,other in [('active',True,False),('expired',False,False),('new',True,True),('referred',False,False)]:
        group=await offers.update_group(group['id'],offers.GroupIn(name='Dynamic',segment=segment,version=group['version']),db,ADMIN)
        assert await offers.audience_allowed(db,result['promo_id'],1)==owner
        assert await offers.audience_allowed(db,result['promo_id'],2)==other
    user=await db.get(User,2);user.referred_by_id=1;await db.commit()
    assert await offers.audience_allowed(db,result['promo_id'],2)
    group=await offers.update_group(group['id'],offers.GroupIn(name='Disabled',segment='referred',enabled=False,version=group['version']),db,ADMIN)
    assert not await offers.audience_allowed(db,result['promo_id'],2)


@pytest.mark.asyncio
async def test_offer_existing_quota_and_admin_history_deletion_guard(database):
    result=await offers.create_offer(offers.NewOfferIn(code='ONCE',value=10,title='Once',user_ids=[1],version=0),database,ADMIN)
    promo,discount=await shop.promo_discount(database,'ONCE',1,100,1)
    await shop.reserve_promo(database,promo,1,'one');await database.commit()
    with pytest.raises(HTTPException):await shop.promo_discount(database,'ONCE',1,100,1)
    with pytest.raises(HTTPException) as e:await shop.delete_promo_code(result['promo_id'],database,ADMIN)
    assert e.value.status_code==409


@pytest.mark.asyncio
async def test_wallet_offer_reserves_quota_before_queued_fulfillment(database,monkeypatch):
    async def queued(*args,**kwargs):raise RuntimeError('VPN temporarily unavailable')
    monkeypatch.setattr(shop,'fulfill',queued)
    await offers.create_offer(offers.NewOfferIn(code='WALLET_ONCE',value=25,title='Wallet',user_ids=[1],version=0),database,ADMIN)
    result=await shop.wallet_spend({'plan_id':1,'promo_code':'WALLET_ONCE'},request('wallet-one'),database)
    assert result['fulfillment']=='queued'
    assert (await database.get(User,1)).wallet_balance==925
    assert (await database.scalar(select(PromoCode))).reserved_count==1
    reservation=await database.scalar(select(PromoReservation))
    reservation.expires_at=datetime.utcnow()-timedelta(days=1);await database.commit()
    assert await shop.cleanup_expired_promo_reservations(database,datetime.utcnow())==0
    assert reservation.status=='reserved'
    again=await shop.wallet_spend({'plan_id':1,'promo_code':'WALLET_ONCE'},request('wallet-one'),database)
    assert again['payment_id']==result['payment_id']
    with pytest.raises(HTTPException):await shop.wallet_spend({'plan_id':2,'promo_code':'WALLET_ONCE'},request('wallet-two'),database)
    assert (await database.get(User,1)).wallet_balance==925


@pytest.mark.asyncio
async def test_http_audience_permissions_and_paginated_privacy(database):
    import httpx
    from fastapi import FastAPI
    from app.db import get_db
    from app.security import current_admin
    app=FastAPI();app.include_router(offers.router)
    actor=SimpleNamespace(email=ADMIN.email,role='viewer')
    async def db():yield database
    async def admin():return actor
    app.dependency_overrides[get_db]=db;app.dependency_overrides[current_admin]=admin
    body={'code':'PRIVATE','value':10,'title':'Private','user_ids':[1],'version':0}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        assert (await client.get('/api/admin/promo-groups')).status_code==403
        assert (await client.post('/api/admin/personal-offers',json=body)).status_code==403
        actor.role='operator'
        r=await client.post('/api/admin/personal-offers',json=body);assert r.status_code==200,r.text
        r=await client.get('/api/me/offers?limit=1');assert r.status_code==200
        assert r.json()['next_offset']==1 and 'user_ids' not in r.text
        assert r.headers['cache-control']=='private, no-store'
        assert (await client.get('/api/me/offers?offset=1&limit=1')).json()=={'items':[],'next_offset':None}


@pytest.mark.asyncio
async def test_postgres_same_offer_code_is_atomic(database):
    import asyncio
    if database.bind.dialect.name!='postgresql':pytest.skip('PostgreSQL unique race')
    async def create():
        async with AsyncSession(database.bind,expire_on_commit=False) as db:
            try:return await offers.create_offer(offers.NewOfferIn(code='ONE_CODE',value=10,title='One',user_ids=[1],version=0),db,ADMIN)
            except HTTPException as e:return e.status_code
    result=await asyncio.gather(create(),create())
    assert sum(isinstance(x,dict) for x in result)==1 and 409 in result
    assert await database.scalar(select(func.count(PromoCode.id)))==1
    assert await database.scalar(select(func.count(PromoAudience.promo_id)))==1
