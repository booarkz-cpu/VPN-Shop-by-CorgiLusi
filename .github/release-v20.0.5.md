# v20.0.5

## Русский

Версия приложения в коде — **20.0.5**.

- Сверка платежа со статусом `creation_unknown` больше не вызывает создание нового счёта ЮKassa.
- Планировщик и `POST /api/admin/payments/reconcile` находят уже созданный счёт через `find_by_order_id`.
- `Idempotence-Key` нового счёта ЮKassa равен номеру заказа магазина.

## English

The application version in code is **20.0.5**.

- Reconciliation of a `creation_unknown` payment no longer creates a new YooKassa invoice.
- The scheduler and `POST /api/admin/payments/reconcile` find the existing invoice with `find_by_order_id`.
- The `Idempotence-Key` of a new YooKassa invoice is the shop order id.

## Українська

Версія застосунку в коді — **20.0.5**.

- Звірка платежу зі статусом `creation_unknown` більше не створює новий рахунок ЮKassa.
- Планувальник і `POST /api/admin/payments/reconcile` знаходять уже створений рахунок через `find_by_order_id`.
- `Idempotence-Key` нового рахунку ЮKassa дорівнює номеру замовлення магазину.
