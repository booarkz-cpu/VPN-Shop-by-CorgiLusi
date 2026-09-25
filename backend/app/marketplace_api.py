from __future__ import annotations
import hashlib, hmac, secrets
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_db
from .models import Reseller, Plan, Promotion, User, Subscription, ReferralLedger, Payment
from .security import require_permission

router = APIRouter(prefix="/api", tags=["corgi-marketplace"])


def _key_hash(key: str) -> str:
    return hmac.new(settings.app_secret.encode(), key.encode(), hashlib.sha256).hexdigest()


class ResellerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    commission_percent: Decimal = Field(default=Decimal("20"), ge=0, le=100)
    plan_ids: list[int] = Field(default_factory=list)
    branding: dict = Field(default_factory=dict)


class ResellerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    commission_percent: Decimal | None = Field(default=None, ge=0, le=100)
    plan_ids: list[int] | None = None
    branding: dict | None = None
    enabled: bool | None = None


async def _reseller_from_request(request: Request, db: AsyncSession) -> Reseller:
    raw = request.headers.get("Authorization", "")
    if not raw.startswith("Bearer "):
        raise HTTPException(401, "Reseller API key required")
    digest = _key_hash(raw[7:].strip())
    row = (await db.execute(select(Reseller).where(Reseller.api_key_hash == digest, Reseller.enabled.is_(True)))).scalar_one_or_none()
    if not row:
        raise HTTPException(401, "Invalid reseller API key")
    row.last_used_at = datetime.utcnow()
    await db.commit()
    return row


@router.get("/admin/marketplace/resellers")
async def list_resellers(admin=Depends(require_permission("referrals.read")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Reseller).order_by(Reseller.id.desc()))).scalars().all()
    return [{"id": r.id, "name": r.name, "slug": r.slug, "commission_percent": str(r.commission_percent),
             "plan_ids": r.plan_ids or [], "branding": r.branding or {}, "enabled": r.enabled,
             "created_at": r.created_at.isoformat(), "last_used_at": r.last_used_at.isoformat() if r.last_used_at else None} for r in rows]


@router.post("/admin/marketplace/resellers")
async def create_reseller(payload: ResellerCreate, admin=Depends(require_permission("referrals.reconcile")), db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(Reseller).where(Reseller.slug == payload.slug))
    if existing:
        raise HTTPException(409, "Reseller slug already exists")
    raw_key = "corgi_rsk_" + secrets.token_urlsafe(32)
    row = Reseller(name=payload.name, slug=payload.slug, commission_percent=payload.commission_percent,
                   plan_ids=payload.plan_ids, branding=payload.branding, api_key_hash=_key_hash(raw_key), enabled=True)
    db.add(row); await db.commit(); await db.refresh(row)
    return {"id": row.id, "name": row.name, "slug": row.slug, "api_key": raw_key,
            "commission_percent": str(row.commission_percent), "plan_ids": row.plan_ids or [], "branding": row.branding or {}}


@router.patch("/admin/marketplace/resellers/{reseller_id}")
async def update_reseller(reseller_id: int, payload: ResellerUpdate, admin=Depends(require_permission("referrals.reconcile")), db: AsyncSession = Depends(get_db)):
    row = await db.get(Reseller, reseller_id)
    if not row: raise HTTPException(404, "Reseller not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    await db.commit(); return {"ok": True, "id": row.id}


@router.post("/admin/marketplace/resellers/{reseller_id}/rotate-key")
async def rotate_reseller_key(reseller_id: int, admin=Depends(require_permission("referrals.reconcile")), db: AsyncSession = Depends(get_db)):
    row = await db.get(Reseller, reseller_id)
    if not row: raise HTTPException(404, "Reseller not found")
    raw_key = "corgi_rsk_" + secrets.token_urlsafe(32)
    row.api_key_hash = _key_hash(raw_key); await db.commit()
    return {"ok": True, "api_key": raw_key}


@router.get("/reseller/catalog")
async def reseller_catalog(request: Request, db: AsyncSession = Depends(get_db)):
    reseller = await _reseller_from_request(request, db)
    query = select(Plan).where(Plan.enabled.is_(True))
    if reseller.plan_ids:
        query = query.where(Plan.id.in_(reseller.plan_ids))
    plans = (await db.execute(query.order_by(Plan.id))).scalars().all()
    return {"reseller": {"slug": reseller.slug, "name": reseller.name, "branding": reseller.branding or {}},
            "plans": [{"id": p.id, "name": p.name, "price": str(p.price), "duration_days": p.duration_days,
                       "traffic_limit_gb": p.traffic_limit_gb, "device_limit": p.device_limit} for p in plans]}


@router.get("/reseller/stats")
async def reseller_stats(request: Request, db: AsyncSession = Depends(get_db)):
    reseller = await _reseller_from_request(request, db)
    # Payments are already linked to users; reseller attribution is represented by the
    # referral ledger source_user_id when a reseller uses referral links.
    gross = await db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.reseller_id == reseller.id, Payment.status == "paid"))
    commission = (Decimal(str(gross or 0)) * reseller.commission_percent / Decimal("100")).quantize(Decimal("0.01"))
    return {"reseller": reseller.slug, "gross_paid": str(gross or Decimal("0")), "commission_estimate": str(commission), "commission_percent": str(reseller.commission_percent)}


@router.get("/reseller/branding")
async def reseller_branding(request: Request, db: AsyncSession = Depends(get_db)):
    reseller = await _reseller_from_request(request, db)
    return {"name": reseller.name, "slug": reseller.slug, "branding": reseller.branding or {}}
