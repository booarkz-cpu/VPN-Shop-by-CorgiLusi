# 03. Установка на VDS

**Нужно:** новый Ubuntu 24.04 / Debian 12 VDS, SSH-доступ с sudo, домен с пятью A-записями (API, админка, Mini App, кабинет, Support Pro), открытые TCP 80/443, бот-токен и доступ к Remnawave. Запишите домены и храните секреты вне GitHub.

1. Подключитесь по SSH и проверьте свободное место (`df -h /`) и DNS каждого имени (`dig +short A api.ВАШ-ДОМЕН`). Сверьте IP с VDS.
2. Установите Git: `sudo apt-get update && sudo apt-get install -y git`.
3. Скачайте именно проверенный тег:

   ```bash
   cd /opt
   sudo git clone --branch v20.0.22 --depth 1 https://github.com/booarkz-cpu/shop-by-boo.git vpn-shop-src
   cd /opt/vpn-shop-src
   sudo bash deploy/install-vps.sh
   ```

4. Отвечайте на вопросы установщика своими доменами и секретами. Для кассы выберите `none`, пока нет готового staging. Не вставляйте секреты в issue или чат.
5. После завершения выполните `cd /opt/vpn-shop && sudo docker compose ps`, затем откройте `https://api.ВАШ-ДОМЕН/health/ready` и админку в браузере. Включите TOTP для администратора.

Если установка остановилась, запишите текст ошибки без секретов и следуйте [подробной инструкции для текущего выпуска](../VDS_PRODUCTION_20_0_22.md). Живые платежи после установки закрыты.
