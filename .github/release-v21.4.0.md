# v21.4.0 stable — вложенные меню

Добавлены Telegram/Mini App деревья до 30 кнопок и четырёх уровней, папки, перенос, возврат, styles/custom emoji и обычные иконки. Предпросмотр использует общий компонент Mini App. Миниатюры Telegram разрешаются сервером, преобразуются в PNG; bot token не попадает в браузер. При внешней ошибке используется обычная иконка/название.

Изменения сериализуются в PostgreSQL. Циклы, потеря детей и слишком глубокий перенос блокируются. Mini App имеет отдельное атомарное сохранение с fingerprint: устаревший редактор получает 409, другие настройки сохраняются. Миграция `0061_menu_hierarchy` сохраняет старые кнопки в корне; downgrade настроенного дерева блокируется.

Текущие руководства, README, API, CHANGELOG, production-инструкция и описание состава лицензии 2.7 обновлены. Исторические отчёты сохраняют версии своих релизов.

Полная матрица остаётся незавершённой. Внешние платёжные/SMTP/VPN/restore проверки и подписанные мобильные пакеты требуют среды владельца. `production_ready`, `full_function_transfer`, `production_e2e_verified`, `signed` остаются false.

[Меню](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.4.0/docs/ru/MENU_TREE_CURRENT.md) · [Production](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.4.0/docs/ru/PRODUCTION_CURRENT.md) · [Матрица](https://github.com/booarkz-cpu/shop-by-boo/blob/v21.4.0/docs/ru/WORKSPACE_COVERAGE.md).
