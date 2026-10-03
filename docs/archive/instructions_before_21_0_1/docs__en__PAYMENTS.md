**v20.0.8:** The current runner does not verify webhook delivery or fulfillment. Live payments remain gated. See the [full procedure](STAGING_E2E_20_0_8.md).

# Connecting payment gateways

The shop creates a charge at the provider and grants a subscription only after the provider confirms the same amount, currency and order id. A webhook alone does not grant access until that check succeeds.

Live charges are also closed by `payments.production_gate`. While it is off, `POST /api/payments/create` returns `503` even when the keys are set. Sandbox does not use this flag, and sandbox is refused in production. Deploy the shop first, using [DEPLOYMENT.md](DEPLOYMENT.md).

## 1. Pick a provider

Fill in only the keys you will use. An empty key removes that provider from routing.

| Provider | Required variables | Webhook |
| --- | --- | --- |
| YooKassa | `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_WEBHOOK_IP_ALLOWLIST` | `POST https://API_DOMAIN/api/webhooks/yookassa` |
| Platega | `PLATEGA_MERCHANT_ID`, `PLATEGA_SECRET` | `POST https://API_DOMAIN/api/webhooks/platega` |
| RollyPay | `ROLLYPAY_API_KEY`, `ROLLYPAY_SIGNING_SECRET` | `POST https://API_DOMAIN/api/webhooks/rollypay` |
| Stripe | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | the Stripe webhook route on the API |
| PayPal | `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID` | the PayPal webhook route on the API |
| Crypto gateway | `CRYPTO_GATEWAY_URL`, `CRYPTO_GATEWAY_KEY` | as agreed with that gateway |

`YOOKASSA_API_URL` defaults to `https://api.yookassa.ru`. `PLATEGA_API_URL` defaults to `https://app.platega.io`. `ROLLYPAY_API_URL` defaults to `https://rollypay.io`. Change them only when the provider gives another host. The host is checked as a public URL.

Platega and RollyPay refunds need their own URLs: `PLATEGA_REFUND_URL`, `PLATEGA_REFUND_STATUS_URL`, `ROLLYPAY_REFUND_URL`, `ROLLYPAY_REFUND_STATUS_URL`. Without them a refund fails with a configuration error instead of a silent success.

`ROLLYPAY_TEST_MODE=true` sends RollyPay's own test flag. That is not the shop sandbox.

## 2. YooKassa

1. Copy the shop id and secret key from the YooKassa dashboard.
2. Set `YOOKASSA_SHOP_ID` and `YOOKASSA_SECRET_KEY`.
3. Point payment notifications at `https://API_DOMAIN/api/webhooks/yookassa`.
4. Put the networks YooKassa sends from into `YOOKASSA_WEBHOOK_IP_ALLOWLIST`, separated by commas. An empty list rejects every notification. The shop uses the address of the nearest proxy, not a client-supplied `X-Forwarded-For` value.
5. Restart the backend and worker: `docker compose up -d`.

A receipt is sent only when the user has an email.

## 3. Platega

1. Set the merchant id and secret.
2. Point the Platega webhook at `https://API_DOMAIN/api/webhooks/platega`.
3. The notification must send `X-MerchantId` and `X-Secret` matching `.env`. A different secret is rejected.
4. Before fulfillment the shop reads the transaction from Platega and checks the amount and `payload` against the order id.

## 4. RollyPay

1. Set the API key and signing secret.
2. Point the webhook at `https://API_DOMAIN/api/webhooks/rollypay`.
3. The notification must include `X-Signature` (HMAC-SHA256 of the body) and `X-Timestamp`. A timestamp older than five minutes is rejected. A missing timestamp is rejected too, so a captured notification cannot be replayed later.
4. Before fulfillment the shop reads the payment from RollyPay and checks the amount and `order_id`.

## 5. Open live charges

Keys are not enough. You need a full staging run: charge, webhook, fulfillment, the same webhook again, and a refund. The result must be less than 24 hours old.

In the panel, as an `admin` (permission `security.manage`), open the staging check, save staging keys that do not match the production keys in `.env`, and wait for a pass. Then enable live payments. `POST /api/admin/payments/production-gate` with `{"enabled": true}` does the same and returns `409` when the check is stale or incomplete.

Turn charges off at once with `{"enabled": false}`.

While the flag is off, the buyer sees “Реальные платежи временно заблокированы”. That is expected.

## 6. Check one payment

1. Create a plan with a small price.
2. Register a test buyer in the cabinet.
3. Pay with the chosen gateway.
4. Return to the cabinet. Billing shows the payment `paid` and fulfillment `completed`.
5. Open the subscription link. It must be an `https://` Remnawave URL, not `sandbox://`.
6. Deliver the same webhook again. The second delivery must not add another term.
7. Refund from the panel. Access must be revoked, and a late success webhook must not grant it again.

## 7. Auto-renew

`AUTO_RENEW_ENABLED=true` can store a YooKassa payment method and charge the next period. Sandbox does not run recurring charges. Leave auto-renew off until a manual staging refund has succeeded.

## 8. Do not

- Do not set `PAYMENTS_SANDBOX=true` on a host that already has buyers. `APP_ENV=production` refuses to start, and that stop is intentional.
- Do not paste production keys into the staging form. Saving rejects keys that match `.env`.
- Do not publish PostgreSQL so you can flip the flag by hand on a public server. Use the panel route.

## 9. Apple, Google, Stripe and PayPal

`MOBILE_STORE_PRODUCTS` is a JSON object. The key is the App Store or Google Play product id. The value is the shop plan id. Example: `{"com.shop.month": 1}`. An empty value refuses `POST /api/payments/mobile/verify`. An Apple receipt without a `transactionId`, or without App Store Server API keys, is also refused. A Google Play receipt is accepted only when the state is `SUBSCRIPTION_STATE_ACTIVE` and the product in Google's answer is in this map.

Stripe webhook: `POST /api/payments/webhooks/stripe`. The subscription is granted only when `payment_status` is `paid` and `amount_total` plus currency match the order. A checkout the buyer finished but has not paid yet does not grant access.

PayPal webhook: `POST /api/payments/webhooks/paypal`. The captured amount and currency must match the order. A different amount is not applied.

A gift card credits the wallet only when its currency equals `DEFAULT_CURRENCY`.

A zero order amount is refused before the gateway is called. Stripe and PayPal grant access only after the provider API confirms the same amount, currency and `order_id`. The crypto gateway is confirmed with `GET {CRYPTO_GATEWAY_URL}/payments/{id}` and `POST /api/webhooks/crypto`. The signature is header `X-Timestamp` (unix seconds, five-minute window) and `X-Signature`, the hex HMAC-SHA256 of `{timestamp}.{raw body}` using `CRYPTO_GATEWAY_KEY`. A buyer cannot mark their own invoice tax exempt.
