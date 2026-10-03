Предварительный выпуск **v21.0.0-alpha.7**, не финальный stable.

- Реальный административный WebAuthn/passkey: browser registration/login, cryptographic verifier, обязательные UV/UP, RP/origin/userHandle, single-use cookie-bound challenges, counter locks и MFA-сессии.
- Операционные gauges БД, 14 панелей Grafana, Prometheus scrape example и пять alert rules без персональных labels.
- Mobile release assets привязаны к версии манифеста и exact source commit; workflow ждёт CI/релиз и проверяет digest/size.
- Обновлены README, changelog, канонические инструкции, license 2.3 и third-party notices с сохранением существующих grants/restrictions.

Миграция магазина: **0053_admin_passkeys**; Support Pro **0005**, версия 3.5. Сделайте проверенный backup. Downgrade 0053 запрещён при зарегистрированных passkeys. Инструкции: `docs/ru/ADMIN_PASSKEYS.md`, `OPERATIONS_MONITORING.md`, `WORKSPACE_UPGRADE.md`, `RELEASE_21_0_0_ALPHA_7.md`.

Публикация следует за обязательным успешным CI, включая реальную EC-криптографию, PostgreSQL races и Chromium virtual-authenticator E2E. Это не внешний production E2E: полный перенос функций, provider sandbox/Remnawave/SMTP, физические native-устройства и owner APK/IPA signing ещё не подтверждены. Манифест честно сохраняет `full_function_transfer=false`, `production_e2e_verified=false`, `signed=false`.
