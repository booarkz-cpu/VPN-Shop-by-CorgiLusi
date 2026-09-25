# VDS: установка и запуск VPN Shop v20.0.12 в production

Для v20.0.13 используйте те же шаги, но замените тег в разделе 3 на `v20.0.13` и ожидаемую версию в `/health/ready` на `20.0.13`. Изменение staging-конфигурации теперь сбрасывает доказательство и закрывает gate; [контракт реализации v2](STAGING_E2E_V2_IMPLEMENTATION.md). Текущий runner всё ещё не разрешает живые платежи.

Этот регламент рассчитан на чистый Ubuntu 24.04 LTS или Debian 12, собственный домен, отдельную работающую панель Remnawave и доступ к серверу по SSH. Команды ниже выполняет администратор сервера. Замените имена `api.example.com`, `admin.example.com`, `app.example.com`, `cabinet.example.com`, `support.example.com` на свои. Не вставляйте настоящие ключи в переписку, скриншоты и журналы команд.

> **Граница готовности:** сервис можно запустить как production-инфраструктуру, однако приём **живых платежей остаётся закрытым**. В этом выпуске staging runner возвращает `full_e2e=false`, `contract_version=1`, а production gate требует полный E2E версии 2: счёт, webhook, выдачу, повтор и возврат. Запрос на включение gate отклоняется. Заполнение ключей провайдеров и ручное изменение БД не заменяют такую проверку. Развёртывание на вашей VDS и реальные интеграции не выполнялись при подготовке релиза.

## 1. Подготовьте сервер, DNS и доступ

1. Возьмите VDS с актуальными обновлениями, минимум 2 vCPU, 4 ГиБ RAM и свободным местом под PostgreSQL, резервные копии и контейнеры. Для реальных нагрузок измерьте потребление и увеличьте ресурсы. Обеспечьте отдельные проверяемые резервные копии вне VDS.
2. Создайте пять DNS-записей A (и AAAA только если IPv6 действительно работает) на внешний IP: `api`, `admin`, `app`, `cabinet`, `support`. Дождитесь разрешения с внешней машины (`dig +short api.example.com` и аналогично для остальных).
3. В панели хостера разрешите SSH только с ваших адресов, TCP 80/443, при необходимости UDP 443. Порты PostgreSQL 5432, Redis 6379 и внутреннего API 8000 наружу не открывайте. Проверьте, что 80/443 свободны: `sudo ss -lntup | grep -E ':(80|443)\b'`.
4. Войдите по SSH под пользователем с `sudo`. Если используете `ufw`, **сначала** разрешите ваш действующий SSH-порт и сохраните текущую сессию, затем `sudo ufw allow 80/tcp`, `sudo ufw allow 443/tcp`, `sudo ufw allow 443/udp`, `sudo ufw enable`. Правила Docker могут обходить `ufw`; следите за фактическими опубликованными портами в Compose и правилами хостера.
5. Установите обновления ОС и перезагрузите сервер при обновлении ядра: `sudo apt-get update && sudo apt-get upgrade -y`.

## 2. Установите Docker Engine с официального apt-репозитория

Сверьте актуальные команды для своей ОС с документацией Docker: [Ubuntu](https://docs.docker.com/engine/install/ubuntu/) / [Debian](https://docs.docker.com/engine/install/debian/). Для Ubuntu 24.04 / Debian 12:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git openssl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL "https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg" -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$ID $VERSION_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
```

Если система уже содержит конфликтующие `docker.io`, `docker-compose`, `podman-docker`, сначала выполните раздел удаления конфликтующих пакетов официальной инструкции. Доступ к Docker равен правам root; используйте `sudo docker`, не добавляйте обычного пользователя в группу `docker` ради удобства.

## 3. Получите именно проверенный релиз

```bash
sudo git clone https://github.com/booarkz-cpu/VPN-Shop-by-CorgiLusi.git /opt/vpn-shop
cd /opt/vpn-shop
sudo git fetch --tags origin
sudo git checkout --detach v20.0.12
git describe --tags --exact-match HEAD
```

Последняя команда должна вывести `v20.0.12`. При установке из ZIP скачайте два вложения GitHub Release (`...full_release.zip` и `...zip.sha256`) и проверьте `sha256sum -c ...zip.sha256` до распаковки; в архиве нет локальных секретов. Для дальнейших шагов используется git-копия. Не запускайте установщик через `curl | bash` из непроверенного URL.

## 4. Подготовьте секреты и конфигурацию магазина

```bash
cd /opt/vpn-shop
sudo cp .env.example .env
sudo cp support-pro/.env.example support-pro/.env
sudo chmod 600 .env support-pro/.env
openssl rand -hex 32
```

Последняя команда создаёт пример отдельного секрета. Запишите его в закрытый менеджер секретов; повторите для `APP_SECRET`, `SUPPORT_PRO_SSO_SECRET`, `SESSION_SECRET` и паролей. Файлы должны редактироваться из защищённой SSH-сессии, например `sudo nano .env` и `sudo nano support-pro/.env`. Не коммитьте их, не передавайте в тикеты. В `.env` установите:

| Поле | Значение |
| --- | --- |
| `APP_ENV`, `COOKIE_SECURE`, `PAYMENTS_SANDBOX` | `production`, `true`, `false` |
| `APP_SECRET` | уникальная строка `openssl rand -hex 32`; сохраните для восстановления шифрованных данных |
| `DB_PASSWORD`, `POSTGRES_PASSWORD` | один сильный пароль из букв и цифр |
| `DATABASE_URL` | `postgresql+asyncpg://vpnshop:ВАШ_ПАРОЛЬ@db:5432/vpnshop`, тот же пароль |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | ваш адрес и уникальный длинный пароль; после первого запуска смена в `.env` не меняет действующий пароль |
| `BOT_TOKEN`, `BOT_USERNAME` | токен BotFather и имя бота без `@` |
| `REMNAWAVE_URL`, `REMNAWAVE_TOKEN` | HTTPS URL существующей панели и её API-токен |
| `API_DOMAIN`, `ADMIN_DOMAIN`, `APP_DOMAIN`, `CABINET_DOMAIN`, `SUPPORT_PRO_DOMAIN` | пять действующих DNS-имён **без** `https://` |
| `PUBLIC_BASE_URL`, `MINI_APP_URL`, `CABINET_URL` | `https://api.example.com`, `https://app.example.com`, `https://cabinet.example.com` |
| `ADMIN_CORS_ORIGINS` | `https://admin.example.com,https://cabinet.example.com,https://app.example.com` |
| `SUPPORT_PRO_URL`, `SUPPORT_PRO_PUBLIC_ORIGIN` | `https://support.example.com` |
| `SUPPORT_PRO_DB_PASSWORD` | отдельный пароль БД поддержки из букв и цифр |
| `SUPPORT_PRO_SSO_SECRET` | второй независимый `openssl rand -hex 32` |
| `MOBILE_REQUIRE_PROOF`, `MOBILE_CLIENT_KEY` | оставьте согласованными с собранными мобильными клиентами; пустой ключ при включённой проверке отклоняет запросы |

Пароль в ручном `DATABASE_URL` при специальных символах надо кодировать как URL-компонент; простой вариант здесь — случайные буквенно-цифровые пароли. Проверьте `POSTGRES_PASSWORD` совпадает с `DB_PASSWORD`, а `SUPPORT_PRO_SSO_SECRET` совпадает с `SSO_SECRET` во втором файле. Не меняйте `APP_SECRET` на работающем сервере без процедуры ротации. Не включайте внешние платёжные системы до полноценного E2E следующего релиза.

В `support-pro/.env` установите `POSTGRES_PASSWORD` равным `SUPPORT_PRO_DB_PASSWORD` из корневого файла, `SESSION_SECRET` новым независимым случайным значением, `ADMIN_LOGIN` (например `admin`), `ADMIN_PASSWORD` отдельным паролем минимум 12 символов, `BOT_TOKEN` действительным токеном **отдельного** бота поддержки, `SSO_SECRET` равным корневому `SUPPORT_PRO_SSO_SECRET`, `PUBLIC_ORIGIN=https://support.example.com`, `COOKIE_SECURE=true`. `support_worker` создаёт Telegram-клиент при запуске, поэтому пустой `BOT_TOKEN` поддержки непригоден для полной Compose-конфигурации. Настройте в BotFather оба бота; не используйте один токен одновременно для двух процессов long polling.

Если планируете использовать нативные приложения, помните: опубликованный в мобильном приложении `MOBILE_CLIENT_KEY` известен клиенту и **не является серверным секретом**. Проверка подписи защищает от случайного несовпадения заголовков, а полномочия пользователя должны основываться на его сессии; свой ключ требует пересборки клиентов.

## 5. Проверьте конфигурацию и запустите контейнеры

```bash
cd /opt/vpn-shop
sudo docker compose --env-file .env config --quiet
sudo docker compose up -d --build
sudo docker compose ps
```

Команда `config --quiet` проверяет синтаксис и обязательные переменные, не печатая секреты. `up -d --build` собирает API, bot, worker, веб-клиенты и поддержку. Дождитесь состояния `healthy` у БД, Redis, backend, клиентов, Support Pro и Caddy; контейнер `support_migrate` штатно завершается после миграций. Backend запускает `alembic upgrade head` при старте. Для поиска ошибки:

```bash
sudo docker compose logs --tail=100 backend worker bot caddy support_pro support_worker
sudo docker compose logs --tail=100 support_migrate db support_db
sudo docker compose exec backend alembic current
```

Не публикуйте полные логи без удаления токенов и личных данных. Если Caddy не получает сертификат, проверьте DNS, внешние порты и отсутствие другого веб-сервера. Если backend не стартует, проверьте `APP_SECRET`, `ADMIN_PASSWORD`, URL БД, наличие Redis, `COOKIE_SECURE=true` и `PAYMENTS_SANDBOX=false`.

## 6. Проверьте HTTPS и первоначальный вход

Замените примерные домены на свои:

```bash
curl -fsS https://api.example.com/health/ready
curl -I https://admin.example.com/
curl -I https://app.example.com/
curl -I https://cabinet.example.com/
curl -fsS https://support.example.com/health
```

`/health/ready` должен вернуть `ok: true`, `version: 20.0.12`, `database: true`, `redis: true`. Откройте админку по HTTPS, войдите `ADMIN_EMAIL`/`ADMIN_PASSWORD` и немедленно включите TOTP. Инициализируйте отдельную учётную запись Support Pro (команда выводит секрет TOTP — запускайте только в закрытом терминале):

```bash
cd /opt/vpn-shop
sudo docker compose exec support_pro python -m app.cli init
```

Сохраните TOTP в защищённом приложении и проверьте вход на `https://support.example.com`. В @BotFather настройте Web App основного бота с `https://app.example.com`; отправьте `/start` и проверьте загрузку магазина. Убедитесь, что Remnawave отвечает на API-токен, проверьте тарифы и отображение витрины без реального списания. Пробное списание и автоматическую выдачу на production в этом релизе не проводите.

## 7. Эксплуатация, копии, контроль и обновления

1. В админке включите расписание резервных копий, шифрование и retention. `scripts/backup.sh` **не создаёт дамп**: он выводит подсказку. Перед обновлением проверьте, что созданная копия скачана за пределы VDS, проверена контрольной суммой и пробно восстановлена в изолированной среде. Отдельно сохраните оба `.env`, доступ к их секретам и конфигурацию Remnawave. Утечка копии с платежами и пользователями требует процедуры реагирования.
2. Проверяйте `sudo docker compose ps`, `/health/ready`, срок TLS, свободное место `df -h`, журналы ошибок и выполнение резервных копий. Настройте внешние оповещения. Порты PostgreSQL и Redis должны оставаться только в сети Compose.
3. Для обновления изучите changelog новой версии, сохраните проверенный backup и секреты, затем `sudo git fetch --tags origin`, `sudo git checkout --detach vНОВАЯ_ВЕРСИЯ`, `sudo docker compose up -d --build`; проверьте миграции и `/health/ready`. Миграции базы могут не поддерживать обратный ход: при откате после миграции возвращайте совместимую заранее проверенную копию БД вместе с кодом и медиа в изолированном окне обслуживания.
4. Для штатной остановки: `sudo docker compose stop`. **Не** применяйте `docker compose down -v`: это удаляет именованные тома базы и медиа. Для возобновления: `sudo docker compose up -d`.

Версию, артефакт и подробности аудита см. в [заметках релиза](../../.github/release-v20.0.12.md). Текущий production gate платежей нельзя открыть инструкцией по установке; нужна отдельная реализация и успешная проверка полного E2E v2.
