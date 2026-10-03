# v21.2.0 stable — импорт клиентов и массовые операции

Добавлены безопасный users.db mapping/preview, шифрованная staging-запись, постоянные связи источника и однократное зачисление начальных остатков новым клиентам через финансовый журнал. Совпавшие аккаунты сохраняют данные и текущий баланс.

Массовые операции поддерживают preview и атомарное применение: отзыв входных сессий, отключение автопродления и приватные уведомления. Новый раздел админки доступен роли admin. Исправлен порядок блокировок управления методом автопродления.

Head магазина **0058_customer_operations**, Support Pro **0005**. Перед обновлением сохраните согласованный backup и проверьте изолированный стенд. Downgrade с импортными связями/batch-журналом блокируется.

Обновлены README, production-регламент, API, инструкции, CHANGELOG и состав лицензии. ZIP, SHA256 и manifest публикуются из точного main commit после успешного полного CI. Подписанные APK/IPA требуют собственных Android/Apple ключей; фактический статус приложен отдельно.

**Вся матрица ещё не завершена.** Импорт профилей/начальных остатков не является автоматическим переносом исторических VPN-подписок и платежей любой сторонней схемы. Production gate закрыт; `production_ready=false`, `full_function_transfer=false`, `production_e2e_verified=false`, `signed=false`.

[Импорт](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.2.0/docs/ru/CUSTOMER_OPERATIONS_CURRENT.md) · [Production](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.2.0/docs/ru/PRODUCTION_CURRENT.md) · [матрица](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.2.0/docs/ru/WORKSPACE_COVERAGE.md).
