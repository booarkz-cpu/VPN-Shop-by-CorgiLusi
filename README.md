# VPN Shop by Corgi Lusi

Магазин VPN-подписок: кабинет, Mini App, админка, Telegram-бот, приложения Android и iOS, выдача доступа через Remnawave.

A VPN subscription shop: cabinet, Mini App, admin panel, Telegram bot, Android and iOS apps, and Remnawave fulfillment.

Магазин VPN-підписок: кабінет, Mini App, адмінка, Telegram-бот, застосунки Android і iOS, видача доступу через Remnawave.

Лицензия — [LICENSE](LICENSE). Подробные описания лежат в `docs/ru`, `docs/en` и `docs/uk`.

| | Русский | English | Українська |
| --- | --- | --- | --- |
| Возможности | [docs/ru/README.md](docs/ru/README.md) | [docs/en/README.md](docs/en/README.md) | [docs/uk/README.md](docs/uk/README.md) |
| Развёртывание | [docs/ru/DEPLOYMENT.md](docs/ru/DEPLOYMENT.md) | [docs/en/DEPLOYMENT.md](docs/en/DEPLOYMENT.md) | [docs/uk/DEPLOYMENT.md](docs/uk/DEPLOYMENT.md) |
| Проверка без касс | [docs/ru/TESTING.md](docs/ru/TESTING.md) | [docs/en/TESTING.md](docs/en/TESTING.md) | [docs/uk/TESTING.md](docs/uk/TESTING.md) |
| Живые платежи | [docs/ru/PAYMENTS.md](docs/ru/PAYMENTS.md) | [docs/en/PAYMENTS.md](docs/en/PAYMENTS.md) | [docs/uk/PAYMENTS.md](docs/uk/PAYMENTS.md) |

Песочница разрешена только при `APP_ENV=development`, `test` или `staging`. На `APP_ENV=production` процесс с `PAYMENTS_SANDBOX=true` не стартует. Пока не пройден staging E2E, живые платежи отвечают отказом.

## Русский

### Тестовый стенд

Стенд поднимает API, админку, кабинет и Mini App без YooKassa, Platega, RollyPay, Stripe, PayPal, Telegram и Remnawave. Подписка будет `sandbox://local/...`: это проверка магазина, а не рабочий VPN.

Нужны Docker Engine, плагин Compose и свободные порты 18080–18083.

```bash
git clone https://github.com/booarkz-cpu/VPN-Shop-by-CorgiLusi.git
cd VPN-Shop-by-CorgiLusi
bash scripts/test-up.sh
```

Скрипт создаёт `.env.test` со случайными секретами, открывает TCP 18080–18083 в файрволе хоста, собирает `docker-compose.test.yml`, ждёт `http://127.0.0.1:18080/health` и покупает тариф «Тестовый месяц» через песочницу. Пароль администратора печатается один раз: почта `admin@example.test`.

| Поверхность | Адрес |
| --- | --- |
| API | http://127.0.0.1:18080/health |
| Админка | http://127.0.0.1:18081 |
| Кабинет | http://127.0.0.1:18082 |
| Mini App | http://127.0.0.1:18083 |

Порты опубликованы на всех интерфейсах. Скрипт сам открывает TCP 18080–18083 в ufw, firewalld или iptables. С этой машины используйте адреса из таблицы. С другой машины замените `127.0.0.1` на IP сервера, например `http://IP:18081`. `COOKIE_SECURE=false` годится только для этой проверки: стенд не является публичным магазином. Если у хостера есть отдельный файрвол панели, разрешите в нём TCP 18080–18083.

Остановка: `docker compose -f docker-compose.test.yml down`. Флаг `-v` удаляет базу.

### Установка на VDS

Боевой магазин принимает заказы по HTTPS. Нужны Ubuntu или Debian, root по SSH, домен и пять имён на IP сервера: API, админка, Mini App, кабинет и Support Pro. Ещё нужны панель Remnawave и токен бота от @BotFather. Установщик сам открывает SSH, TCP 80, TCP 443 и UDP 443 в файрволе сервера. PostgreSQL, Redis и порт приложения наружу не публикуются. Если у хостера есть отдельный файрвол панели, разрешите в нём те же порты.

Пароли в `.env` — только буквы и цифры. Символы `@ : / #` ломают `DATABASE_URL`.

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git openssl
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
sudo git clone https://github.com/booarkz-cpu/VPN-Shop-by-CorgiLusi.git /opt/vpn-shop
cd /opt/vpn-shop
sudo bash install.sh
```

`install.sh` ставит Docker, если его ещё нет, и запускает `deploy/install-vps.sh`. Вопросы читаются в терминале SSH. Тот же результат вручную:

```bash
cd /opt/vpn-shop
cp .env.example .env
openssl rand -hex 32
```

Впишите в `.env`:

| Переменная | Значение |
| --- | --- |
| `APP_SECRET` | строка из `openssl rand -hex 32`, не короче 32 символов |
| `APP_ENV` | `production` |
| `DB_PASSWORD` и `POSTGRES_PASSWORD` | один и тот же пароль |
| `DATABASE_URL` | тот же пароль в `postgresql+asyncpg://vpnshop:ПАРОЛЬ@db:5432/vpnshop` |
| `BOT_TOKEN` | токен BotFather |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | первый вход в панель |
| `REMNAWAVE_URL`, `REMNAWAVE_TOKEN` | панель |
| `PUBLIC_BASE_URL`, `MINI_APP_URL`, `CABINET_URL` | адреса `https://` |
| `API_DOMAIN`, `ADMIN_DOMAIN`, `APP_DOMAIN`, `CABINET_DOMAIN` | имена без схемы |
| `SUPPORT_PRO_DOMAIN` | имя службы заявок |
| `SUPPORT_PRO_DB_PASSWORD` | отдельный пароль базы заявок |
| `SUPPORT_PRO_SSO_SECRET` | ещё одна строка `openssl rand -hex 32` |
| `COOKIE_SECURE` | `true` |
| `PAYMENTS_SANDBOX` | `false` |

Без `SUPPORT_PRO_DOMAIN` файл `docker-compose.yml` не стартует.

```bash
cd /opt/vpn-shop
docker compose up -d --build
curl -fsS https://API_DOMAIN/health
```

Ответ содержит "ok": true. Откройте `https://ADMIN_DOMAIN` и войдите почтой из `.env`. Ключи касс можно оставить пустыми: живые платежи закрыты, пока не пройден staging E2E. Подключение касс — в [docs/ru/PAYMENTS.md](docs/ru/PAYMENTS.md).
