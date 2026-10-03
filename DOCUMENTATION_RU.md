# Полная документация на русском

Начните с [актуального указателя](DOCUMENTATION.md). Для v21.4.0 используйте руководства `WORKSPACE_*` и [отчёт выпуска](docs/ru/RELEASE_21_3_0_STABLE.md). Порядок установки: [INSTALL_STEPS.md](INSTALL_STEPS.md). Каждая область описана в [FUNCTIONS.md](FUNCTIONS.md).

Магазин использует единые финансовые операции для кабинета, Mini App и бота. Отдельные мобильные приложения клиента и администратора остаются в исходниках. Старые платёжные адаптеры нужны для исторической сверки и не расширяют список новых покупок. Новые агенты: YooKassa, RollyPay, Platega. Производственный допуск закрыт до полного внешнего application E2E v2.

[Архитектура](docs/ru/WORKSPACE_ARCHITECTURE.md), [состав компонентов](MODULES.md), [проверка полноты](docs/ru/WORKSPACE_COVERAGE.md), [лицензия](LICENSE).

Изменения alpha.7: [ключи доступа администратора](docs/ru/ADMIN_PASSKEYS.md), [метрики, dashboard и alerts](docs/ru/OPERATIONS_MONITORING.md). Мобильный workflow использует версию текущего манифеста; без owner signing secrets APK/IPA не объявляются подписанными production assets.

## Новые функции v21.4.0

Добавлены [партнёрский кабинет и комиссии](docs/ru/PARTNERS_CURRENT.md), [клиентские ключи доступа](docs/ru/CUSTOMER_PASSKEYS_CURRENT.md) и [объединение/разделение обращений](docs/ru/SUPPORT_TOPOLOGY_CURRENT.md). [Полная инструкция production](docs/ru/PRODUCTION_CURRENT.md) охватывает SSH/Termius, DNS/TLS, настройку, приёмку, backup/restore, обновления и инциденты. Вся матрица ещё не завершена; production gate закрыт.
