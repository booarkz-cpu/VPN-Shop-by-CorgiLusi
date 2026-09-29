# v20.0.22 — исправление установки Support Redis

- Исправлен сбой `SUPPORT_REDIS_PASSWORD: unbound variable` после копирования release на новый VDS. Установщик генерирует пароль до записи `.env` и применяет одно значение в обоих файлах.
- Регрессионный тест исполняет запись конфигурации с `set -u` без заранее заданного пароля Redis.
- [Инструкция VDS и восстановление после частичной установки v20.0.21](https://github.com/booarkz-cpu/shop-by-boo/blob/v20.0.22/docs/ru/VDS_PRODUCTION_20_0_22.md) · [README](https://github.com/booarkz-cpu/shop-by-boo/blob/v20.0.22/README.md) · [Changelog](https://github.com/booarkz-cpu/shop-by-boo/blob/v20.0.22/CHANGELOG.md).

Это выпуск исходников. Реальный VDS этим CI не тестируется. Живые платежи остаются закрытыми до полного staging E2E v2.
