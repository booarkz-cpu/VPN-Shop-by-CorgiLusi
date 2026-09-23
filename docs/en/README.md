# VPN Shop by Corgi Lusi

A subscription shop for VPN access. A buyer picks a plan, pays, and receives a Remnawave subscription link. An operator manages plans, payments, users and the panel.

This file is the map of the product. Gateway-free startup is in [TESTING.md](TESTING.md). A server install is in [DEPLOYMENT.md](DEPLOYMENT.md). Live gateways are in [PAYMENTS.md](PAYMENTS.md). The code layout is in [DOCUMENTATION.md](DOCUMENTATION.md).

## Parts

| Part | Path | Role |
| --- | --- | --- |
| API | `backend/app/main.py` | Buyers, plans, payments, fulfillment, admin routes |
| Bot | `backend/app/bot.py` | Telegram start, prices, promo codes, Mini App button |
| Worker | `backend/worker.py` | Job queue, fulfillment retry, trials |
| Admin | `admin/` | Staff sign-in, plans, payments, users, content |
| Mini App | `miniapp/` | Purchase inside Telegram |
| Cabinet | `cabinet/` | Email sign-in, subscription, checkout, connection |
| Apps | `mobile/` | Android and iOS for the buyer and the operator |
| Support Pro | `support-pro/` | Separate ticket desk |
| Edge | `docker-compose.yml`, `deploy/Caddyfile` | HTTPS and one hostname per surface |

PostgreSQL stores the shop. Redis holds locks and short-lived markers. Schema changes go through Alembic in `backend/alembic` only.

## Buyer

- Register with email in the cabinet, or sign in with Telegram, VK or Yandex when those clients are set in `.env`.
- Open the Mini App from the bot and see the plans.
- Buy a fixed plan, or build duration, traffic and device count when a constructor is enabled.
- Apply a promo code. The price and term are stored on the payment and stay put if the plan is edited later.
- Start a trial when no active subscription exists.
- Top up an internal wallet and spend it on a plan.
- Open the subscription link, download it as a text file, and show a QR for Happ, v2rayNG and Streisand when the link is `https://`.
- Schedule cancellation at the end of the paid term.
- Review payments in the billing center.

## Operator

- Sign in with email and password. Roles are `viewer`, `operator` and `admin`. A viewer cannot read subscription keys.
- Turn on TOTP. An admin session is tied to the browser and ends after 15 idle minutes or a User-Agent change.
- Create and disable plans, constructors, promo codes, promotions and cabinet menu items.
- Inspect payments, refund a paid order, and retry fulfillment after a Remnawave error.
- Upload an APK or IPA for the app cards. Buyers download from the cabinet. Operators download from the panel.
- Queue a Telegram broadcast. The bot process delivers it.
- Turn on maintenance mode. New payments are rejected while it is on.
- Read the audit log. Panel responses do not include exception text or provider secrets.

The first administrator is created from `ADMIN_EMAIL` and `ADMIN_PASSWORD` when the admin table is empty.

## Payments

Live providers are YooKassa, Platega, RollyPay, Stripe, PayPal and the crypto gateway, once their keys are set. Apple IAP and Google Play verify a store purchase. They do not open a website checkout. SEPA does not open a redirect checkout in this code.

Until the database flag `payments.production_gate` is on, a live charge returns `503`. The flag turns on only after a staging end-to-end run that is less than 24 hours old. Sandbox checkout does not need that flag.

Sandbox (`PAYMENTS_SANDBOX=true`) creates a local payment whose id starts with `sandbox-`. It is allowed only when `APP_ENV` is `development`, `test` or `staging`. With `APP_ENV=production` the process refuses to start, so a public shop cannot grant a subscription without a charge.

If Remnawave is not configured, sandbox writes a local link `sandbox://local/...`. That marks a test subscription. It is not a working VPN profile.

## Remnawave

Production fulfillment calls Remnawave with `REMNAWAVE_URL` and `REMNAWAVE_TOKEN`. The shop creates or extends the remote user and stores the expiry, traffic limit and subscription link. Repeating the same operation does not add the term twice: the expected expiry is compared before the extend call.

Without both variables, production fulfillment does not run. Use the test stack to exercise checkout and the cabinet.

## What this project does not do

- It does not host VPN nodes. Nodes belong to Remnawave.
- It does not take money until gateway keys are set and the production gate is open. The exception is an explicit sandbox outside production.
- It does not replace the Remnawave license or the payment provider agreements.
