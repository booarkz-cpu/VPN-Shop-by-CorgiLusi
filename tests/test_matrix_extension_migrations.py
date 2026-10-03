import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.models import CustomerPasskey, SupportTopologyOperation, PartnerWithdrawal, Reseller, CustomerBatchOperation
from test_subscription_commerce import database


def migration(name):
    path=Path('backend/alembic/versions')/(name+'.py')
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_postgres_new_migrations_roundtrip_and_history_guards(database):
    if database.bind.dialect.name!='postgresql':pytest.skip('PostgreSQL DDL')
    names=['0058_customer_operations','0057_partner_commissions','0056_support_topology','0055_customer_passkeys']
    for name in names:
        module=migration(name)
        async with database.bind.begin() as conn:
            def cycle(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    module.downgrade();module.upgrade()
            await conn.run_sync(cycle)
    partner=Reseller(name='Test',slug='test',api_key_hash='hash',owner_user_id=1)
    database.add(partner);await database.flush()
    database.add(PartnerWithdrawal(reseller_id=partner.id,amount=1,currency='RUB',destination='Test',idempotency_key='one'))
    database.add(CustomerPasskey(user_id=1,credential_id='credential',public_key='key',name='Test'))
    database.add(SupportTopologyOperation(key='key',fingerprint='fingerprint',result={}))
    database.add(CustomerBatchOperation(key='key',fingerprint='fingerprint',result={}))
    await database.commit()
    for name in names:
        module=migration(name)
        async with database.bind.begin() as conn:
            def guarded(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    with pytest.raises(RuntimeError):module.downgrade()
            await conn.run_sync(guarded)
