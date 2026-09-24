## Русский

Аудит 20.0.2 закрывает выдачу подписки без оплаты.

- Чек Apple больше не принимается из браузера сам по себе. Нужны `transactionId`, ключи App Store Server API и подписанная транзакция из ответа Apple. Отозванная транзакция отклоняется.
- Чек Google Play принимается только при `SUBSCRIPTION_STATE_ACTIVE`.
- `MOBILE_STORE_PRODUCTS` связывает id продукта магазина с id тарифа. Пустая карта отклоняет обе покупки. Чужой продукт нельзя применить к более дорогому тарифу.
- Вебхук Stripe проводит заказ только если `payment_status` равен `paid`, а сумма и валюта совпали с заказом.
- Вебхук PayPal проводит заказ только если сумма захвата и валюта совпали с заказом.
- Подарочная карта зачисляется только в валюте магазина (`DEFAULT_CURRENCY`).

Версия приложения остаётся 20.0.0. Это исправление поверх 20.0.1, где стенд и VDS сами открывают порты.

## English

The 20.0.2 audit closes subscription grants that did not require a real charge.

- An Apple receipt from the browser is no longer proof of payment. The shop requires a `transactionId`, App Store Server API keys, and the signed transaction from Apple's response. A revoked transaction is refused.
- A Google Play receipt is accepted only when the state is `SUBSCRIPTION_STATE_ACTIVE`.
- `MOBILE_STORE_PRODUCTS` maps a store product id to a shop plan id. An empty map refuses both purchases. A cheaper product cannot be applied to a more expensive plan.
- A Stripe webhook applies an order only when `payment_status` is `paid` and the amount and currency match.
- A PayPal webhook applies an order only when the captured amount and currency match.
- A gift card is credited only in the shop currency (`DEFAULT_CURRENCY`).

The application version remains 20.0.0. This fix follows 20.0.1, where the test stand and the VDS open their own ports.

## Українська

Аудит 20.0.2 закриває видачу підписки без оплати.

- Чек Apple більше не приймається з браузера сам по собі. Потрібні `transactionId`, ключі App Store Server API і підписана транзакція з відповіді Apple. Відкликана транзакція відхиляється.
- Чек Google Play приймається лише при `SUBSCRIPTION_STATE_ACTIVE`.
- `MOBILE_STORE_PRODUCTS` пов’язує id продукту крамниці з id тарифу. Порожня карта відхиляє обидві покупки. Дешевший продукт не можна застосувати до дорожчого тарифу.
- Вебхук Stripe проводить замовлення лише якщо `payment_status` дорівнює `paid`, а сума і валюта збіглися із замовленням.
- Вебхук PayPal проводить замовлення лише якщо сума захоплення і валюта збіглися із замовленням.
- Подарункова картка зараховується лише у валюті магазину (`DEFAULT_CURRENCY`).

Версія застосунку лишається 20.0.0. Це виправлення після 20.0.1, де стенд і VDS самі відкривають порти.
