# v20.0.29 — исправление API-списков админ-центра

Дата: 2026-10-01

## Что исправлено

- Исправлен JavaScript-регресс в админ-центре: некоторые API-разделы могли вернуть объект вместо массива, после чего интерфейс падал с ошибкой map is not a function.
- Добавлена единая безопасная нормализация списков перед рендерингом таблиц и списков.
- Поддерживаются стандартные формы ответа: массив, items, results, data.
- Сохранён AdminErrorBoundary, поэтому непредвиденная ошибка интерфейса отображается диагностически, а не превращает панель в чёрный экран.
- Версии backend, installer, build tooling, release manifest и workflow синхронизированы на 20.0.29.

## Обновление существующего VDS

```bash
cd /opt/vpn-shop
sudo bash scripts/update-from-github.sh
sudo docker compose ps
```

После обновления сделайте жёсткое обновление страницы админ-центра: Ctrl+Shift+R.

## Проверка

```bash
cd /opt/vpn-shop
sudo docker compose config >/dev/null
sudo docker compose ps
sudo docker compose exec -T backend python - <<'PY'
from app.main import APP_VERSION
print(APP_VERSION)
PY
```

Ожидаемая версия: 20.0.29.

## Важно

- Перед обновлением сохраняйте резервную копию .env, .env.images, Support Pro environment, PostgreSQL и пользовательских загрузок.
- Не выполняйте docker compose down -v.
- Не заменяйте рабочий .env файлом .env.example.
- Реальные платежи по-прежнему требуют отдельного полного staging E2E v2.
