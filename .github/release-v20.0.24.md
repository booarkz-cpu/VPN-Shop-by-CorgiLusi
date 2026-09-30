# v20.0.24 — исправления ротации и pinning

- Первая ротация `APP_SECRET` добавляет отсутствующий `APP_SECRET_PREVIOUS`, чтобы ранее выданные токены и зашифрованные значения могли использовать прежний ключ. Повторная ротация не создаёт дублей.
- Закрепление Docker образов прекращается до изменения окружения, если Docker не вернул immutable digest.
- PyJWT обновлён до 2.14.0 после обнаружения уязвимостей в аудите зависимостей CI.
- Добавлены регрессионные проверки и [инструкция обслуживания](https://github.com/booarkz-cpu/shop-by-boo/blob/v20.0.24/docs/ru/steps/05-operations.md). [Инструкция VDS](https://github.com/booarkz-cpu/shop-by-boo/blob/v20.0.24/docs/ru/VDS_PRODUCTION_20_0_24.md) · [README](https://github.com/booarkz-cpu/shop-by-boo/blob/v20.0.24/README.md) · [Changelog](https://github.com/booarkz-cpu/shop-by-boo/blob/v20.0.24/CHANGELOG.md).

Production платежи остаются закрытыми до полного staging E2E v2. Реальный VDS этим CI не тестируется.
