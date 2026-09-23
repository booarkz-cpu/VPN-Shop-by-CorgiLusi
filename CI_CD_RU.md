# Corgi Lusi CI/CD

После push в `main` GitHub Actions автоматически:
- запускает backend compile/tests;
- проверяет Alembic migrations;
- собирает admin;
- валидирует Docker Compose;
- собирает и публикует backend/bot/admin/miniapp в GHCR;
- запускает pip-audit и npm audit.

Production deploy запускается вручную из Actions и требует GitHub Environment `production`
с секретами `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH` и при необходимости
`DEPLOY_PORT`.

Никакие реальные payment/Remnawave credentials в workflow не хранятся.
