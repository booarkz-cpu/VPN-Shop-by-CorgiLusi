# Changelog

## 20.0.15 / Mobile 2.15.0 — 2026-09-27

Защищено хранение native-токенов и блокировка приложений; исправлены recovery login, ранний PKCE-отказ и конкурентная регистрация; усилены production secrets, Support sessions, инфраструктурный RBAC и валидация конфигурации. Backup/restore используют приватные временные каталоги. Публикация native production требует успешного CI и постоянной подписи владельца, без подмены debug/unsigned сборками. [Аудит](docs/ru/AUDIT_20_0_15.md) · [Обновление и подпись](docs/ru/PRODUCTION_20_0_15.md).

## Mobile 2.14.1 — 2026-09-27

Согласованы версии четырёх native-клиентов, build 2141 и User-Agent; сохранён PKCE-вход для backend 20.0.14. Добавлены сборка и публикация Android APK, iOS unsigned IPA и simulator ZIP, SHA-256 и метаданные происхождения. Для iOS добавлено описание использования Face ID, необходимое для разблокировки сохранённой сессии. Release APK больше не подписывается debug-ключом автоматически: без постоянного ключа создаётся отдельный preview package. [Установка](docs/ru/MOBILE_RELEASE_2_14_1.md).

## 20.0.14 — 2026-09-26

Исправлен сводный аудит из 19 пунктов: native PKCE вместо общего ключа, разделение CORS, Redis AUTH и локальный аварийный rate limit, явный trusted ingress, fail-closed настройки webhook, Stripe/PayPal dedupe, обычный исходный main.py, POST SSO без повышения ролей, непривилегированные web/ingress процессы, текстовый CMS, DNS-pinned Support webhooks и restore с двумя MFA-администраторами.

Добавлены миграция environment, регрессионные/конкурентные тесты, CI сборок native и запуска контейнеров. Native source version — 2.14.0. Старый mobile login и restore API несовместимы: [инструкция обновления](docs/ru/SECURITY_UPGRADE_20_0_14.md). [Подробный отчёт](docs/ru/SECURITY_AUDIT_20_0_14.md).

Production payment gate версии 20.0.13 сохраняется; полный E2E v2 не реализован этим релизом.

## 20.0.13

Привязка staging gate к конфигурации и свежему доказательству, защита от подмены результата и конкурентного запуска; инструкция будущего staging E2E v2. [Release notes](.github/release-v20.0.13.md).

Предыдущая история: [GitHub Releases](https://github.com/booarkz-cpu/VPN-Shop-by-CorgiLusi/releases).
