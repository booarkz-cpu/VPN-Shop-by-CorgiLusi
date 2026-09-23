# VPN Shop by Corgi Lusi — Remnawave Shop Integration

Corgi работает как коммерческий слой поверх Remnawave:

`Corgi Store -> Payment -> Entitlement -> Remnawave API -> Subscription URL -> Client`

## Как это работает

1. Пользователь выбирает тариф в Corgi.
2. Corgi принимает оплату и ждёт подтверждения платёжного провайдера.
3. Только после подтверждённого `paid/succeeded` запускается fulfillment.
4. Если у пользователя уже есть Remnawave user — Corgi продлевает его и обновляет entitlement.
5. Если пользователя нет — Corgi создаёт Remnawave user с серверным API token.
6. Corgi получает subscription URL и сохраняет его как entitlement.
7. Мобильное/веб-приложение получает URL только через Corgi API.

## Remnawave 3.x

Для Panel 3.x Corgi использует числовой Remnawave `userId`. Старые UUID user routes не используются.

## Настройка

В production backend:

```env
REMNAWAVE_URL=https://panel.example.com
REMNAWAVE_TOKEN=<server-side-api-token>
```

API token никогда не помещается в Android/iOS/Web client.

## Связь тарифов

Каждый активный Corgi Plan должен иметь `remnawave_profile_id` — идентификатор Internal Squad/профиля доступа Remnawave.

Проверить:

`POST /api/admin/remnawave/shop/plan-mapping/validate`

Проверить соединение:

`POST /api/admin/remnawave/shop/test`

Сводка:

`GET /api/admin/remnawave/shop`

## Пользователь

Текущая подписка:

`GET /api/me/remnawave/subscription`

Принудительно обновить expiry/subscription URL:

`POST /api/me/remnawave/subscription/refresh`

## Безопасность

- Remnawave API token остаётся только на backend.
- Corgi не возвращает удалённые VPN credentials в admin read-only responses.
- Fulfillment идемпотентен.
- Refund не может повторно перевести платёж в `paid`.
- Временная недоступность Remnawave не должна приводить к повторному списанию.
- Subscription URL выдаётся только аутентифицированному владельцу.

Remnawave официально предоставляет REST API, управление пользователями, нодами и subscription URLs; для Panel 3.x user-scoped API используют числовой `userId`. См. официальную документацию Remnawave.
