"""Poll canonical shop threads and deliver through its idempotent API.

Scanning repeatedly by ticket id avoids timestamp watermarks losing late commits.
Every page and message cursor is committed only after its files are persisted.
"""
import base64
import hashlib
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
import httpx
from sqlalchemy import select,func
from .models import Ticket, Message, Attachment, Client, ShopSyncState, WorkItem, PortalAccess, now
from .storage import checked_path, new_path, scan_file
from .services import settings, assign, notify
from .sla import set_deadlines, utc

MAX_BYTES=2*1024*1024

class BridgeError(ValueError):pass

class ClientAPI:
    def __init__(self):
        self.origin=os.getenv('SHOP_BRIDGE_URL','').rstrip('/')
        self.token=os.getenv('SHOP_BRIDGE_TOKEN','')
        self.instance=os.getenv('SHOP_BRIDGE_INSTANCE','')
        self._client=None
        u=urlsplit(self.origin)
        if not self.origin or len(self.token)<32 or not re.fullmatch(r'[A-Za-z0-9_-]{8,40}',self.instance):
            raise BridgeError('Укажите SHOP_BRIDGE_URL, TOKEN и постоянный INSTANCE')
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or u.path:
            raise BridgeError('SHOP_BRIDGE_URL должен быть HTTPS origin без пути и credentials')
    async def __aenter__(self):
        from .outbound import _pinned_public_http_client
        self._client=_pinned_public_http_client(20)
        await self._client.__aenter__();return self
    async def __aexit__(self,*args):
        await self._client.__aexit__(*args);self._client=None
    async def request(self,method,path,payload=None,key=None):
        if self._client is None:
            async with self:return await self.request(method,path,payload,key)
        headers={'Authorization':'Bearer '+self.token,'X-Support-Instance':self.instance}
        if key:headers['Idempotency-Key']=key
        response=await self._client.request(method,self.origin+'/api/internal/support-bridge'+path,json=payload,headers=headers)
        if response.status_code>=400:
            # Do not copy provider response bodies, URLs or credentials to logs.
            raise BridgeError(f'Магазин отклонил операцию: HTTP {response.status_code}')
        if response.is_redirect:raise BridgeError('Перенаправление интеграции запрещено')
        return response.json()


def enabled():return bool(os.getenv('SHOP_BRIDGE_URL',''))

def validate_file(name,data):
    if not data or len(data)>MAX_BYTES:raise BridgeError('Вложения магазина: до 2 МБ')
    ext=name.rsplit('.',1)[-1].lower()
    if ext=='png' and data.startswith(b'\x89PNG\r\n\x1a\n'):return 'image/png'
    if ext in ('jpg','jpeg') and data.startswith(b'\xff\xd8\xff'):return 'image/jpeg'
    if ext=='pdf' and data.startswith(b'%PDF-'):return 'application/pdf'
    if ext=='txt' and b'\0' not in data:
        try:data.decode('utf-8');return 'text/plain'
        except UnicodeDecodeError:pass
    raise BridgeError('Вложения магазина: только PNG, JPEG, PDF и UTF-8 TXT')

async def send_files(api,s,ticket,message,import_source_id=None):
    items=(await s.scalars(select(Attachment).where(Attachment.message_id==message.id).order_by(Attachment.id))).all()
    if len(items)>3:raise BridgeError('Не более трёх вложений в сообщении')
    ids=[]
    for item in items:
        if item.state!='ready':raise BridgeError('Вложение ещё не загружено')
        if item.shop_attachment_id:
            ids.append(item.shop_attachment_id);continue
        path=checked_path(item.path)
        if path.stat().st_size>MAX_BYTES:raise BridgeError('Вложения магазина: до 2 МБ')
        data=path.read_bytes();validate_file(item.filename,data)
        upload_path=f'/imports/{import_source_id}/attachments' if import_source_id else f'/tickets/{ticket.shop_ticket_id}/attachments'
        result=await api.request('POST',upload_path,
            {'name':item.filename,'content_base64':base64.b64encode(data).decode()},f'sp:{api.instance}:file:{item.id}')
        item.shop_attachment_id=result['id'];ids.append(item.shop_attachment_id)
        await s.commit() # Persist before sending the message; upload retries use the same key.
    return ids

async def deliver(s,ticket,message,api=None):
    if api is None:
        async with ClientAPI() as owned:return await deliver(s,ticket,message,owned)
    await binding(s,api)
    if message.sender not in ('operator','user'):
        message.delivery_state='sent';message.sent_at=now();await s.commit();return
    files=await send_files(api,s,ticket,message)
    kind='reply' if message.sender=='operator' else 'customer'
    body={'body':message.text or 'Вложение','attachment_ids':files}
    if kind=='customer':body['user_id' if ticket.telegram_user_id<0 else 'telegram_id']=abs(ticket.telegram_user_id)
    result=await api.request('POST',f'/tickets/{ticket.shop_ticket_id}/'+('reply' if kind=='reply' else 'customer-message'),body,
        f'sp:{api.instance}:{kind}:{message.id}')
    # Never advance the read cursor here: earlier incoming messages may not be mirrored yet.
    message.delivery_state='sent';message.sent_at=now();message.text_sent=True;message.attachment_sent=True;message.error=''
    ticket=await s.scalar(select(Ticket).where(Ticket.id==ticket.id).execution_options(populate_existing=True).with_for_update())
    if kind=='reply':
        ticket.first_response_at=ticket.first_response_at or now()
        latest=await s.scalar(select(Message).where(Message.ticket_id==ticket.id,Message.sender=='user').order_by(Message.id.desc()).limit(1))
        if not latest or utc(latest.created_at)<=utc(message.created_at):ticket.waiting_since=None
        if ticket.status=='new':ticket.status='open'
    await s.commit()
    return result

async def purge(s,ticket):
    files=(await s.scalars(select(Attachment).where(Attachment.ticket_id==ticket.id))).all()
    for item in files:
        try:checked_path(item.path).unlink()
        except ValueError:pass
        await s.delete(item)
    rows=(await s.scalars(select(Message).where(Message.ticket_id==ticket.id))).all()
    for m in rows:
        m.text='[Аккаунт удалён]';m.delivery_state='internal';m.error='';m.telegram_message_id=None
    ticket.subject='Удалённый аккаунт';ticket.username='';ticket.full_name='';ticket.status='closed';ticket.waiting_since=None
    c=await s.get(Client,ticket.telegram_user_id)
    other=await s.scalar(select(func.count()).select_from(Ticket).where(Ticket.telegram_user_id==ticket.telegram_user_id,Ticket.shop_ticket_id.is_(None)))
    if c and not other:
        c.full_name='Удалённый аккаунт';c.username='';c.notes='';c.tags=''
        for access in (await s.scalars(select(PortalAccess).where(PortalAccess.client_id==ticket.telegram_user_id))).all():access.revoked=True

async def mirror(s,item,api):
    s.info['shop_pull']=True
    paths=[]
    try:
        ticket=await s.scalar(select(Ticket).where(Ticket.shop_ticket_id==item['id']).with_for_update())
        if ticket and ticket.shop_import_until_id is not None and not ticket.shop_import_complete and not item['deleted']:return
        if not ticket:
            if item['deleted']:return
            client_id=-item['user_id'] # Reserved shop identity; never send it to Telegram.
            client=await s.get(Client,client_id)
            if not client:
                client=Client(telegram_user_id=client_id,full_name=f"Клиент магазина #{item['user_id']}",username=item['username'] or '')
                s.add(client);await s.flush()
            ticket=Ticket(telegram_user_id=client_id,username=client.username,full_name=client.full_name,
                subject=item['subject'],priority='normal',channel='shop',shop_ticket_id=item['id'],status='new',created_at=utc(datetime.fromisoformat(item['created_at'])))
            set_deadlines(ticket,await settings(s));s.add(ticket);await s.flush()
            await assign(s,ticket)
        if item['deleted']:
            await purge(s,ticket);await s.commit();return
        after=ticket.shop_last_message_id if ticket.shop_initial_loaded else 0
        page=await api.request('GET',f'/tickets/{item["id"]}/messages?after={after}')
        if page.get('deleted'):
            await purge(s,ticket);await s.commit();return
        for remote in page['messages']:
            if remote['id']==0 and ticket.shop_initial_loaded:continue
            key=f'shop:{item["id"]}:{remote["id"]}'
            message=await s.scalar(select(Message).where(Message.source_key==key))
            source=remote.get('source_key') or ''
            match=re.fullmatch(r'sp:'+re.escape(api.instance)+r':(reply|customer|import):(\d+)',source)
            if not message and match:
                original=await s.get(Message,int(match[2]))
                if original and original.ticket_id==ticket.id:
                    message=original
                    if match[1]!='import':message.delivery_state='sent';message.error='';message.sent_at=now()
            if not message:
                date=utc(datetime.fromisoformat(remote['created_at']))
                message=Message(ticket_id=ticket.id,sender='user' if remote['role']=='customer' else 'operator',text=remote['body'],
                    source_key=key,created_at=date,delivery_state='received' if remote['role']=='customer' else 'sent')
                s.add(message);await s.flush()
                if remote['role']=='customer':
                    ticket.last_customer_message_id=message.id;ticket.waiting_since=date
                    if ticket.status in ('closed','pending'):ticket.status='open';ticket.closed_at=None
                    await notify(s,ticket,f'Новое сообщение из магазина в #{ticket.id}',key)
                else:
                    ticket.first_response_at=ticket.first_response_at or date
                    ticket.waiting_since=None
            for file in remote.get('attachments',[]):
                if await s.scalar(select(Attachment.id).where(Attachment.shop_attachment_id==file['id'])):continue
                raw=await api.request('GET',f'/attachments/{file["id"]}')
                data=base64.b64decode(raw['content_base64'],validate=True)
                mime=validate_file(raw['name'],data)
                if hashlib.sha256(data).hexdigest()!=file['sha256']:raise BridgeError('Контрольная сумма вложения не совпала')
                path=new_path(raw['name']);paths.append(path);path.write_bytes(data);await scan_file(path)
                s.add(Attachment(ticket_id=ticket.id,message_id=message.id,filename=raw['name'],path=str(path),
                    content_type=mime,size=len(data),shop_attachment_id=file['id']))
            ticket.shop_last_message_id=max(ticket.shop_last_message_id,remote['id'])
        ticket.shop_initial_loaded=True
        ticket.subject=item['subject']
        if page['next_cursor'] is None:
            if page['status']=='resolved':ticket.status='closed';ticket.closed_at=ticket.closed_at or now()
            elif ticket.status=='closed':ticket.status='open';ticket.closed_at=None
        await s.commit()
        return page['next_cursor'] is not None
    except BaseException:
        await s.rollback()
        for path in paths:path.unlink(missing_ok=True)
        raise
    finally:s.info.pop('shop_pull',None)

async def binding(s,api):
    state=await s.scalar(select(ShopSyncState).where(ShopSyncState.id==1).with_for_update())
    if not state:
        state=ShopSyncState(id=1,origin=api.origin,instance=api.instance,after_id=0);s.add(state);await s.flush()
    if state.origin and (state.origin,state.instance)!=(api.origin,api.instance):
        raise BridgeError('Изменение origin/instance требует отдельного переноса существующих связей')
    state.origin=api.origin;state.instance=api.instance
    return state

async def poll(session_factory,api=None):
    if api is None:
        async with ClientAPI() as owned:return await poll(session_factory,owned)
    async with session_factory() as control:
        state=await binding(control,api)
        page=await api.request('GET',f'/tickets?after={state.after_id}')
        if control.bind.dialect.name=='sqlite':await control.commit()
        recent=await api.request('GET','/tickets/recent')
        items={item['id']:item for item in page['items']}
        items.update({item['id']:item for item in recent['items']})
        for item in items.values():
            async with session_factory() as s:await mirror(s,item,api)
        state.after_id=page['next_cursor'] or 0
        state.last_success=now();state.error='';await control.commit()
    return len(page['items'])

async def status_one(session_factory,api=None):
    if api is None:
        async with ClientAPI() as owned:return await status_one(session_factory,owned)
    async with session_factory() as s:
        job=await s.scalar(select(WorkItem).where(WorkItem.kind=='shop_status',WorkItem.state.in_(('queued','sending')),WorkItem.due_at<=now())
            .order_by(WorkItem.id).with_for_update(skip_locked=True).limit(1))
        if not job:return False
        await binding(s,api)
        job.state='sending';job.attempts+=1;job.due_at=now()+timedelta(minutes=2);await s.commit()
        ticket=await s.scalar(select(Ticket).where(Ticket.id==job.ticket_id).execution_options(populate_existing=True).with_for_update())
        desired='resolved' if ticket.status=='closed' else 'open'
        if desired!=job.payload['status'] or ticket.shop_last_message_id!=job.payload['expected_message_id']:
            job.state='cancelled';job.error='Более новое состояние обращения';await s.commit();return True
        try:
            await api.request('POST',f'/tickets/{ticket.shop_ticket_id}/status',job.payload)
            job.state='done';job.error=''
        except BridgeError as exc:
            job.error=str(exc)
            if 'HTTP 409' in str(exc):
                job.state='cancelled';await notify(s,ticket,'Статус магазина изменился. Обновите переписку перед закрытием.',f'shop-status:{job.id}')
            else:job.state='dead' if job.attempts>=8 else 'queued'
        except Exception:
            job.error='Магазин недоступен; повтор с прежними условиями';job.state='dead' if job.attempts>=8 else 'queued'
        job.due_at=now()+timedelta(seconds=min(3600,10*2**job.attempts));await s.commit()
    return True
