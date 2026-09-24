# Розгортання магазину

Цей файл для сервера, який прийматиме справжні замовлення. Щоб перевірити магазин без кас, Telegram і Remnawave, йдіть у [TESTING.md](TESTING.md).

## Що потрібно

- Ubuntu або Debian і root по SSH.
- Домен і чотири імена, які вказують на IP сервера: API, адмінка, Mini App, кабінет. П’яте ім’я потрібне службі заявок, бо `docker-compose.yml` не стартує без `SUPPORT_PRO_DOMAIN`.
- Працююча панель Remnawave: базова адреса і API-токен.
- Токен бота від @BotFather.
- Пошта адміністратора і довгий пароль.
- Встановлювач сам відкриває SSH, TCP 80, TCP 443 і UDP 443. PostgreSQL, Redis і API назовні не публікуються. Зовнішній файрвол панелі хостера має пропускати ті самі порти.

Паролі в `.env` складайте з літер і цифр. Символи `@ : / #` ламають `DATABASE_URL`.

## 1. Поставити Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git openssl
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
docker compose version
```

## 2. Отримати джерела

```bash
sudo git clone https://github.com/booarkz-cpu/VPN-Shop-by-CorgiLusi.git /opt/vpn-shop
cd /opt/vpn-shop
```

Те саме робить `sudo bash install.sh`: скрипт ставить Docker і викликає `deploy/install-vps.sh`, який ставить питання в терміналі SSH. Запуск через `curl | bash` читає відповіді з `/dev/tty`.

## 3. Заповнити оточення

```bash
cp .env.example .env
openssl rand -hex 32
```

| Змінна | Значення |
| --- | --- |
| `APP_SECRET` | рядок з `openssl rand -hex 32`, не коротший за 32 символи |
| `APP_ENV` | `production` |
| `DB_PASSWORD` і `POSTGRES_PASSWORD` | один і той самий пароль |
| `DATABASE_URL` | той самий пароль у `postgresql+asyncpg://vpnshop:ПАРОЛЬ@db:5432/vpnshop` |
| `BOT_TOKEN` | токен BotFather |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | перший вхід у панель |
| `ADMIN_TELEGRAM_ID` | ваш числовий id, якщо потрібна команда `/ops` |
| `REMNAWAVE_URL`, `REMNAWAVE_TOKEN` | панель |
| `PUBLIC_BASE_URL` | адреса API з `https://` |
| `MINI_APP_URL` | адреса Mini App |
| `CABINET_URL` | адреса кабінету |
| `API_DOMAIN`, `ADMIN_DOMAIN`, `APP_DOMAIN`, `CABINET_DOMAIN` | імена без схеми |
| `SUPPORT_PRO_DOMAIN` | ім’я служби заявок |
| `SUPPORT_PRO_DB_PASSWORD` | окремий пароль бази заявок |
| `SUPPORT_PRO_SSO_SECRET` | `openssl rand -hex 32` |
| `COOKIE_SECURE` | `true` |
| `PAYMENTS_SANDBOX` | `false` |

`PAYMENTS_SANDBOX=true` разом із `APP_ENV=production` зупиняє процес текстом `PAYMENTS_SANDBOX is allowed only when APP_ENV is development, test, or staging`.

Ключі кас на цьому кроці можна лишити порожніми. Живі платежі закриті, поки не виконано кроки з [PAYMENTS.md](PAYMENTS.md).

## 4. Запустити контейнери

```bash
cd /opt/vpn-shop
docker compose up -d --build
docker compose ps
```

PostgreSQL і Redis стають здоровими, backend застосовує міграції Alembic, воркер стартує після API, панелі чекають здоровий API, Caddy публікує 80 і 443.

Перевірка:

```bash
curl -fsS https://API_DOMAIN/health
```

Відповідь містить `"ok": true`.

Перший запуск створює адміністратора. Наступний запуск не перезаписує пароль з `.env`.

## 5. Увійти в панель

Відкрийте `https://ADMIN_DOMAIN`. Увійдіть поштою і паролем з `.env`. Змініть пароль, якщо він десь засвітився, і ввімкніть TOTP у розділі безпеки.

Створіть тариф: назва, ціна більша за нуль, строк у днях, ліміт трафіку в гігабайтах, ліміт пристроїв. Вимкнений тариф вітрина не віддає.

## 6. Підключити бота

У @BotFather вкажіть Mini App URL рівним `MINI_APP_URL`. Напишіть боту `/start`. Кнопка магазину має відкрити Mini App через HTTPS.

Порожній `BOT_TOKEN` у production зупиняє контейнер бота. Бойовий магазин не повинен тихо крутити порожній цикл.

## 7. Перевірити видачу

Потрібні ключі каси і відкритий production gate або окремий staging із пісочницею. На production пісочниця заборонена.

Після оплати webhook або воркер викликає видачу. У картці користувача з’являються строк і посилання. Якщо Remnawave недоступний, платіж лишається оплаченим, а видача позначається помилкою і повторюється. Текст помилки лишається в журналі процесу.

## 8. Копії

Каталог копій — `/data/backups` усередині backend і worker. `scripts/backup.sh` знімає дамп. `scripts/update.sh` спочатку робить знімок і `pg_dump`, і лише потім копіює файли.

`APP_SECRET` розшифровує вже записані секрети. Перед зміною запишіть старе значення в `APP_SECRET_PREVIOUS`, випустіть новий `APP_SECRET`, перезапустіть backend і worker, і лише потім очистіть попередній ключ.

## 9. Оновлення

```bash
cd /opt/vpn-shop
sudo bash scripts/update-from-github.sh
```

Скрипт не затирає `.env`.

## Якщо контейнер не піднявся

```bash
docker compose logs --tail 100 backend
docker compose logs --tail 100 worker
docker compose logs --tail 50 caddy
```

Типові причини: пароль у `DATABASE_URL` не збігся з `DB_PASSWORD`, `APP_SECRET` коротший за 32 символи, не задані `SUPPORT_PRO_DB_PASSWORD` або домени, DNS ще не вказує на сервер, порти 80 або 443 зайняті.
