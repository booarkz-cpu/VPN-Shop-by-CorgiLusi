# Security / Безопасность — Remnawave VPN Shop 3.1.6

## Аудит 20.0.3 / 20.0.3 audit

- Заказ с суммой 0 или меньше не уходит в кассу и не становится оплаченным. Сверка Stripe, PayPal и криптошлюза читает статус у провайдера и сравнивает сумму, валюту и номер заказа. Вебхук `POST /api/webhooks/crypto` без `CRYPTO_GATEWAY_KEY`, со старым `X-Timestamp` или с неверной HMAC-подписью отклоняется. Повтор выдачи не переводит неоплаченный заказ в подписку. Поля `tax_exempt` и `reverse_charge` из профиля покупателя не принимаются. `POST /api/me/remnawave/subscription/refresh` не копирует более поздний срок из панели.
- An order of amount 0 or less is not sent to a gateway and is not marked paid. Stripe, PayPal and crypto reconciliation read the provider status and compare amount, currency and order id. `POST /api/webhooks/crypto` is refused without `CRYPTO_GATEWAY_KEY`, with a stale `X-Timestamp`, or with a bad HMAC. An admin retry does not turn an unpaid order into a subscription. Buyer-supplied `tax_exempt` and `reverse_charge` are ignored. `POST /api/me/remnawave/subscription/refresh` does not copy a later expiry from the panel.
