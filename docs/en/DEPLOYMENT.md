# Deploying the shop

Use this file for a server that will take real orders. To try the shop without gateways, Telegram or Remnawave, follow [TESTING.md](TESTING.md) instead.

## What you need

- Ubuntu or Debian, with root SSH.
- A domain and four names that point at the server: API, admin, Mini App, cabinet. A fifth name is required for Support Pro, because `docker-compose.yml` will not start without `SUPPORT_PRO_DOMAIN`.
- A running Remnawave panel: base URL and API token.
- A bot token from @BotFather.
- An administrator email and a long password.
- The installer opens SSH, TCP 80, TCP 443 and UDP 443. PostgreSQL, Redis and the API are not published. A hoster panel firewall must allow the same ports.

Keep `.env` passwords to letters and digits. The characters `@ : / #` break `DATABASE_URL`.

## 1. Install Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git openssl
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
docker compose version
```

## 2. Get the source

```bash
sudo git clone https://github.com/booarkz-cpu/VPN-Shop-by-CorgiLusi.git /opt/vpn-shop
cd /opt/vpn-shop
```

`sudo bash install.sh` from the repository does the same preparation and then runs `deploy/install-vps.sh`, which asks the questions on the SSH terminal. A `curl | bash` install reads answers from `/dev/tty`.

## 3. Fill in the environment

```bash
cp .env.example .env
openssl rand -hex 32
```

Set:

| Variable | Value |
| --- | --- |
| `APP_SECRET` | output of `openssl rand -hex 32`, at least 32 characters |
| `APP_ENV` | `production` |
| `DB_PASSWORD` and `POSTGRES_PASSWORD` | the same password |
| `DATABASE_URL` | that password inside `postgresql+asyncpg://vpnshop:PASSWORD@db:5432/vpnshop` |
| `BOT_TOKEN` | the BotFather token |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | the first panel login |
| `ADMIN_TELEGRAM_ID` | your numeric id if you want `/ops` |
| `REMNAWAVE_URL`, `REMNAWAVE_TOKEN` | the panel |
| `PUBLIC_BASE_URL` | `https://` API origin |
| `MINI_APP_URL` | `https://` Mini App origin |
| `CABINET_URL` | `https://` cabinet origin |
| `API_DOMAIN`, `ADMIN_DOMAIN`, `APP_DOMAIN`, `CABINET_DOMAIN` | hostnames without a scheme |
| `SUPPORT_PRO_DOMAIN` | ticket desk hostname |
| `SUPPORT_PRO_DB_PASSWORD` | a separate database password |
| `SUPPORT_PRO_SSO_SECRET` | `openssl rand -hex 32` |
| `COOKIE_SECURE` | `true` |
| `PAYMENTS_SANDBOX` | `false` |

`PAYMENTS_SANDBOX=true` with `APP_ENV=production` stops the process with `PAYMENTS_SANDBOX is allowed only when APP_ENV is development, test, or staging`.

Gateway keys can stay empty here. Live charges stay closed until the steps in [PAYMENTS.md](PAYMENTS.md).

## 4. Start the containers

```bash
cd /opt/vpn-shop
docker compose up -d --build
docker compose ps
```

PostgreSQL and Redis become healthy, the backend applies Alembic migrations, the worker starts after the API, the panels wait for a healthy API, and Caddy publishes ports 80 and 443.

Check:

```bash
curl -fsS https://API_DOMAIN/health
```

The body contains `"ok": true`.

The first start creates the administrator. A later start does not overwrite that password from `.env`.

## 5. Open the panel

Open `https://ADMIN_DOMAIN`. Sign in with the email and password from `.env`. Change the password if it was copied anywhere, and turn on TOTP in the security section.

Create a plan: name, price above zero, duration in days, traffic in gigabytes, device limit. A disabled plan is hidden from the storefront.

## 6. Connect the bot

In @BotFather set the Mini App URL to `MINI_APP_URL`. Send `/start`. The shop button must open the Mini App over HTTPS.

An empty `BOT_TOKEN` in production stops the bot container. A production shop must not sit in a silent idle loop.

## 7. Check fulfillment

You need gateway keys and an open production gate, or a separate staging host that uses sandbox. Sandbox is refused on production.

After payment, the webhook or the worker runs fulfillment. The user card shows an expiry and a subscription link. If Remnawave is down, the payment stays paid and fulfillment is marked failed, then retried. The error text stays in the process log.

## 8. Backups

Backups live in `/data/backups` inside the backend and worker. `scripts/backup.sh` writes a dump. `scripts/update.sh` takes a snapshot and `pg_dump` before it copies files. A failed build restores that snapshot.

`APP_SECRET` decrypts secrets already stored. Before rotation, copy the old value to `APP_SECRET_PREVIOUS`, set a new `APP_SECRET`, restart the backend and worker, then clear the previous key.

## 9. Updates

```bash
cd /opt/vpn-shop
sudo bash scripts/update-from-github.sh
```

The script leaves `.env` in place.

## If a container does not start

```bash
docker compose logs --tail 100 backend
docker compose logs --tail 100 worker
docker compose logs --tail 50 caddy
```

Typical causes: the password inside `DATABASE_URL` does not match `DB_PASSWORD`, `APP_SECRET` is shorter than 32 characters, `SUPPORT_PRO_DB_PASSWORD` or a domain is missing, DNS does not point at the server yet, or ports 80 and 443 are taken.
