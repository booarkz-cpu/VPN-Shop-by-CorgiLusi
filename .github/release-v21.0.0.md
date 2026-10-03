# v21.0.0 stable — проверенное ядро

Стабильный выпуск текущего реализованного ядра после alpha.7: кабинет, админка, бот/Mini App, торговые операции, независимые подписки, поддержка, конкурсы и колесо, административные WebAuthn passkeys и операционный мониторинг.

Версия API, установщика, архивов и текущих инструкций согласована. Миграция магазина `0053_admin_passkeys`, Support Pro `0005`; после alpha.7 новых миграций нет. Лицензия 2.3 сохраняет действующие разрешения.

**Ограничения:** это stable-канал проверенного ядра, а не подтверждение полного переноса функций или production-ready магазина. Application E2E v2 не завершён, production-платежи остаются закрытыми. `production_ready=false`, `full_function_transfer=false`, `production_e2e_verified=false`, `signed=false`. Подписанные APK/IPA требуют ключей Android/Apple владельца; статус мобильной публикации приложен отдельно.

Исходный ZIP, SHA256 и манифест опубликованы только после полного успешного CI точного commit main. CI включает PostgreSQL backend, Support Pro, аудит зависимостей, web-сборки, Chromium WebAuthn, Compose/контейнеры и компиляцию Android/iOS. Точный commit и CI run находятся в манифесте.

Перед обновлением сохраните backup базы, uploads и настроек и проверьте отдельный стенд. Подробности: [README](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.0.0/README.md), [отчёт](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.0.0/docs/ru/RELEASE_21_0_0_STABLE.md), [матрица оставшихся работ](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.0.0/docs/ru/WORKSPACE_COVERAGE.md).
