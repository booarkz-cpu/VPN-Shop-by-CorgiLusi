# v21.0.1 stable — рефералы, резервирование и документация

Реализованы до пяти реферальных уровней со снимками условий заказа, безопасными повторами, отменой всех уровней при возврате и обезличенным графом сети. В админке добавлена настройка процентов; исправлен учёт отменённых наград.

CLI backup теперь создаёт согласованную зашифрованную копию двух баз, media/mobile files, uploads и окружения. Проверяет AES-GCM-поток, возобновляет writers после snapshot и при ошибке, удаляет неполные результаты. Формат `.vpb` отличается от архивов административного backup.

Обновлены текущие инструкции, SSH/Termius, точки входа, API-каталог из OpenAPI, README/CHANGELOG и область лицензии 2.3. Исправлены loopback-порты: кабинет 18082, Mini App 18083. Wrapper установки закреплён за stable-тегом.

Миграция магазина **0054_referral_levels**, Support Pro **0005**. Сначала сохраните согласованный backup и проверьте отдельный стенд. Старая одноуровневая история сохраняется; downgrade с новыми финансовыми строками запрещён.

Исходный ZIP, SHA256 и манифест публикуются только после полного успешного CI точного main commit. Точный commit и CI run записаны в манифесте.

**Ограничения:** полный набор матрицы ещё не завершён, application E2E v2 не реализован полностью, production-платежи закрыты. `production_ready=false`, `full_function_transfer=false`, `production_e2e_verified=false`, `signed=false`. Подписанные APK/IPA требуют ключей владельца; статус подписи приложен отдельно. Внешний VDS restore drill и VPN-проверка не заменяются CI.

[README](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.0.1/README.md) · [рефералы](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.0.1/docs/ru/REFERRALS_CURRENT.md) · [backup](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.0.1/docs/ru/BACKUP_CURRENT.md) · [отчёт](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.0.1/docs/ru/RELEASE_21_0_1_STABLE.md) · [оставшиеся работы](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.0.1/docs/ru/WORKSPACE_COVERAGE.md).
