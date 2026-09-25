# Развёртывание магазина

Перед боевыми платежами см. [контракт и порядок реализации staging E2E v2](STAGING_E2E_V2_IMPLEMENTATION.md). В v20.0.13 приложение может работать в production с закрытым платёжным gate; текущий runner v1 не выдаёт полный результат.

Для релиза v20.0.12 используйте подробную процедуру [установки и запуска на VDS](VDS_PRODUCTION_V20_0_12.md). Этот исторический документ содержит упрощённые шаги. **В v20.0.12 текущий staging runner не может открыть допуск реальных платежей**: он не проверяет полный цикл webhook и выдачи. Запуск в production допускается только с закрытым платёжным шлюзом.

Инструкция для сервера, на котором магазин принимает настоящие заказы. Для проверки без касс, без Telegram и без Remnawave используйте [TESTING.md](TESTING.md), а не этот файл.

## Что понадобится

- Ubuntu или Debian, доступ root по SSH.
- Домен и четыре имени, которые указывают на IP сервера: API, админка, Mini App, кабинет. Пятое имя нужно службе заявок Support Pro, потому что `docker-compose.yml` не стартует без `SUPPORT_PRO_DOMAIN`.
- Уже работающая панель Remnawave: базовый URL и API-токен.
- Токен бота от @BotFather.
- Почтовый ящик администратора и пароль длиннее случайного слова.
- Установщик сам открывает SSH, TCP 80, TCP 443 и UDP 443. PostgreSQL, Redis и API наружу не публикуются. Внешний файрвол панели хостера должен пропускать те же порты.

Пароли в `.env` держите из букв и цифр. Символы `@ : / #` ломают `DATABASE_URL`.

## 1. Поставить Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git openssl
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
docker compose version
```

## 2. Получить исходники

```bash
sudo git clone https://github.com/booarkz-cpu/VPN-Shop-by-CorgiLusi.git /opt/vpn-shop
cd /opt/vpn-shop
```

Тот же результат даёт `sudo bash install.sh` из каталога репозитория: скрипт ставит Docker и вызывает `deploy/install-vps.sh`, который задаёт вопросы в терминале SSH. Если скрипт запущен через `curl | bash`, ответы читаются с `/dev/tty`.

## 3. Заполнить окружение

```bash
cp .env.example .env
openssl rand -hex 32
```

Впишите в `.env`:

| Переменная | Значение |
| --- | --- |
| `APP_SECRET` | строка из `openssl rand -hex 32`, не короче 32 символов |
| `APP_ENV` | `production` |
| `DB_PASSWORD` и `POSTGRES_PASSWORD` | один и тот же пароль |
| `DATABASE_URL` | тот же пароль в строке `postgresql+asyncpg://vpnshop:ПАРОЛЬ@db:5432/vpnshop` |
| `BOT_TOKEN` | токен BotFather |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | первый вход в панель |
| `ADMIN_TELEGRAM_ID` | ваш числовой id, если нужна команда `/ops` |
| `REMNAWAVE_URL`, `REMNAWAVE_TOKEN` | панель |
| `PUBLIC_BASE_URL` | `https://` адрес API |
| `MINI_APP_URL` | `https://` адрес Mini App |
| `CABINET_URL` | `https://` адрес кабинета |
| `API_DOMAIN`, `ADMIN_DOMAIN`, `APP_DOMAIN`, `CABINET_DOMAIN` | имена без схемы |
| `SUPPORT_PRO_DOMAIN` | имя службы заявок |
| `SUPPORT_PRO_DB_PASSWORD` | отдельный пароль базы заявок |
| `SUPPORT_PRO_SSO_SECRET` | `openssl rand -hex 32` |
| `COOKIE_SECURE` | `true` |
| `PAYMENTS_SANDBOX` | `false` |

`PAYMENTS_SANDBOX=true` вместе с `APP_ENV=production` останавливает процесс с текстом `PAYMENTS_SANDBOX is allowed only when APP_ENV is development, test, or staging`.

Ключи касс на этом шаге можно оставить пустыми. Живые платежи всё равно закрыты, пока не пройден шаг из [PAYMENTS.md](PAYMENTS.md).

## 4. Запустить контейнеры

```bash
cd /opt/vpn-shop
docker compose up -d --build
docker compose ps
```

Порядок такой: PostgreSQL и Redis становятся здоровыми, backend применяет миграции Alembic и только потом принимает запросы, воркер стартует после backend, панели ждут здоровый API, Caddy публикует 80 и 443.

Проверка:

```bash
curl -fsS https://API_DOMAIN/health
```

Ответ содержит `"ok": true`.

Первый запуск создаёт администратора. Повторный запуск пароль из `.env` не перезаписывает.

## 5. Войти в панель

Откройте `https://ADMIN_DOMAIN`. Войдите почтой и паролем из `.env`. Сразу смените пароль, если он где-то засветился, и включите TOTP в разделе безопасности.

Создайте тариф: название, цена больше нуля, срок в днях, лимит трафика в гигабайтах, лимит устройств. Пока тариф выключен, витрина его не отдаёт.

## 6. Подключить бота

В @BotFather укажите Mini App URL равным `MINI_APP_URL`. Напишите боту `/start`. Кнопка магазина должна открывать Mini App по HTTPS.

Пустой `BOT_TOKEN` в production останавливает контейнер бота. Это сделано специально: боевой магазин без бота не должен тихо крутить пустой цикл.

## 7. Проверить выдачу

Нужны ключи кассы и открытый production gate, либо отдельный staging с песочницей. На production песочница запрещена.

После оплаты воркер или сам webhook вызывает выдачу. В карточке пользователя появляется срок и ссылка подписки. Если Remnawave недоступен, платёж остаётся оплаченным, а выдача помечается ошибкой и повторяется. Текст ошибки виден в журнале процесса, не в ответе покупателю.

## 8. Копии

Каталог копий — `/data/backups` внутри backend и worker. Скрипт `scripts/backup.sh` снимает дамп. Перед обновлением `scripts/update.sh` сначала делает снимок и `pg_dump`, и только потом копирует файлы. Неудачная сборка возвращает снимок.

Секрет `APP_SECRET` нужен, чтобы расшифровать уже записанные секреты. Перед сменой запишите старое значение в `APP_SECRET_PREVIOUS`, выпустите новый `APP_SECRET`, перезапустите backend и worker, и только потом очистите предыдущий ключ.

## 9. Обновление

```bash
cd /opt/vpn-shop
sudo bash scripts/update-from-github.sh
```

Скрипт не затирает `.env`.

## Если контейнер не поднялся

```bash
docker compose logs --tail 100 backend
docker compose logs --tail 100 worker
docker compose logs --tail 50 caddy
```

Частые причины: пароль в `DATABASE_URL` не совпал с `DB_PASSWORD`, `APP_SECRET` короче 32 символов, не заданы `SUPPORT_PRO_DB_PASSWORD` или домены, DNS ещё не указывает на сервер, порты 80 или 443 заняты.
