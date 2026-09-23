"""Corgi Lusi production control-plane contracts.

Control-plane only: no private VPN payloads are accepted or persisted.
"""
from __future__ import annotations
import hashlib, hmac, json, secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from .db import get_db
from pydantic import BaseModel, Field
from .config import settings

router = APIRouter()


async def _user_id(request: Request, db: AsyncSession) -> int:
    from .main import user_from_token
    user = await user_from_token(request, db)
    if not user:
        raise HTTPException(401, "Authentication required")
    return int(user.id)


def _canonical(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def _sign(data: dict) -> str:
    return hmac.new(settings.app_secret.encode(), _canonical(data), hashlib.sha256).hexdigest()


class TunnelRequest(BaseModel):
    platform: str = Field(min_length=2, max_length=32)
    device_id: str = Field(min_length=1, max_length=128)
    region: str = Field(default="auto", min_length=2, max_length=64)


class NodeRegister(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    endpoint: str = Field(min_length=3, max_length=255)
    public_key: str = Field(min_length=20, max_length=128)
    region: str = Field(default="auto", min_length=2, max_length=64)


class FailoverRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.post("/api/me/v16/tunnel-profile")
async def tunnel_profile(payload: TunnelRequest, request: Request, db: AsyncSession = Depends(get_db)):
    uid = await _user_id(request, db)
    profile = {
        "version": 1,
        "product": "corgi-lusi",
        "user_id": uid,
        "device_id": payload.device_id,
        "platform": payload.platform,
        "region": payload.region,
        "mode": "wireguard",
        "dns": ["1.1.1.1", "9.9.9.9"],
        "kill_switch": True,
        "split_tunnel": False,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_in": 900,
        "private_traffic_inspection": False,
    }
    profile["signature"] = _sign(profile)
    return profile


@router.post("/api/me/v16/roaming")
async def roaming(payload: TunnelRequest, request: Request, db: AsyncSession = Depends(get_db)):
    await _user_id(request, db)
    return {
        "ok": True,
        "device_id": payload.device_id,
        "strategy": "seamless",
        "handoff": "preserve-session-when-possible",
        "failover": True,
        "recommended_region": payload.region if payload.region != "auto" else "best-health",
    }


@router.post("/api/admin/v16/nodes/register")
async def register_node(payload: NodeRegister, request: Request):
    token = secrets.token_urlsafe(32)
    return {
        "ok": True,
        "node": payload.model_dump(),
        "agent_token": token,
        "provisioning": {
            "engine": "wireguard",
            "health_check": True,
            "auto_routing": True,
            "private_traffic_payloads": False,
        },
        "next": ["install node agent", "submit heartbeat", "run health check"],
    }


@router.post("/api/admin/v16/nodes/{node_name}/failover")
async def node_failover(node_name: str, payload: FailoverRequest, request: Request):
    return {"ok": True, "node": node_name, "state": "draining", "reason": payload.reason, "traffic_shift": "automatic"}


@router.get("/api/public/v16/release")
async def release():
    return {
        "product": "VPN Shop by Corgi Lusi",
        "platform": "Corgi Lusi Platform",
        "release": "16.0.0",
        "channels": ["stable", "canary", "internal"],
        "languages": ["ru", "en", "uk"],
        "privacy": {"private_traffic_inspection": False, "payload_logging": False},
    }
