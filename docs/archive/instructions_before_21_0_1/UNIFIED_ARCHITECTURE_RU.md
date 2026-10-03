# VPN Shop by Corgi — Unified Architecture

## Единый продукт

VPN Shop by Corgi и Support Pro 3.4 теперь распространяются как **один репозиторий и один release bundle**.

Support Pro находится в `support-pro/` и является единственным каноническим движком поддержки.

## Удалённые дубли

- Отдельный `support_pro_3_4.zip` больше не нужен: его содержимое уже находится в `support-pro/`.
- Отдельный installer Support Pro из второго архива не включается в основной release bundle.
- В админском UI удалён старый раздел `Поддержка`; вместо него используется `Support Pro`.
- Старый `SupportTicket` backend API оставлен только для обратной совместимости со старыми клиентами и явно помечен `LEGACY COMPATIBILITY`.
- Новые UI и операционные сценарии поддержки должны использовать Support Pro.

## Источники истины

| Функция | Канонический модуль |
|---|---|
| VPN users / subscriptions / payments | `backend/` |
| VPN nodes / routing / provisioning | `backend/` |
| Support / tickets / SLA / operators | `support-pro/` |
| Support knowledge base | `support-pro/` |
| Support automation / webhooks | `support-pro/` |
| Admin navigation | `admin/` |
| User cabinet | `cabinet/` |

## Deployment

Используйте корневой `docker-compose.yml`. Support Pro запускается как часть общего stack через:

- `support_db`
- `support_redis`
- `support_migrate`
- `support_pro`
- `support_worker`

SSO между основной админкой и Support Pro остаётся включённым.

## Следующий этап

После перехода всех старых клиентов на Support Pro legacy `SupportTicket` endpoints/model можно удалить отдельной миграцией данных.
