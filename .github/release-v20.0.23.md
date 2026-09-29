# v20.0.23 — продолжение установки VDS

- Исправлен отказ на `./scripts/pin-images.sh: Permission denied` при установке v20.0.22; этот и другие shell-скрипты запускаются через Bash, права запуска двух необходимых файлов исправлены.
- Добавлен безопасный [скрипт продолжения уже начатой установки](https://github.com/booarkz-cpu/shop-by-boo/blob/v20.0.23/deploy/resume-vps-after-pin.sh): он сохраняет оба `.env` и завершает сборку без повторного опроса.
- [Инструкция VDS и восстановление](https://github.com/booarkz-cpu/shop-by-boo/blob/v20.0.23/docs/ru/VDS_PRODUCTION_20_0_23.md) · [README](https://github.com/booarkz-cpu/shop-by-boo/blob/v20.0.23/README.md) · [Changelog](https://github.com/booarkz-cpu/shop-by-boo/blob/v20.0.23/CHANGELOG.md).

Это выпуск исходников. Реальный VDS этим CI не тестируется; живые платежи остаются закрытыми до полного staging E2E v2.
