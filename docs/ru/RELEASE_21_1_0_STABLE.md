# v21.1.0 stable: завершённый этап матрицы

Добавлены клиентские browser passkeys, журналируемые merge/split обращений и партнёрский кабинет с фактическими комиссиями/резервируемыми выплатами. Реализовано отдельное руководство production по исходникам текущего тега. **Это не завершение всей матрицы.** Статусы незавершённых областей сохранены явно.

## Изменения

- `0055_customer_passkeys`: отдельные credentials/challenges клиента, opaque handles, real signature/UV/origin/counter verification, password/fresh OAuth подтверждение регистрации/удаления, штатные сессии, кабинет.
- `0056_support_topology`: preview fingerprint, atomic merge/split внутри одного клиента, сохранение первого сообщения/legacy replies, ID вложений, namespace retry keys, audit и запрет сообщений в объединённый источник.
- `0057_partner_commissions`: владелец кабинета, снимки ставки checkout/wallet, однократное начисление после выдачи, clawback при refund, валютный баланс, reserve/approve/paid/reject workflow и приватный кабинет.
- Исправлен порядок row/advisory locks при привязке реферала из Telegram, чтобы не инвертировать блокировки checkout. Чтение предков обновляет cached ORM rows.
- Установка Docker через signed apt вместо convenience script; новые установки записывают оба WebAuthn origin. Версия installer/source ZIP закреплена за тегом.
- Обновлены README, текущие инструкции, OpenAPI-каталог, changelog и лицензия 2.4 с прежними разрешениями/ограничениями.

## Проверки

Backend/SQLite, PostgreSQL races/DDL в CI, admin/cabinet/Mini App typecheck/build, Chromium с virtual authenticator для двух поверхностей, Support Pro, контейнеры/Compose, native builds и аудит зависимостей. Фактический итог точного релизного commit следует смотреть в GitHub Actions; успешный локальный тест не заменяет CI. Манифест архива содержит commit и CI run.

Head магазина `0057_partner_commissions`, Support Pro `0005`. Новые миграции не начисляют старые партнёрские платежи. Downgrade блокируется при соответствующих ключах, topology journal или финансовой истории. Перед обновлением обязательна согласованная копия двух баз/файлов и отдельный restore drill.

## Незавершённое

Остаются account merge, расширенные маркетинговые редакторы, plugin runtime, безопасный импорт, внешние каналы/remote mapping поддержки, nDPI/операторская инфраструктура, входящая почта, native push/widgets/passkeys и application payment E2E v2. Полный список и конкретные границы — [матрица](WORKSPACE_COVERAGE.md).

`production_ready=false`, `full_function_transfer=false`, `production_e2e_verified=false`, `signed=false`. Production gate остаётся закрыт. Android/Apple signing keys отсутствуют; mobile status показывает реальное состояние. VDS/SMTP/VPN/payment/restore проверки владельца не объявляются выполненными.

[Production](PRODUCTION_CURRENT.md) · [партнёры](PARTNERS_CURRENT.md) · [клиентские ключи](CUSTOMER_PASSKEYS_CURRENT.md) · [обращения](SUPPORT_TOPOLOGY_CURRENT.md).
