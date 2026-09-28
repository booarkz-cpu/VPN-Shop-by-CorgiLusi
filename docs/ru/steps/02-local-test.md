# 02. Тестовый запуск без реальных платежей

**Нужно:** Docker Engine и Docker Compose, Git, свободные порты 18080–18083. Команды вводите на своей машине в терминале.

1. Скачайте проект и перейдите в каталог:

   ```bash
   git clone https://github.com/booarkz-cpu/shop-by-boo.git vpn-shop-src
   cd vpn-shop-src
   ```

2. Запустите `bash scripts/test-up.sh`. Дождитесь результата проверки и запишите выведенный одноразовый пароль администратора.
3. Откройте `http://127.0.0.1:18081` (админка), `:18082` (кабинет), `:18083` (Mini App). Состояние API: `http://127.0.0.1:18080/health`.
4. Если что-то не открылось, выполните `docker compose --env-file .env.test -f docker-compose.test.yml ps` и посмотрите [разбор проблем](../TESTING.md). Исправьте ошибку до проверки покупки.
5. Остановите стенд: `docker compose --env-file .env.test -f docker-compose.test.yml down`. Не добавляйте `-v`, если хотите сохранить тестовую базу.

Здесь выдаётся тестовый адрес `sandbox://`, он **не подключает VPN**. Живые кассы, Telegram и Remnawave этим запуском не проверяются.
