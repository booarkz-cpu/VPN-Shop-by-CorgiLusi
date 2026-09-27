## Исправления сводного аудита безопасности

- Удалён общий ключ native-клиентов; одноразовый обмен кода с PKCE S256, разделённый CORS и запрет browser bearer exchange.
- Redis AUTH в backend/worker/Support и Compose; ограниченный локальный rate-limit fallback при сбое Redis.
- Только явно доверенный ingress IP; Uvicorn больше не доверяет произвольным proxy headers.
- Fail-closed RollyPay, единый официальный протокол Platega, event dedupe Stripe/PayPal, startup validation провайдеров.
- Полный читаемый `main.py` вместо runtime exec частей.
- Support SSO через POST с сохранением роли; удалён HTML sink CMS; Support webhooks защищены от DNS rebinding.
- Frontend и Caddy работают без root; отдельная одноразовая миграция прав volumes.
- Restore требует двух отдельных MFA-администраторов, одноразового разрешения, проверки SHA-256 и сохраняемого вне БД аудита.

**Обновление несовместимо со старым native login:** пересоберите Android/iOS 2.14.0. Потребуются Redis passwords и согласованное обновление служб. ZIP содержит исходники, не подписанные APK/IPA.

[Отчёт по всем 19 пунктам](https://github.com/booarkz-cpu/VPN-Shop-by-CorgiLusi/blob/v20.0.14/docs/ru/SECURITY_AUDIT_20_0_14.md) · [Инструкция обновления](https://github.com/booarkz-cpu/VPN-Shop-by-CorgiLusi/blob/v20.0.14/docs/ru/SECURITY_UPGRADE_20_0_14.md)

CI проверяет backend/Support, миграции и конкурентные сценарии PostgreSQL, web builds, зависимости, запуск контейнеров с Redis AUTH, Android debug/iOS simulator builds. Рабочий VDS и реальные provider callbacks не проверялись. Production payment gate остаётся закрытым до полного staging E2E v2.
