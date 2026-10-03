from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from starlette.requests import Request

from app import support_topology as topology
from app.models import SupportTicket, SupportMessage, SupportAttachment, SupportTopologyOperation
from app.support_threads import append_message
from test_subscription_commerce import database

ADMIN = SimpleNamespace(email='operator@example.test')


def request(key='operation-1'):
    return Request({'type':'http','headers':[(b'idempotency-key',key.encode())]})


async def setup(db):
    a=SupportTicket(user_id=1,subject='One',message='First',admin_reply='Legacy reply')
    b=SupportTicket(user_id=1,subject='Two',message='Second')
    c=SupportTicket(user_id=2,subject='Other',message='Private')
    db.add_all([a,b,c]);await db.flush()
    x=SupportMessage(ticket_id=a.id,role='customer',body='Continue',idempotency_key='same')
    y=SupportMessage(ticket_id=b.id,role='customer',body='Continue other',idempotency_key='same')
    db.add_all([x,y]);await db.flush()
    f=SupportAttachment(ticket_id=a.id,message_id=x.id,actor='customer:1',idempotency_key='file',
        name='a.txt',mime='text/plain',data=b'secret',size=6,sha256='hash')
    db.add(f);await db.commit()
    return a,b,c,x,y,f


async def apply(db,payload,key='operation-1'):
    preview=await topology.preview(payload,db,ADMIN)
    return await topology.apply(payload.model_copy(update={'fingerprint':preview['fingerprint']}),request(key),db,ADMIN)


@pytest.mark.asyncio
async def test_merge_keeps_files_roots_legacy_reply_and_retry(database):
    a,b,c,x,y,f=await setup(database)
    payload=topology.OperationIn(kind='merge',source_id=a.id,target_id=b.id)
    preview=await topology.preview(payload,database,ADMIN)
    exact=payload.model_copy(update={'fingerprint':preview['fingerprint']})
    result=await topology.apply(exact,request(),database,ADMIN)
    assert a.status=='merged' and a.merged_into_id==b.id
    assert f.ticket_id==b.id and f.message_id==x.id and f.data==b'secret'
    rows=(await database.scalars(select(SupportMessage).where(SupportMessage.ticket_id==b.id))).all()
    assert any('First' in m.body for m in rows)
    assert any(m.body=='Legacy reply' for m in rows)
    assert x.idempotency_key!=y.idempotency_key
    assert await topology.apply(exact,request(),database,ADMIN)==result
    assert await database.scalar(select(func.count()).select_from(SupportTopologyOperation))==1
    with pytest.raises(HTTPException):await append_message(database,a,'customer','new','retry')


@pytest.mark.asyncio
async def test_split_moves_selected_messages_and_files_only(database):
    a,b,c,x,y,f=await setup(database)
    result=await apply(database,topology.OperationIn(kind='split',source_id=a.id,subject='New',message_ids=[x.id]))
    target=await database.get(SupportTicket,result['target_id'])
    assert target.user_id==a.user_id and x.ticket_id==target.id and f.ticket_id==target.id
    assert a.merged_into_id is None and b.message=='Second'
    assert any(m.body=='Legacy reply' for m in (await database.scalars(select(SupportMessage).where(SupportMessage.ticket_id==a.id))).all())


@pytest.mark.asyncio
async def test_cross_owner_and_foreign_message_rejected(database):
    a,b,c,x,y,f=await setup(database)
    with pytest.raises(HTTPException):await topology.preview(topology.OperationIn(kind='merge',source_id=a.id,target_id=c.id),database,ADMIN)
    with pytest.raises(HTTPException):await topology.preview(topology.OperationIn(kind='split',source_id=a.id,subject='New',message_ids=[y.id]),database,ADMIN)


@pytest.mark.asyncio
async def test_preview_becomes_stale_after_reply(database):
    a,b,c,x,y,f=await setup(database)
    payload=topology.OperationIn(kind='merge',source_id=a.id,target_id=b.id)
    preview=await topology.preview(payload,database,ADMIN)
    await append_message(database,a,'customer','New arrival','new');await database.commit()
    with pytest.raises(HTTPException) as error:
        await topology.apply(payload.model_copy(update={'fingerprint':preview['fingerprint']}),request(),database,ADMIN)
    assert error.value.status_code==409 and a.merged_into_id is None
