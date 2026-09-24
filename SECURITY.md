# Security / Безопасность — Remnawave VPN Shop 3.1.6

## Аудит 20.0.2 / 20.0.2 audit

- Клиентский JWS Apple больше не является доказательством оплаты. Нужны `transactionId`, ключи App Store Server API и подписанная транзакция из ответа Apple. Отозванная транзакция отклоняется. `MOBILE_STORE_PRODUCTS` связывает продукт магазина с id тарифа. Пустая карта отклоняет и Apple, и Google Play. Случайный идентификатор платежа больше не создаётся.
- Вебхук Stripe проводит заказ только при `payment_status=paid` и совпадении суммы с валютой. Вебхук PayPal проводит заказ только при совпадении суммы захвата и валюты. Подарочная карта другой валюты на баланс не зачисляется.
- A client Apple JWS is no longer proof of payment. The shop requires a `transactionId`, App Store Server API keys, and the signed transaction from Apple's response. A revoked transaction is refused. `MOBILE_STORE_PRODUCTS` binds a store product to a plan id. An empty map refuses both Apple and Google Play. A random payment id is no longer created.
- A Stripe webhook applies an order only when `payment_status=paid` and the amount and currency match. A PayPal webhook applies an order only when the captured amount and currency match. A gift card in another currency is not credited.
