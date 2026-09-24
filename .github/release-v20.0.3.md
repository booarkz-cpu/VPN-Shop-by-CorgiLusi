# v20.0.3

Версия приложения в коде остаётся `20.0.0`. Этот релиз закрывает ошибки, найденные после 20.0.2.

## Русский

- Заказ с суммой 0 или меньше отклоняется до вызова кассы. Скидка 100% не создаёт оплаченную подписку.
- Stripe и PayPal проводят заказ только после ответа API провайдера. Сумма, валюта и номер заказа должны совпасть. Потерянный вебхук закрывает фоновая сверка.
- Криптошлюз больше не остаётся в `pending` навсегда. Статус читается `GET {CRYPTO_GATEWAY_URL}/payments/{id}`. Вебхук `POST /api/webhooks/crypto` требует `X-Timestamp` не старше 5 минут и HMAC-SHA256 тела ключом `CRYPTO_GATEWAY_KEY`.
- Повтор выдачи в панели работает только для платежа со статусом `paid`.
- Покупатель не может сам включить `tax_exempt` или `reverse_charge`.
- Обновление ссылки подписки из панели Remnawave не удлиняет оплаченный срок.
- Песочница подтверждает только точный идентификатор `sandbox-{order_id}` и положительную сумму.

## English

The application version in code stays `20.0.0`. This release closes bugs found after 20.0.2.

- An order of amount 0 or less is refused before the gateway is called. A 100% discount does not create a paid subscription.
- Stripe and PayPal apply an order only after the provider API answers. Amount, currency and order id must match. A lost webhook is closed by background reconciliation.
- A crypto payment no longer stays `pending` forever. Status is read with `GET {CRYPTO_GATEWAY_URL}/payments/{id}`. `POST /api/webhooks/crypto` requires `X-Timestamp` within 5 minutes and HMAC-SHA256 of the body using `CRYPTO_GATEWAY_KEY`.
- An admin fulfillment retry runs only for a payment whose status is `paid`.
- A buyer cannot turn on `tax_exempt` or `reverse_charge`.
- Refreshing the subscription URL from the Remnawave panel does not extend the paid expiry.
- Sandbox confirmation accepts only the exact id `sandbox-{order_id}` and a positive amount.

## Українська

Версія застосунку в коді лишається `20.0.0`. Цей реліз закриває помилки, знайдені після 20.0.2.

- Замовлення з сумою 0 або менше відхиляється до виклику каси. Знижка 100% не створює оплачену підписку.
- Stripe і PayPal проводять замовлення лише після відповіді API провайдера. Сума, валюта і номер замовлення мають збігтися. Втрачений вебхук закриває фонова звірка.
- Криптоплатіж більше не лишається в `pending` назавжди. Статус читається `GET {CRYPTO_GATEWAY_URL}/payments/{id}`. Вебхук `POST /api/webhooks/crypto` вимагає `X-Timestamp` не старший за 5 хвилин і HMAC-SHA256 тіла ключем `CRYPTO_GATEWAY_KEY`.
- Повтор видачі в панелі працює лише для платежу зі статусом `paid`.
- Покупець не може сам увімкнути `tax_exempt` або `reverse_charge`.
- Оновлення посилання підписки з панелі Remnawave не подовжує оплачений строк.
- Пісочниця підтверджує лише точний ідентифікатор `sandbox-{order_id}` і додатну суму.
