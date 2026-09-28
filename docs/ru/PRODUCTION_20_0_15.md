# Обновление 20.0.15 / production-подпись Mobile 2.15.0

[GitHub Release](https://github.com/booarkz-cpu/shop-by-boo/releases/tag/v20.0.15) · [Отчёт аудита](AUDIT_20_0_15.md).

## Обновление сервера

Сделайте проверенную резервную копию. Сохраните APP_SECRET и предыдущий ключ, чтобы не потерять доступ к зашифрованным настройкам. Перед развёртыванием проверьте:

- `APP_SECRET`: уникальный, минимум 32 символа; непустой `APP_SECRET_PREVIOUS` — также минимум 32.
- `ADMIN_PASSWORD`: минимум 12 символов, не placeholder. Он используется для первичного bootstrap; изменение env не меняет пароль существующего администратора в БД.
- Пароль внутри фактического `DATABASE_URL`: минимум 16 символов. В URL пароль кодируется percent-encoding. Смена значения env сама по себе не меняет пароль PostgreSQL: используйте согласованную ротацию пользователя БД и конфигурации.
- `SESSION_SECRET` Support Pro: минимум 32 символа. Его смена завершит существующие cookie-сессии.
- Redis AUTH, точные CORS origins, отдельный API_DOMAIN и TRUSTED_PROXY_CIDRS из инструкции 20.0.14 остаются обязательными.

Получите исходники тега `v20.0.15`, примените штатную процедуру обновления из [INSTALL_STEPS.md](../../INSTALL_STEPS.md). Проверьте `/health/ready`, вход администратора, 2FA/recovery, загрузку кабинета и Support Pro. Автоматического доступа к вашему VDS у процесса выпуска нет.

## Изменения входа

Recovery-код содержит 10 шестнадцатеричных символов, вводится в то же поле, что TOTP. Он одноразовый. После использования подготовьте новый набор кодов предусмотренным процессом настройки MFA.

Mobile 2.15.0 удаляет старые plaintext-токены: войдите заново. Android использует Keystore/AES-GCM, iOS — device-only Keychain. При смене API origin зашифрованный токен не переиспользуется. Для разблокировки сохранённой сессии настройте системный код устройства/биометрию. Если проверка недоступна, выйдите из сессии и выполните обычный вход; ошибка биометрии не открывает приложение.

Support Pro ограничивает серверную сессию 8 часами. После истечения срока потребуется новый вход.

## Production Android

Для обновления установленного `shop.remnawave.user` / `shop.remnawave.admin` требуется прежний ключ подписи. Новый произвольный ключ не обеспечит обновление поверх старой установки.

В GitHub → Settings → Secrets and variables → Actions настройте:

| Secret | Содержимое |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | Base64 постоянного файла JKS/PKCS12 владельца |
| `ANDROID_KEYSTORE_PASSWORD` | Пароль контейнера |
| `ANDROID_KEY_ALIAS` | Имя ключа |
| `ANDROID_KEY_PASSWORD` | Пароль ключа |

Локальная production-сборка выполняется так (значения передаются безопасным окружением):

```sh
export ANDROID_BUILD_MODE=release
export ANDROID_KEYSTORE=/absolute/path/owner-release.jks
bash scripts/build-android-apk.sh "$PWD/dist/mobile"
```

Ожидаемые файлы: `corgi_lusi_android_user_2_15_0_release.apk` и `corgi_lusi_android_admin_2_15_0_release.apk`. Версия 2.15.0, build 2150, debuggable выключен. Без keystore режим `release` завершается ошибкой. `verify-release` создаёт unsigned APK только для проверки компиляции; такой файл не публикуется как production.

Если это первая установка и постоянного keystore никогда не было, владелец может создать его с `keytool -genkeypair`, сохранить защищённую резервную копию и затем заполнить secrets. Существующий ключ нельзя заменять без решения о миграции установленных приложений.

## Production iOS

Нужен Apple Developer identity, разрешающий подпись bundle IDs `shop.remnawave.user` и `shop.remnawave.admin`. В GitHub Actions настройте:

| Secret | Содержимое |
| --- | --- |
| `IOS_CERTIFICATE_BASE64` | Base64 экспортированного P12 с приватным ключом |
| `IOS_CERTIFICATE_PASSWORD` | Пароль P12 |
| `IOS_USER_PROFILE_BASE64` | Base64 provisioning profile покупателя |
| `IOS_ADMIN_PROFILE_BASE64` | Base64 provisioning profile администратора |
| `IOS_TEAM_ID` | Apple Team ID |

Переменная Actions `IOS_EXPORT_METHOD`: `release-testing` по умолчанию; также поддерживаются `debugging`, `app-store-connect`, `enterprise`. Выбор должен соответствовать сертификату, профилям и аккаунту. Для release-testing устройства должны входить в профиль. Экспорт для App Store не равнозначен публикации в TestFlight/App Store; доставка и проверка магазина выполняются отдельно.

`scripts/build-ios-signed.sh` проверяет Team ID, bundle ID и срок профилей, импортирует ключ во временный keychain, собирает архив, экспортирует IPA, проверяет codesign и удаляет временные identity/profile файлы. Неподписанные IPA и Simulator ZIP остаются только техническими артефактами CI и не включаются в production-assets.

Официальные требования: [Apple signing/distribution](https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases), [Android signing](https://developer.android.com/studio/publish/app-signing).

## Публикация после настройки подписи

Actions → **Mobile packages** → **Run workflow** → ветка `main` на коммите релиза. Workflow проверит успешный общий CI, соответствие тега исходникам, SHA-256 и подписи. Затем прикрепит подписанные пакеты к `v20.0.15` и обновит `mobile-production-status.json`.

Если ключей нет, состояние будет `blocked_missing_signing_key` / `blocked_missing_apple_identity`; source release при этом доступен, production APK/IPA не заявляются готовыми. Ключи не выводятся в логи и не прикладываются к релизу. При уже опубликованных бинарных файлах workflow откажется их незаметно заменять: для нового содержимого нужен новый выпуск.

После публикации скачайте пакет и соседнюю `.sha256`, выполните `sha256sum -c <имя>.sha256`. Укажите HTTPS-адрес API вашей установки. Проверку входа, выхода, повторной блокировки, восстановления после перезапуска и покупки на staging выполните на реальном устройстве перед распространением покупателям.

## Платежи и доступность функций

Payment gate сохраняется закрытым до полного staging E2E v2. Этот релиз исправляет безопасность и сборку, но не является подтверждением готовности живых платежей или реализации встроенного VPN-движка. Исторические описания запланированных control-plane функций не заменяют их проверку на стенде.
