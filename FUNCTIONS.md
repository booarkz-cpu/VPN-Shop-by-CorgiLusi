# Функции и отдельные инструкции

Наличие реализации означает наличие кода, а не подтверждённую работу чужой кассы, SMTP или VPN. Полная матрица статусов: [WORKSPACE_COVERAGE.md](docs/ru/WORKSPACE_COVERAGE.md).

| Функция | Отдельная инструкция |
| --- | --- |
| Регистрация, вход, профиль и сессии | [Кабинет](docs/ru/WORKSPACE_USER_GUIDE.md), [безопасность аккаунта](docs/ru/WORKSPACE_ACCOUNT_SECURITY.md) |
| Тарифы, конструктор и триал | [Администратор](docs/ru/WORKSPACE_ADMIN_GUIDE.md), [пользователь](docs/ru/WORKSPACE_USER_GUIDE.md) |
| Несколько подписок, названия и выбор профиля | [Подписки](docs/ru/WORKSPACE_SUBSCRIPTIONS.md) |
| Пропорциональная смена тарифа и докупка трафика | [Коммерческие операции](docs/ru/WORKSPACE_COMMERCE.md) |
| Кошелёк, платежи и квитанции | [Платежи](docs/ru/WORKSPACE_PAYMENTS.md), [кабинет](docs/ru/WORKSPACE_USER_GUIDE.md) |
| Подарки, конструктор подарков и подарочные карты | [Подписки и подарки](docs/ru/WORKSPACE_SUBSCRIPTIONS.md) |
| Автопродление и сохранённые условия | [Подписки](docs/ru/WORKSPACE_SUBSCRIPTIONS.md), [платежи](docs/ru/WORKSPACE_PAYMENTS.md) |
| Промокоды, рассылки и маркетинг | [Администратор](docs/ru/WORKSPACE_ADMIN_GUIDE.md) |
| Опросы, агрегированные ответы и награды | [Опросы](docs/ru/WORKSPACE_SURVEYS.md) |
| Бесплатный конкурс, выбор победителей | [Создание и розыгрыш](docs/ru/WORKSPACE_GIVEAWAYS.md#создать-конкурс) |
| Колесо призов и вероятности | [Настройка колеса](docs/ru/WORKSPACE_GIVEAWAYS.md#создать-колесо-призов) |
| Одноуровневые рефералы и заявки на выплаты | [Кабинет](docs/ru/WORKSPACE_USER_GUIDE.md), [администратор](docs/ru/WORKSPACE_ADMIN_GUIDE.md) |
| Переписка, приватные файлы, Support Pro | [Мост поддержки](docs/ru/WORKSPACE_SUPPORT_BRIDGE.md) |
| Telegram-бот и Mini App | [Администратор](docs/ru/WORKSPACE_ADMIN_GUIDE.md#telegram-бот) |
| Управление Remnawave, устройства и мониторинг | [Администратор](docs/ru/WORKSPACE_ADMIN_GUIDE.md), [архитектура](docs/ru/WORKSPACE_ARCHITECTURE.md) |
| Android/iOS клиента и администратора | [Мобильные приложения](MOBILE.md) |
| Backup, восстановление и обновление | [Эксплуатация](OPERATIONS_RUNBOOK_RU.md), [обновление](docs/ru/WORKSPACE_UPGRADE.md) |
| Роли, 2FA, аудит и секреты | [Безопасность](SECURITY.md) |
| HTTP API и идемпотентность | [API](API_REFERENCE_RU.md) |

Многоуровневые рефералы, merge аккаунтов, клиентский/native passkeys login, общий merge/split поддержки, безопасный импорт чужой базы, удалённый терминал, полный plugin runtime и native push/виджеты ещё не завершены. Данный выпуск добавляет конкурсы и колесо, но не объявляет остальные функции реализованными.

Изменения alpha.7: [ключи доступа администратора](docs/ru/ADMIN_PASSKEYS.md), [метрики, dashboard и alerts](docs/ru/OPERATIONS_MONITORING.md). Мобильный workflow использует версию текущего манифеста; без owner signing secrets APK/IPA не объявляются подписанными production assets.
