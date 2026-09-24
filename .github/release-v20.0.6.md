# v20.0.6 — staging E2E

## Русский

Журнал staging больше не считает подсказку полным проходом. Отдельная строка `FULL_E2E_PASS` появляется только после sandbox-оплаты, повторного чтения счёта, возврата и проверки токена staging Remnawave. Пока проверка выполняется, панель показывает строку `[CHECKOUT]`.

Счёт staging не попадает в таблицу платежей, поэтому боевой воркер не выдаёт VPN. Вебхук магазина по-прежнему сверяет боевые ключи. Оплату и возврат читает сам runner через localhost.

Как пройти проверку, записано в `README.md`, раздел «Как пройти staging E2E».

## English

The staging log no longer treats a help sentence as a full pass. A line that is exactly `FULL_E2E_PASS` appears only after the sandbox payment, a second read of the invoice, a refund, and a check of the staging Remnawave token. While the check is running, the panel shows the `[CHECKOUT]` line.

A staging invoice is not stored in the payment table, so the production worker does not grant VPN. The shop webhook still checks the live keys. The runner itself reads the payment and the refund through localhost.

The operator sequence is in `README.md`, under “How to pass staging E2E”.

## Українська

Журнал staging більше не вважає підказку повним проходженням. Окремий рядок `FULL_E2E_PASS` з'являється лише після sandbox-оплати, повторного читання рахунку, повернення і перевірки токена staging Remnawave. Поки перевірка виконується, панель показує рядок `[CHECKOUT]`.

Рахунок staging не потрапляє в таблицю платежів, тому бойовий воркер не видає VPN. Вебхук магазину й далі звіряє бойові ключі. Оплату і повернення читає сам runner через localhost.

Як пройти перевірку, записано в `README.md`, розділ «Як пройти staging E2E».
