# Support Pro — интеграция в VPN Shop by Corgi

Support Pro 3.4 встроен в production stack как изолированный сервис. Его PostgreSQL/Redis/загрузки имеют отдельные volumes, поэтому схема поддержки не смешивается с основной БД VPN Shop.

## Что добавлено

- `support-pro/` — исходники Support Pro 3.4.
- `support_db`, `support_redis`, `support_migrate`, `support_pro`, `support_worker` в основном `docker-compose.yml`.
- `SUPPORT_PRO_DOMAIN` — отдельный same-site HTTPS hostname.
- `SUPPORT_PRO_URL` — URL сервиса для admin API.
- `SUPPORT_PRO_SSO_SECRET` — общий секрет для короткоживущего одноразового SSO.
- Admin → Клиенты → **Support Pro**.
- SSO из основной админки без передачи пароля Support Pro в браузер.
- Health/status карточка и встроенный iframe.
- Все функции Support Pro 3.4 остаются доступными: тикеты, SLA, Telegram, realtime, база знаний, macros, automation, webhooks, incidents, reports, operators, portal и attachments.

## Production variables

```env
SUPPORT_PRO_DOMAIN=support.example.com
SUPPORT_PRO_URL=https://support.example.com
SUPPORT_PRO_SSO_SECRET=<openssl rand -hex 32>
SUPPORT_PRO_DB_PASSWORD=<strong-random-password>
SUPPORT_PRO_PUBLIC_ORIGIN=https://support.example.com
SUPPORT_PRO_BOT_TOKEN=<отдельный Telegram Bot Token>
```

## Security

- SSO token: HMAC-SHA256.
- TTL: 60 секунд.
- `jti`: одноразовый через Redis.
- SSO secret никогда не отдаётся frontend.
- Support Pro остаётся отдельным trust boundary и отдельной БД.
- Порт Support Pro наружу напрямую не публикуется — только через Caddy.
