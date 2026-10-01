# Обновление VPN Shop до актуальной версии v20.0.29

Инструкция для уже установленного VDS. Повторная установка сервера не требуется.

## 1. Перед обновлением

Сделайте backup `.env`, `.env.images`, `support-pro/.env` (если используется), PostgreSQL и пользовательских загрузок. Проверьте место на диске:

```bash
cd /opt/vpn-shop
df -h /
sudo docker compose ps
```

Не используйте `docker compose down -v`: это может удалить volumes.

## 2. Обновление

```bash
cd /opt/vpn-shop
sudo bash scripts/update-from-github.sh
```

Скрипт сохраняет локальные environment-файлы, проверяет релиз и выполняет health-check. Не заменяйте `.env` файлом `.env.example`.

## 3. Проверка версии

```bash
cd /opt/vpn-shop
sudo docker compose exec -T backend python - <<'PY'
from app.main import APP_VERSION
print(APP_VERSION)
PY
sudo docker compose ps
```

Ожидается `20.0.29`, а контейнеры должны быть `Up`/`healthy` там, где healthcheck предусмотрен.

## 4. Проверка админ-центра

1. Откройте админ-центр.
2. Выполните `Ctrl+Shift+R`.
3. Откройте разделы, которые ранее показывали `s.map is not a function` или `map is not a function`.
4. Если API вернул объект вместо массива, новый frontend нормализует `items`, `results` или `data`.
5. При непредвиденной ошибке Error Boundary показывает диагностическое сообщение вместо чёрного экрана.

## 5. Диагностика

```bash
cd /opt/vpn-shop
sudo docker compose config >/dev/null
sudo docker compose logs --tail=100 backend
sudo docker compose logs --tail=100 admin
```

Для нестабильного SSH используйте tmux.

## 6. Откат

Если после обновления сервис не проходит health-check, остановитесь и используйте штатный rollback из deployment-инструментов. Сначала сохраните логи и состояние контейнеров. Не удаляйте volumes вручную.

## 7. После обновления

Проверьте админку, Support Pro, личный кабинет, Mini App, worker, платежные webhooks и мониторинг. Реальные платежи не считаются разрешёнными только потому, что обновление прошло успешно: для них требуется полный staging E2E v2.
