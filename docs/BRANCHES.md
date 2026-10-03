# Ветки и очистка проекта

Проверено 3 октября 2026 для `main` на коммите `341c88ea7cef601a8fede949ba0b42c584045a81` (PR #59, v21.2.0).

`main` содержит опубликованный код. Теги `v*` и `mobile-v*`, миграции, тесты, исторические CHANGELOG и документы в `docs/archive/` сохраняются: это история выпусков и обновления установок.

## Проверенные кандидаты на удаление

Следующие 13 веток полностью включены в `main`: для каждого SHA проверен `git merge-base --is-ancestor`. Перед удалением повторно проверьте SHA, отсутствие открытого PR и зависимых процессов. Результат относится к снимку ниже; новые изменения в ветке отменяют разрешение на её удаление.

| Ветка | Проверенный SHA |
| --- | --- |
| `fix/pending-grants-support-drafts-20261002` | `28ee64473c178ea1c1c34f56b6ac49a0b1f74d3c` |
| `release/alpha6-giveaways-20261003` | `ecb02ae7ad3c74d626e2cb39117dae962cc80892` |
| `release/alpha7-passkeys-monitoring-20261003` | `ebabea1842682398bf3b1839ac1ac2f668d93d8c` |
| `release/full-function-transfer-20261002` | `c2a3221aeca2972c79e65d132567c8dab48e5e89` |
| `release/v21.0.0-stable` | `274b62a25877599a3998641a3329148c459bb55e` |
| `release/v21.0.1-referrals-backup` | `795ee29a190d50dcca5caa37c2e1564161d0f632` |
| `release/v21.1.0-matrix-functions` | `eefe681735a4ab5d57ffcb8d8c61e7180b10e14b` |
| `release/v21.2.0-customer-operations` | `06f8588714c236128c96581a9eaf586c771983ec` |
| `rework/unified-workspace-20261001` | `2fc81762456453a40aa361c37f7dd00d0db7079d` |
| `transfer/account-readiness-20261002` | `3ac13e4ba7b0064d45e91c204cb5470ea97f9b2f` |
| `transfer/remaining-features-20261002` | `057989f7eb0e644e12fac42963ad2248c7d76ae1` |
| `transfer/support-bridge-20261002` | `f1fe2dd65fe79fb79a74ee8a62cb513b19306eb1` |
| `transfer/surveys-20261003` | `531f196880ced28d9d198d41377b6a279fbe4097` |

## Сохранённые ветки

Для следующих веток включение всей истории в `main` не подтверждено. Совпадение отдельных патчей после squash недостаточно для удаления. Открытые PR, в том числе #60 и обновления Dependabot, сохраняются; #60 содержит отдельные действия ограничения/восстановления доступа и альтернативную миграцию 0058, поэтому требует переноса с разрешением конфликтов, а не удаления.

- `audit/payment-contracts-vds-20260928` — `53d4210128308621916311cfb5e583faa24fccdb`
- `audit/v20.0.11-payments` — `8a38c9b1e538f7884ee5b727241fdb719a4955f6`
- `audit/v20.0.12-deep-security` — `fdd03fea9263efbb7b9aae88d340e7e4c132a6f9`
- `audit/v20.0.13-staging-e2e-guide` — `bcc43256cd962b3f481411f2d6aec6bafa404721`
- `audit/v20.0.14-security` — `2ba6f5e52dc6f37504263fa417f2782f8c73fe46`
- `audit/v20.0.8` — `6f849b16c8a133a4350a7611dc6c20493136430f`
- `audit/v20.0.9` — `4308344634dd2fc6b11aaeb3b1499839314258c4`
- `audit/v21.1.0-published-assets` — `1fbd9aa3739c3f0bae3312073b99997ef909433b`
- `cleanup/obsolete-publish-artifacts` — `8742d9ee39fafb326d74c65f99f0c41b89d80877`
- `dependabot/github_actions/actions/download-artifact-8` — `c34c50e53a3a66774665665edf8941dada62a655`
- `dependabot/github_actions/actions/github-script-9` — `0caa0cb59019d0e183ed428703d357f1c03d8ae7`
- `dependabot/github_actions/actions/setup-java-6` — `f013a2ec361290622fae3fb5a4aea9cb1a3706f1`
- `dependabot/github_actions/actions/setup-node-7` — `1a99b9b193336f7cbd52f2ceb0f0aedef86d19d8`
- `dependabot/github_actions/actions/upload-artifact-7` — `69be28dcf4844a166c1c138ab12cfa0cd926a4e8`
- `dependabot/npm_and_yarn/admin/vite-8.3.1` — `3227f0597f4e3a830aa5fca65d5cd5793af1b3f6`
- `dependabot/pip/backend/alembic-1.20.0` — `1d4e3867368f2cc9a902d85f28a348afc270e389`
- `dependabot/pip/backend/asyncpg-0.31.0` — `1a6f7e763e0b5f6df000f671f905c9264ff1187e`
- `dependabot/pip/backend/python-multipart-0.0.32` — `c0384dabca5a8529f965d513aa78505ca544d887`
- `dependabot/pip/backend/starlette-1.7.0` — `51ea323ad3fdf13e5dd4900e9cab193676c328c7`
- `docs/real-payments-readme-guide` — `d8c7c96514678fb083a4e419692491e3eaf173a0`
- `docs/staging-vds-e2e-operator-v20-0-18` — `462e2c54dd3319b25cd6dbcfaa867bd63ba0a697`
- `feat/customer-import-operations` — `ff024e714cee4ef2819d844e809b39c515ba4989`
- `fix/docker-buildx-v20.0.8` — `2a1db426b2a027a4e330231d02b0110b35d8f64c`
- `fix/docker-buildx-v20.0.8-ready` — `7f431321d4c07329e60d8bfbfe5ce96ba0956a1c`
- `fix/sandbox-payment-v20.0.10` — `669c91c227a858bbbd998cb7fe8c99aebc0ed2ad`
- `fix/v20-0-18-recovery-audit` — `cb0cc5e21d9fcf56c1c3b301ecd12707d109a0d9`
- `fix/v20.0.16-release-assets` — `23d81a3a8b89fcdb042ef30841e931956295b5c3`
- `fix/v20.0.16-vds-production` — `37d9f928ea6bc91a7a2d01d280a7f665d9b2f5c9`
- `release/mobile-2.14.1` — `72c92f9d78963cba748eb037b24f2e3a596575a2`
- `release/security-20.0.15` — `a0a383ab377167ccfaf6e1bca4d5fe62c05352d2`

## Ограничение удаления на GitHub

Активный ruleset `Rules` распространяется на все ветки и запрещает удаление. Использованное подключение GitHub умеет публиковать и объединять PR, но не предоставляет операцию удаления ветки. Поэтому удалённые ветки в этой очистке сохранены; защита не изменялась. Администратор с правом обхода ruleset может удалить проверенных кандидатов штатной кнопкой GitHub после повторной проверки. Список правил: https://github.com/booarkz-cpu/shop-by-boo/rules/23903620.

## Локальные файлы

Удалены кэши Python/pytest, результаты браузерных проверок, `admin/dist`, `cabinet/dist`, `miniapp/dist` и пустое рабочее дерево подготовки CMS. Зависимости `node_modules` оставлены для последующей разработки, но не входят в Git и релиз. `.gitignore` также исключает ссылки `node_modules`, отчёты браузера/покрытия, временные файлы редактора и результаты сборки iOS.

Перед очисткой смотрите `git status --short` и `git clean -ndX`. Не запускайте безусловный `git clean -fdX`: он может удалить локальный `.env`, ключи, базы и резервные копии. Удаляйте только явно перечисленные кэши и сборочные каталоги. Для новой задачи создавайте короткоживущую ветку от актуального `main`, публикуйте PR, проверяйте CI и после объединения повторно проверяйте ветку перед удалением.
