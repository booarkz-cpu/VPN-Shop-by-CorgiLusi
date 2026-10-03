from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from starlette.requests import Request

from app import partners, main as shop
from app.models import Payment, Reseller, PartnerCommission, PartnerWithdrawal
from test_subscription_commerce import database

ADMIN=SimpleNamespace(email='admin@example.test')


def request(key='one'):
    return Request({'type':'http','headers':[(b'idempotency-key',key.encode())]})


async def setup(db):
    partner=Reseller(name='Partner',slug='partner',owner_user_id=1,api_key_hash='hash',commission_percent=20,plan_ids=[1])
    db.add(partner);await db.flush()
    terms=await partners.checkout_terms(db,'partner',1,2)
    payment=Payment(user_id=2,plan_id=1,provider='wallet',order_id='test',amount=100,
        status='paid',fulfillment_status='completed',purpose='subscription',**terms)
    db.add(payment);await db.commit()
    return partner,payment


@pytest.mark.asyncio
async def test_immutable_commission_and_refund_never_recredit(database):
    partner,payment=await setup(database)
    partner.commission_percent=90;await database.commit()
    await partners.credit(database,payment);await partners.credit(database,payment);await database.commit()
    assert partner.balance==Decimal(20)
    assert await database.scalar(select(func.count()).select_from(PartnerCommission))==1
    await partners.reverse(database,payment);await partners.reverse(database,payment);await database.commit()
    assert partner.balance==0
    await partners.credit(database,payment);await database.commit()
    assert partner.balance==0


@pytest.mark.asyncio
async def test_withdrawal_reserve_repeat_reject_and_negative_clawback(database):
    partner,payment=await setup(database);await partners.credit(database,payment);await database.commit()
    payload=partners.WithdrawalIn(amount=15,destination='Bank reference')
    first=await partners.withdraw(payload,request(),database)
    assert (await partners.withdraw(payload,request(),database))['id']==first['id'] and partner.balance==5
    await partners.reverse(database,payment);await database.commit()
    assert partner.balance==-15
    await partners.decide(first['id'],partners.DecisionIn(status='rejected'),database,ADMIN)
    await partners.decide(first['id'],partners.DecisionIn(status='rejected'),database,ADMIN)
    assert partner.balance==0
    with pytest.raises(HTTPException):await partners.decide(first['id'],partners.DecisionIn(status='paid',reference='bank'),database,ADMIN)


@pytest.mark.asyncio
async def test_paid_payout_requires_approval_and_real_reference(database):
    partner,payment=await setup(database);await partners.credit(database,payment);await database.commit()
    first=await partners.withdraw(partners.WithdrawalIn(amount=10,destination='Bank'),request(),database)
    with pytest.raises(HTTPException):await partners.decide(first['id'],partners.DecisionIn(status='paid',reference='bank'),database,ADMIN)
    await partners.decide(first['id'],partners.DecisionIn(status='approved'),database,ADMIN)
    with pytest.raises(HTTPException):await partners.decide(first['id'],partners.DecisionIn(status='paid'),database,ADMIN)
    await partners.decide(first['id'],partners.DecisionIn(status='paid',reference='bank-123'),database,ADMIN)
    assert partner.balance==10


@pytest.mark.asyncio
async def test_partner_checkout_allowlist_self_purchase_and_private_portal(database,monkeypatch):
    partner,payment=await setup(database)
    with pytest.raises(HTTPException):await partners.checkout_terms(database,'partner',2,2)
    with pytest.raises(HTTPException):await partners.checkout_terms(database,'partner',1,1)
    portal=await partners.portal(request(),database)
    assert portal['slug']=='partner'
    async def other(*args):
        from app.models import User
        return await database.get(User,2)
    monkeypatch.setattr(shop,'user_from_token',other)
    with pytest.raises(HTTPException):await partners.portal(request(),database)


@pytest.mark.asyncio
async def test_pending_fulfillment_never_credits_and_mixed_currency_blocked(database):
    partner,payment=await setup(database);payment.fulfillment_status='pending';await database.commit()
    await partners.credit(database,payment);assert partner.balance==0
    partner.balance_currency='USD';await database.commit()
    with pytest.raises(HTTPException):await partners.checkout_terms(database,'partner',1,2)


@pytest.mark.asyncio
async def test_postgres_concurrent_credit_and_withdrawal_reservations(database):
    if database.bind.dialect.name != 'postgresql':pytest.skip('PostgreSQL reservation races')
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession
    partner,payment=await setup(database)
    async def credit():
        async with AsyncSession(database.bind,expire_on_commit=False) as db:
            await partners.credit(db,await db.get(Payment,payment.id));await db.commit()
    await asyncio.gather(credit(),credit())
    await database.refresh(partner)
    assert partner.balance==20
    await database.commit()
    async def withdraw(key):
        async with AsyncSession(database.bind,expire_on_commit=False) as db:
            try:return (await partners.withdraw(partners.WithdrawalIn(amount=15,destination='Bank'),request(key),db))['status']
            except HTTPException as exc:return exc.status_code
    assert sorted(await asyncio.gather(withdraw('first'),withdraw('second')),key=str)==[409,'requested']
    await database.refresh(partner)
    assert partner.balance==5


@pytest.mark.asyncio
async def test_wallet_checkout_freezes_partner_and_retry_survives_disabled_partner(database,monkeypatch):
    partner=Reseller(name='Owner two',slug='partner',owner_user_id=2,api_key_hash='key',commission_percent=12,plan_ids=[1])
    database.add(partner);await database.commit()
    async def no_fulfill(*args,**kwargs):pass
    monkeypatch.setattr(shop,'fulfill',no_fulfill)
    result=await shop.wallet_spend({'plan_id':1,'reseller_slug':'partner'},request(),database)
    payment=await database.get(Payment,result['payment_id'])
    assert payment.reseller_percent_snapshot==12 and payment.reseller_id==partner.id
    partner.enabled=False;partner.commission_percent=80;await database.commit()
    again=await shop.wallet_spend({'plan_id':1,'reseller_slug':'partner'},request(),database)
    assert again['payment_id']==payment.id
    with pytest.raises(HTTPException):await shop.wallet_spend({'plan_id':1},request(),database)
