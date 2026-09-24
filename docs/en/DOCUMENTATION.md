# Shop documentation

How VPN Shop by Corgi Lusi is put together, and the order of a purchase. The product map is in [README.md](README.md).

## Purchase flow

1. The buyer opens the cabinet or the Mini App. The storefront calls `GET /api/plans` and `GET /api/public/config`. The public plan list does not include `remnawave_profile_id`.
2. `POST /api/payments/create` requires an `Idempotency-Key` header and a buyer session. The same key returns the existing charge and does not open a second one.
3. Amount, term, traffic, devices and promo code are written on the `payments` row before the gateway is called. A later plan edit does not change that snapshot.
4. The gateway returns an id and a URL. The row becomes `pending`, except for sandbox: sandbox sets `paid` and runs fulfillment immediately.
5. A live webhook checks the signature or the IP allowlist, then asks the provider for status again. Amount, currency and order id must match.
6. Fulfillment takes the user lock and the payment lock. It creates or extends the Remnawave user and stores `subscription_url` and the expiry on `subscriptions`.
7. A repeated webhook finds the event in `payment_provider_events` and does not add the term again.
8. A refund moves the payment into revoke. A late success webhook does not fulfill it.

If Remnawave returns an error, the payment stays `paid` and `fulfillment_status` becomes `failed`. The worker retries until the attempt limit.

## Sandbox

`backend/app/sandbox_mode.py` allows sandbox only when `PAYMENTS_SANDBOX=true` and `APP_ENV` is one of development, dev, test, testing, staging, sandbox.

`startup()` stops the process if the flag is on in any other environment. `SandboxProvider` and `POST /api/payments/sandbox/complete` follow the same rule.

When the request omits the provider and no live key is set, routing selects `sandbox`. An explicit `yookassa` is not rewritten to sandbox while the production gate is closed.

Without `REMNAWAVE_URL` and `REMNAWAVE_TOKEN`, sandbox fulfillment writes a local subscription `sandbox://local/{user}/{payment}` and uuid `sandbox-user-{id}`. When the panel is configured, sandbox calls the real Remnawave API.

An empty database with sandbox allowed receives a plan named "Тестовый месяц".

## Sessions

The administrator password is stored as scrypt. The token is JWT HS256 signed with `APP_SECRET`, plus a session row. The token carries `jti`. No session row means no access.

An admin session ends after 15 minutes without a request and when the User-Agent changes. Changing role, password or email revokes every session of that operator.

The cabinet buyer receives the `rw_user` cookie. State-changing requests compare `X-CSRF-Token` with the `rw_csrf` cookie. The local `http://127.0.0.1` test needs `COOKIE_SECURE=false` and `COOKIE_SAMESITE=lax`. On production HTTPS keep `COOKIE_SECURE=true`.

The apps send `X-Shop-Client`, `X-Shop-Time` and `X-Shop-Proof`. The signature is HMAC with `MOBILE_CLIENT_KEY`. The default key is in the app source. A custom key needs a rebuilt app. `MOBILE_REQUIRE_PROOF=false` accepts older clients that do not sign.

## Money

`payments` stores the order. `financial_ledger` stores wallet credits. A referral reward is written once per payment. A fulfillment retry does not create a second reward.

`POST /api/me/wallet/spend` requires its own `Idempotency-Key`. A second key for the same purchase in a short window returns `409`.

A promo code is reserved while the charge is open and consumed when fulfillment succeeds. An unpaid charge releases the reservation.

## Roles

`viewer` can read lists and cannot see subscription keys. `operator` manages plans, users and payments and cannot manage administrators. `admin` adds operators, refunds and the live-payment flag.

The key permission is `users.keys`. A user card without that permission does not include the subscription link.

## Containers

`docker-compose.yml` is the production set: Redis, PostgreSQL, backend, worker, bot, admin, miniapp, cabinet, Support Pro and Caddy. Database ports are not published. Caddy listens on 80 and 443, sends `/api` to the backend, and sends the rest to the matching panel.

`docker-compose.test.yml` is the local set without the bot, Caddy or Support Pro. Each panel proxies `/api` to the backend so the cookie stays on the same port.

The backend runs `alembic upgrade head` on start. Do not edit the schema by hand.

## Directories

| Path | Contents |
| --- | --- |
| `backend/app/main.py` | Shop HTTP routes and fulfillment |
| `backend/app/payments.py` | YooKassa, Platega, RollyPay, sandbox |
| `backend/app/payment_platform.py` | Stripe, PayPal, crypto, app stores |
| `backend/app/remnawave.py` | Panel client |
| `backend/app/security.py` | Passwords, JWT, permissions |
| `backend/alembic/versions` | Migrations |
| `admin`, `cabinet`, `miniapp` | Three Vite interfaces |
| `mobile` | Android and iOS sources |
| `scripts/test-up.sh` | Local start without gateways |
| `scripts/sandbox-e2e.sh` | Registration and sandbox check |
| `docs/ru`, `docs/en`, `docs/uk` | This documentation |

Older release notes stay in the repository root. A new install only needs `docs`.

## Audit 20.0.3

A zero-amount order is not created. Stripe, PayPal and the crypto gateway are included in reconciliation: payment is taken from the provider API, not from the webhook body. The crypto webhook `POST /api/webhooks/crypto` checks the HMAC and the timestamp. An admin retry fulfills only a `paid` payment. A buyer cannot set `tax_exempt` or `reverse_charge`. Refreshing a Remnawave subscription does not extend the paid expiry.

## Audit 20.0.2

An Apple receipt is accepted only after the App Store Server API answers. A Google Play receipt is accepted only for an active subscription. The shop plan and the store product must both match `MOBILE_STORE_PRODUCTS`. An empty product map refuses both purchases. Stripe and PayPal webhooks grant a subscription only when the amount and currency match the order, and Stripe also requires `payment_status=paid`. A gift card credits the wallet only in the shop currency.
