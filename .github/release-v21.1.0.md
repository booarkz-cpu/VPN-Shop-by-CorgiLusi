# v21.1.0 stable — клиентские ключи, обращения и партнёры

Добавлены клиентские WebAuthn passkeys с проверкой подписи/UV/origin/replay и интерфейсом кабинета; preview и атомарные merge/split обращений с сохранением приватных вложений; партнёрский кабинет с неизменяемой ставкой заказа, фактическими комиссиями, отменой при refund и резервируемыми выплатами.

Исправлена инверсия row/advisory locks в Telegram-привязке рефералов. Docker устанавливается из официального signed apt-репозитория. Полное руководство установки/эксплуатации production, актуальные точки входа, API-каталог, README/CHANGELOG и лицензия 2.4 включены в исходники.

Head магазина **0057_partner_commissions**, Support Pro **0005**. Сначала сохраните согласованный backup и проверьте изолированный стенд. Старые партнёрские платежи не начисляются задним числом. Downgrade с новой credential/topology/финансовой историей блокируется.

ZIP, SHA256 и манифест публикуются из точного main commit после полного успешного CI. Ссылку на commit/CI содержит манифест. Подписанные APK/IPA требуют собственных Android/Apple ключей; фактический статус приложен отдельно.

**Вся матрица ещё не завершена:** account merge, E2E v2 и другие перечисленные функции остаются открытыми. Production gate закрыт; `production_ready=false`, `full_function_transfer=false`, `production_e2e_verified=false`, `signed=false`. Stable — канал проверенного текущего ядра, а не подтверждение полного функционального переноса или реального коммерческого запуска.

[Production](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.1.0/docs/ru/PRODUCTION_CURRENT.md) · [README](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.1.0/README.md) · [матрица](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.1.0/docs/ru/WORKSPACE_COVERAGE.md).
