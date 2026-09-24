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

## English

### Test stand

The stand runs the API, admin panel, cabinet and Mini App without YooKassa, Platega, RollyPay, Stripe, PayPal, Telegram or Remnawave. The subscription link is `sandbox://local/...`. That checks the shop. It is not a working VPN profile.

You need Docker Engine, the Compose plugin, and free ports 18080–18083.

```bash
git clone https://github.com/booarkz-cpu/VPN-Shop-by-CorgiLusi.git
cd VPN-Shop-by-CorgiLusi
bash scripts/test-up.sh
```

The script writes `.env.test` with random secrets, opens TCP 18080–18083 in the host firewall, builds `docker-compose.test.yml`, waits for `http://127.0.0.1:18080/health`, and buys the plan "Тестовый месяц" through the sandbox. The admin password is printed once. The email is `admin@example.test`.

| Surface | URL |
| --- | --- |
| API | http://127.0.0.1:18080/health |
| Admin | http://127.0.0.1:18081 |
| Cabinet | http://127.0.0.1:18082 |
| Mini App | http://127.0.0.1:18083 |

The ports are published on every interface. The script opens TCP 18080–18083 in ufw, firewalld, or iptables. On this machine use the table above. From another machine replace `127.0.0.1` with the server IP, for example `http://IP:18081`. `COOKIE_SECURE=false` is only for this check: the stand is not a public shop. If the hoster has a panel firewall, allow TCP 18080–18083 there too.

Stop with `docker compose -f docker-compose.test.yml down`. Add `-v` to drop the database.

### Install on a VDS

A live shop takes orders over HTTPS. You need Ubuntu or Debian, root SSH, a domain, and five names pointing at the server: API, admin, Mini App, cabinet, and Support Pro. You also need a Remnawave panel and a bot token from @BotFather. The installer opens SSH, TCP 80, TCP 443 and UDP 443 in the server firewall. PostgreSQL, Redis and the application port stay unpublished. If the hoster has a panel firewall, allow the same ports there.

Keep `.env` passwords to letters and digits. The characters `@ : / #` break `DATABASE_URL`.

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git openssl
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
sudo git clone https://github.com/booarkz-cpu/VPN-Shop-by-CorgiLusi.git /opt/vpn-shop
cd /opt/vpn-shop
sudo bash install.sh
```

`install.sh` installs Docker when it is missing, then runs `deploy/install-vps.sh`. The questions are read on the SSH terminal. The same result by hand:

```bash
cd /opt/vpn-shop
cp .env.example .env
openssl rand -hex 32
```

Set in `.env`:

| Variable | Value |
| --- | --- |
| `APP_SECRET` | output of `openssl rand -hex 32`, at least 32 characters |
| `APP_ENV` | `production` |
| `DB_PASSWORD` and `POSTGRES_PASSWORD` | the same password |
| `DATABASE_URL` | that password inside `postgresql+asyncpg://vpnshop:PASSWORD@db:5432/vpnshop` |
| `BOT_TOKEN` | the BotFather token |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | the first panel login |
| `REMNAWAVE_URL`, `REMNAWAVE_TOKEN` | the panel |
| `PUBLIC_BASE_URL`, `MINI_APP_URL`, `CABINET_URL` | `https://` origins |
| `API_DOMAIN`, `ADMIN_DOMAIN`, `APP_DOMAIN`, `CABINET_DOMAIN` | hostnames without a scheme |
| `SUPPORT_PRO_DOMAIN` | ticket desk hostname |
| `SUPPORT_PRO_DB_PASSWORD` | a separate database password |
| `SUPPORT_PRO_SSO_SECRET` | another `openssl rand -hex 32` string |
| `COOKIE_SECURE` | `true` |
| `PAYMENTS_SANDBOX` | `false` |

`docker-compose.yml` does not start without `SUPPORT_PRO_DOMAIN`.

```bash
cd /opt/vpn-shop
docker compose up -d --build
curl -fsS https://API_DOMAIN/health
```

The body contains "ok": true. Open `https://ADMIN_DOMAIN` and sign in with the email from `.env`. Gateway keys can stay empty: live charges stay closed until a staging end-to-end run has passed. Connecting gateways is described in [docs/en/PAYMENTS.md](docs/en/PAYMENTS.md).
