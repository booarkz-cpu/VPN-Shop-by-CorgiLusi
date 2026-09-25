"""Execute payment and identity regressions; PostgreSQL cases run in CI."""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import importlib
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import uuid

import httpx
import jwt
import pytest
import pytest_asyncio
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


@pytest.fixture
def shop(monkeypatch, tmp_path):
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.setenv('MEDIA_DIR', str(tmp_path / 'media'))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'backend'))
    return importlib.import_module('app.main')


@pytest.mark.asyncio
@pytest.mark.parametrize('provider,body', [
    ('PlategaProvider', {'status': 'CONFIRMED', 'amount': '100', 'payload': 'order'}),
    ('RollyPayProvider', {'status': 'paid', 'amount': '100', 'order_id': 'order'}),
])
@pytest.mark.parametrize('currency,accepted', [('RUB', True), ('rub', True), ('USD', False), ('', False), (None, False)])
async def test_provider_requires_matching_currency(shop, monkeypatch, provider, body, currency, accepted):
    from app import payments
    body = {**body, 'currency': currency}
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=body))
    monkeypatch.setattr(payments, '_public_client', lambda _: httpx.AsyncClient(transport=transport))
    assert await getattr(payments, provider)().verify_succeeded('id', Decimal('100'), 'RUB', 'order') is accepted


@pytest.mark.asyncio
@pytest.mark.parametrize('provider,body', [
    ('platega', {'status': 'CONFIRMED', 'amount': '100', 'payload': 'order'}),
    ('rollypay', {'status': 'paid', 'amount': '100', 'order_id': 'order'}),
])
async def test_staging_also_rejects_wrong_currency(shop, monkeypatch, provider, body):
    from app.payments import staging_read_payment
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={**body, 'currency': 'USD'}))
    monkeypatch.setattr(shop, 'validate_public_url', lambda value, **kw: value)
    monkeypatch.setattr(shop, '_pinned_public_http_client', lambda _: httpx.AsyncClient(transport=transport))
    result = await staging_read_payment(provider, {'api_url': 'https://pay.example'}, 'id', Decimal('100'), 'order')
    assert result['paid'] is False


@pytest.mark.asyncio
async def test_vk_cannot_merge_an_email_password_account(shop, monkeypatch):
    from app.cabinet_api import vk_callback
    monkeypatch.setattr(shop.settings, 'vk_client_secret', 'test')
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={'user_id': 7, 'email': 'victim@example.com'}))
    monkeypatch.setattr(shop, '_pinned_public_http_client', lambda _: httpx.AsyncClient(transport=transport))
    state = jwt.encode({'exp': datetime.now(timezone.utc) + timedelta(minutes=5)}, shop.settings.app_secret, algorithm='HS256')
    request = Request({'type': 'http', 'headers': [(b'cookie', f'vk_oauth_state={state}'.encode())]})
    existing = SimpleNamespace(vk_id=None, email_password_hash='attacker-password')
    db = SimpleNamespace(execute=AsyncMock(side_effect=[None, Mock(scalar_one_or_none=lambda: None), Mock(scalar_one_or_none=lambda: existing)]), commit=AsyncMock(), add=Mock())
    with pytest.raises(HTTPException) as error:
        await vk_callback('code', state, request, db)
    assert error.value.status_code == 409
    assert existing.vk_id is None
    db.commit.assert_not_awaited()
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_deleted_user_cannot_receive_a_session(shop):
    db = SimpleNamespace(add=Mock(), commit=AsyncMock())
    with pytest.raises(HTTPException) as error:
        await shop.create_user_session(db, SimpleNamespace(deleted_at=datetime.utcnow()), None)
    assert error.value.status_code == 401
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_admin_session_must_belong_to_token_subject(shop, monkeypatch):
    from app import security
    monkeypatch.setattr(security, 'decode_token', lambda _: {'type': 'admin', 'sub': '1', 'jti': 'session', 'mfa': True})
    request = Request({'type': 'http', 'headers': []})
    admin = SimpleNamespace(id=1, disabled=False)
    session = SimpleNamespace(admin_id=2, expires_at=datetime.utcnow() + timedelta(hours=1))
    db = SimpleNamespace(get=AsyncMock(return_value=admin), execute=AsyncMock(return_value=Mock(scalar_one_or_none=lambda: session)), commit=AsyncMock())
    with pytest.raises(HTTPException) as error:
        await security.current_admin(request, SimpleNamespace(credentials='token'), db)
    assert error.value.status_code == 401
    db.commit.assert_not_awaited()


@pytest_asyncio.fixture
async def pg(shop):
    url = os.environ.get('AUDIT_TEST_DATABASE_URL') or (os.environ.get('DATABASE_URL') if os.environ.get('CI') else None)
    if not url:
        pytest.skip('PostgreSQL integration requires AUDIT_TEST_DATABASE_URL (provided in CI)')
    schema = 'audit_' + uuid.uuid4().hex
    root = create_async_engine(url)
    async with root.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine = create_async_engine(url, connect_args={'server_settings': {'search_path': schema}})
    from app.models import User, Payment, FinancialLedger
    try:
        async with engine.begin() as conn:
            for model in (User, Payment, FinancialLedger):
                await conn.run_sync(model.__table__.create)
        yield engine
    finally:
        await engine.dispose()
        async with root.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        await root.dispose()


async def seed_wallet(engine, balance='100', fulfilled=True):
    from app.models import User, Payment
    async with AsyncSession(engine, expire_on_commit=False) as db:
        user = User(wallet_balance=Decimal(balance))
        db.add(user)
        await db.flush()
        payment = Payment(user_id=user.id, plan_id=0, order_id='topup', provider='yookassa', amount=Decimal('100'), currency='RUB', purpose='topup', status='refunded', fulfillment_status='completed' if fulfilled else 'pending')
        db.add(payment)
        await db.commit()
        return user.id, payment.id


@pytest.mark.asyncio
@pytest.mark.parametrize('balance,fulfilled,expected', [('100', True, '0'), ('20', True, '-80'), ('20', False, '20')])
async def test_wallet_refund_is_atomic_and_repeat_safe(shop, pg, balance, fulfilled, expected):
    from app.models import User, Payment, FinancialLedger
    uid, pid = await seed_wallet(pg, balance, fulfilled)
    async with AsyncSession(pg, expire_on_commit=False) as db:
        payment = await db.get(Payment, pid)
        # A top-up must never query or disable a VPN subscription.
        await shop._safe_revoke_for_refunded_payment(db, payment, 'test', 'refund')
        await db.commit()
        await shop._safe_revoke_for_refunded_payment(db, payment, 'test', 'refund')
        await db.commit()
        assert await db.scalar(select(User.wallet_balance).where(User.id == uid)) == Decimal(expected)
        rows = (await db.scalars(select(FinancialLedger))).all()
        assert len(rows) == (1 if fulfilled else 0)


@pytest.mark.asyncio
async def test_concurrent_wallet_refunds_debit_once(shop, pg):
    from app.models import User, Payment, FinancialLedger
    uid, pid = await seed_wallet(pg)
    async def reverse():
        async with AsyncSession(pg, expire_on_commit=False) as db:
            payment = await db.get(Payment, pid)
            await shop._safe_revoke_for_refunded_payment(db, payment, 'test', 'refund')
            await db.commit()
    await asyncio.gather(reverse(), reverse())
    async with AsyncSession(pg) as db:
        assert await db.scalar(select(User.wallet_balance).where(User.id == uid)) == 0
        assert len((await db.scalars(select(FinancialLedger))).all()) == 1


@pytest.mark.asyncio
async def test_failed_ledger_insert_rolls_back_wallet_debit(shop, pg):
    from app.models import User, Payment, FinancialLedger
    uid, pid = await seed_wallet(pg)
    async with pg.begin() as conn:
        await conn.execute(text("ALTER TABLE financial_ledger ADD CONSTRAINT reject_entry CHECK (kind != 'wallet_topup_refund')"))
    async with AsyncSession(pg, expire_on_commit=False) as db:
        payment = await db.get(Payment, pid)
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            await shop._safe_revoke_for_refunded_payment(db, payment, 'test', 'refund')
        await db.commit()  # caller may persist a pending-reversal status
        assert await db.scalar(select(User.wallet_balance).where(User.id == uid)) == 100
        assert (await db.scalars(select(FinancialLedger))).all() == []


@pytest.mark.asyncio
async def test_stale_paid_snapshot_cannot_revive_refund(shop, pg, monkeypatch):
    from app.models import Payment
    _, pid = await seed_wallet(pg)
    async with AsyncSession(pg, expire_on_commit=False) as db:
        payment = await db.get(Payment, pid)
        payment.status = 'paid'
        await db.commit()
        async with AsyncSession(pg) as other:
            await other.execute(update(Payment).where(Payment.id == pid).values(status='refunded'))
            await other.commit()
        assert payment.status == 'paid'  # deliberately stale identity map
        monkeypatch.setattr(shop, '_acquire_user_fulfillment_lock', AsyncMock(return_value=('u', 't')))
        monkeypatch.setattr(shop, '_acquire_payment_side_effect_lock', AsyncMock(return_value=('p', 't')))
        monkeypatch.setattr(shop, '_release_payment_side_effect_lock', AsyncMock())
        fulfill = AsyncMock()
        monkeypatch.setattr(shop, 'fulfill', fulfill)
        result = await shop._confirm_and_fulfill_payment(pid, db)
        assert result['ignored'] is True
        fulfill.assert_not_awaited()
        assert payment.status == 'refunded'


@pytest.mark.asyncio
async def test_payment_lock_failure_releases_user_lock(shop, monkeypatch):
    db = SimpleNamespace(execute=AsyncMock(return_value=Mock(scalar_one_or_none=lambda: SimpleNamespace(user_id=1))))
    monkeypatch.setattr(shop, '_acquire_user_fulfillment_lock', AsyncMock(return_value=('user-lock', 'token')))
    monkeypatch.setattr(shop, '_acquire_payment_side_effect_lock', AsyncMock(side_effect=RuntimeError('lock unavailable')))
    release = AsyncMock()
    monkeypatch.setattr(shop, '_release_payment_side_effect_lock', release)
    with pytest.raises(RuntimeError, match='lock unavailable'):
        await shop._confirm_and_fulfill_payment(1, db)
    release.assert_awaited_once_with('user-lock', 'token')
