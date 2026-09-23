"""Transactional event outbox. Capture changes in the same DB transaction."""
import uuid
from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session
from .models import Ticket, Message, CallRequest, WorkItem, Settings, Team, Holiday, now
from .sla import utc, DEFAULTS, business_seconds, business_add
from datetime import timedelta

@event.listens_for(Session, 'before_flush')
def prepare(session, context, instances):
    changes = session.info.setdefault('support_events', [])
    for obj in list(session.new) + list(session.dirty):
        if isinstance(obj, Ticket):
            fresh = obj in session.new
            state = inspect(obj)
            status = state.attrs.status.history
            if status.has_changes():
                if obj.status == 'pending' and not obj.paused_at:
                    obj.paused_at = now()
                elif obj.status != 'pending' and obj.paused_at:
                    row=session.get(Settings,1)
                    config=dict(row.data if row else DEFAULTS)
                    team=session.get(Team,obj.team_id) if obj.team_id else None
                    if team:config.update(team.calendar)
                    config['exceptions']={h.day.date().isoformat():h.is_working for h in session.scalars(select(Holiday)).all()} | config.get('exceptions',{})
                    elapsed=business_seconds(obj.paused_at,now(),config)
                    obj.paused_seconds=(obj.paused_seconds or 0)+int(elapsed)
                    for field in ('first_response_due','sla_deadline'):
                        due=getattr(obj,field)
                        if due and utc(due)>utc(obj.paused_at):
                            remaining=business_seconds(obj.paused_at,due,config)
                            setattr(obj,field,business_add(now(),remaining/60,config))
                    obj.paused_at = None
            if not session.info.get('automation') and (fresh or session.is_modified(obj)):
                changes.append((obj, 'ticket.created' if fresh else 'ticket.updated'))
        elif isinstance(obj, Message):
            if obj in session.new: changes.append((obj, 'message.created'))
            elif inspect(obj).attrs.delivery_state.history.has_changes() and obj.delivery_state == 'sent':
                changes.append((obj, 'message.sent'))
        elif isinstance(obj, CallRequest) and obj in session.new:
            changes.append((obj, 'call.created'))

@event.listens_for(Session, 'after_flush_postexec')
def enqueue(session, context):
    for obj, name in session.info.pop('support_events', []):
        tid = obj.id if isinstance(obj, Ticket) else obj.ticket_id
        session.add(WorkItem(key=str(uuid.uuid4()), kind='event', event=name, ticket_id=tid,
                             payload={'ticket_id': tid, 'record_id': obj.id}, state='queued'))

@event.listens_for(Session, 'after_soft_rollback')
def clear(session, previous):
    session.info.pop('support_events', None)
