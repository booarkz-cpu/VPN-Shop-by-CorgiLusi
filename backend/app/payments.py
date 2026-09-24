"""
Модуль интеграции с платежными системами.

Провайдеры: YooKassa, Platega, RollyPay.

Безопасность:
- YooKassa: проверка IP-адреса отправителя по allowlist.
- Platega: HMAC-SHA256 подпись вебхука.
- RollyPay: HMAC-SHA256 + проверка timestamp.
- Защита от replay-атак (окно 5 минут для RollyPay).
- Идемпотентность по event_id (YooKassa).
- HTTP-клиент с таймаутами и keep-alive.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from ipaddress import ip_address, ip_network
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _public_client(timeout_seconds: int):
    """Исходящие запросы к платёжным API идут только через DNS-pinned клиент."""
    from .main import _pinned_public_http_client
    return _pinned_public_http_client(timeout_seconds)
