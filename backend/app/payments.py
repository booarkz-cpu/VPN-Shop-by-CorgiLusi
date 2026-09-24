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


def _money(amount) -> str:
    return f"{Decimal(str(amount)).quantize(Decimal('0.01')):.2f}"


def _checkout(data: Dict[str, Any]) -> Dict[str, Any]:
    confirmation = data.get("confirmation") or {}
    url = confirmation.get("confirmation_url") or data.get("url") or data.get("redirect") or data.get("paymentUrl") or data.get("link")
    payment_id = data.get("id") or data.get("payment_id") or data.get("transactionId") or data.get("transaction_id")
    return {"id": payment_id, "url": url, "status": data.get("status") or data.get("Status")}


# ============================================================
# Исключения
# ============================================================

class PaymentError(Exception):
    """Базовое исключение для ошибок платежных систем."""


class SignatureVerificationError(PaymentError):
    """Ошибка проверки вебхука (подпись или IP)."""


class WebhookReplayError(PaymentError):
    """Ошибка повторного использования вебхука (replay attack)."""


class WebhookAlreadyProcessedError(PaymentError):
    """Вебхук с таким event_id уже был обработан."""


# ============================================================
# Базовый провайдер
# ============================================================

class BasePaymentProvider(ABC):
    """Абстрактный базовый класс для платежных провайдеров."""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Клиент с фиксацией DNS. Нельзя открывать прямой httpx.AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = _public_client(20)
        return self._client

    async def close(self) -> None:
        """Закрыть HTTP-клиент."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @abstractmethod
    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Создать платеж."""
        raise NotImplementedError

    @abstractmethod
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Получить статус платежа."""
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(
        self,
        headers: Dict[str, str],
        body: bytes,
        remote_addr: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Проверить вебхук и вернуть его данные."""
        raise NotImplementedError


# ============================================================
# YooKassa Provider
# ============================================================

class YooKassaProvider(BasePaymentProvider):
    """
    Провайдер YooKassa.

    Проверка вебхука выполняется по IP-адресу отправителя
    (allowlist из настроек) + идемпотентность по event_id.
    """

    def __init__(self) -> None:
        super().__init__()
        self._processed_events: Dict[str, datetime] = {}
        self._event_ttl = timedelta(hours=24)

    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        client = await self._get_client()
        # The shop order id is the idempotency key. A lost response must return the
        # same YooKassa payment instead of opening a second charge.
        idempotence_key = str(metadata.get("order_id") or uuid.uuid4())

        payload: Dict[str, Any] = {
            "amount": {"value": f"{amount:.2f}", "currency": currency},
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": metadata.get(
                    "return_url", settings.public_base_url
                ),
            },
            "description": description,
            "metadata": metadata,
        }

        email = metadata.get("email")
        if email:
            payload["receipt"] = {
                "customer": {"email": email},
                "items": [
                    {
                        "description": description,
                        "quantity": "1.00",
                        "amount": {
                            "value": f"{amount:.2f}",
                            "currency": currency,
                        },
                        "vat_code": 1,
                    }
                ],
            }

        response = await client.post(
            f"{settings.yookassa_api_url}/v3/payments",
            auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
            headers={
                "Idempotence-Key": idempotence_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        client = await self._get_client()
        response = await client.get(
            f"{settings.yookassa_api_url}/v3/payments/{payment_id}",
            auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
        )
        response.raise_for_status()
        data = response.json()
        return str(data.get("status") or "")

    async def refund_payment(
        self, payment_id: str, amount: float, currency: str
    ) -> Dict[str, Any]:
        client = await self._get_client()
        payload = {
            "payment_id": payment_id,
            "amount": {"value": f"{amount:.2f}", "currency": currency},
        }
        response = await client.post(
            f"{settings.yookassa_api_url}/v3/refunds",
            auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
            headers={"Idempotence-Key": str(uuid.uuid4())},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def _verify_ip(self, remote_addr: Optional[str]) -> None:
        """Проверить IP-адрес отправителя по allowlist. Пустой список отклоняет вебхук."""
        if not settings.yookassa_webhook_ip_allowlist:
            raise SignatureVerificationError("YooKassa webhook IP allowlist is not configured")
        if not remote_addr:
            raise SignatureVerificationError("Missing remote address for YooKassa webhook")

        allowed = [
            ip_network(n.strip())
            for n in settings.yookassa_webhook_ip_allowlist.split(",")
            if n.strip()
        ]

        try:
            addr = ip_address(remote_addr)
        except ValueError:
            raise SignatureVerificationError(
                f"Некорректный IP: {remote_addr}"
            )

        if not any(addr in net for net in allowed):
            raise SignatureVerificationError(
                f"IP {remote_addr} не входит в allowlist YooKassa"
            )

    def verify_webhook(
        self,
        headers: Dict[str, str],
        body: bytes,
        remote_addr: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Проверить вебхук YooKassa:
        1. IP-адрес (allowlist).
        2. Парсинг JSON.
        3. Идемпотентность по event_id.
        """
        # 1. IP
        self._verify_ip(remote_addr)

        # 2. JSON
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise PaymentError(f"Невалидный JSON в вебхуке: {e}")

        # 3. Идемпотентность. Тип события ("payment.succeeded") одинаков у всех
        # уведомлений, поэтому ключом служит уникальный id уведомления или платежа.
        obj = data.get("object") or {}
        event_id = data.get("id") or obj.get("id")
        if event_id:
            self._cleanup_old_events()
            if event_id in self._processed_events:
                raise WebhookAlreadyProcessedError(
                    f"Событие {event_id} уже обработано"
                )
            self._processed_events[event_id] = datetime.now(timezone.utc)

        return data

    def _cleanup_old_events(self) -> None:
        """Удалить старые записи из кэша обработанных событий."""
        now = datetime.now(timezone.utc)
        expired = [
            eid
            for eid, ts in self._processed_events.items()
            if now - ts > self._event_ttl
        ]
        for eid in expired:
            del self._processed_events[eid]

    async def create(self, amount: Decimal, order_id: str, description: str, return_url: str) -> Dict[str, Any]:
        data = await self.create_payment(float(amount), settings.default_currency, description, {"order_id": order_id, "return_url": return_url})
        return _checkout(data)

    async def charge_recurring(self, amount: Decimal, order_id: str, description: str, payment_method_id: str) -> Dict[str, Any]:
        """Повторное списание сохранённым способом оплаты. Idempotence-Key = order_id."""
        payload = {
            "amount": {"value": _money(amount), "currency": settings.default_currency},
            "capture": True,
            "payment_method_id": payment_method_id,
            "description": description,
            "metadata": {"order_id": order_id},
        }
        async with _public_client(10) as client:
            response = await client.post(
                f"{settings.yookassa_api_url}/v3/payments",
                auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
                headers={"Idempotence-Key": order_id, "Content-Type": "application/json"},
                json=payload,
            )
        response.raise_for_status()
        return _checkout(response.json())
