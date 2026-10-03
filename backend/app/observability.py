"""Bounded, non-personal operational gauges shared by all API replicas."""
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from .models import Job, Payment, RefundRequest, Subscription, SupportTicket, WorkerState

STATUS_METRICS = (
    ('vpnshop_jobs', Job, ('queued', 'processing', 'completed', 'failed')),
    ('vpnshop_payments', Payment, ('pending', 'paid', 'fulfilled', 'failed', 'cancelled', 'refunded')),
    ('vpnshop_refunds', RefundRequest, ('requested', 'approved', 'processing', 'refunded', 'failed', 'review')),
    ('vpnshop_support_tickets', SupportTicket, ('open', 'in_progress', 'answered', 'closed')),
)


def gauge(name, description, values):
    return f'# HELP {name} {description}\n# TYPE {name} gauge\n' + ''.join(
        f'{name}{labels} {value}\n' for labels, value in values)


async def operational_metrics(db):
    now = datetime.utcnow()
    lines=[]
    for name, model, statuses in STATUS_METRICS:
        rows=(await db.execute(select(model.status, func.count()).group_by(model.status))).all()
        counts=dict(rows)
        other=sum(count for status, count in rows if status not in statuses)
        lines.append(gauge(name, 'Current database records by bounded status',
            [(f'{{status="{status}"}}', int(counts.get(status, 0))) for status in statuses]+[('{status="other"}', other)]))
    oldest=await db.scalar(select(func.min(Job.created_at)).where(Job.status == 'queued'))
    seconds=max(0, (now-oldest).total_seconds()) if oldest else 0
    online=await db.scalar(select(func.count()).select_from(WorkerState).where(
        WorkerState.status == 'online', WorkerState.last_seen_at >= now-timedelta(seconds=90)))
    active=await db.scalar(select(func.count()).select_from(Subscription).where(
        Subscription.lifecycle_status.in_(['active','cancel_scheduled','grace']),
        or_(Subscription.expires_at.is_(None), Subscription.expires_at > now)))
    lines.extend([
        gauge('vpnshop_oldest_queued_job_seconds','Age of oldest queued job including retry backoff',[('',round(seconds,3))]),
        gauge('vpnshop_workers_online','Workers with heartbeat within ninety seconds',[('',int(online or 0))]),
        gauge('vpnshop_subscriptions_active','Current locally active subscriptions, not a remote VPN probe',[('',int(active or 0))]),
        gauge('vpnshop_database_metrics_available','One when this scrape read database metrics',[('',1)]),
    ])
    return ''.join(lines)
