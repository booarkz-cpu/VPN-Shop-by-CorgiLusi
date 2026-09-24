#!/usr/bin/env bash
# Start the shop on this machine without payment gateways, Telegram or Remnawave.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Engine and the Compose plugin, then run this script again." >&2
  exit 1
fi
docker compose version >/dev/null 2>&1 || { echo "Docker Compose plugin is required." >&2; exit 1; }

if [[ ! -f .env.test ]]; then
  python3 - <<'PY'
import secrets
from pathlib import Path
text = Path(".env.test.example").read_text()
db = secrets.token_hex(16)
secret = secrets.token_hex(32)
admin = "Admin-" + secrets.token_hex(8)
text = text.replace("CHANGE_ME_DB_PASSWORD", db)
text = text.replace("CHANGE_ME_APP_SECRET_AT_LEAST_32_CHARS", secret)
text = text.replace("CHANGE_ME_ADMIN_PASSWORD", admin)
Path(".env.test").write_text(text)
print("Wrote .env.test")
print("ADMIN_EMAIL=admin@example.test")
print(f"ADMIN_PASSWORD={admin}")
PY
else
  echo "Using existing .env.test"
  python3 - <<'PY'
from pathlib import Path
env = {}
for line in Path(".env.test").read_text().splitlines():
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    env[key] = value
print(f"ADMIN_EMAIL={env.get('ADMIN_EMAIL','')}")
print("ADMIN_PASSWORD is stored in .env.test")
if env.get("APP_ENV","").strip().lower() == "production":
    raise SystemExit("APP_ENV=production cannot be used with the test stack")
if env.get("PAYMENTS_SANDBOX","").strip().lower() not in {"1","true","yes","on"}:
    raise SystemExit("PAYMENTS_SANDBOX must be true in .env.test")
PY
fi

docker compose -f docker-compose.test.yml up -d --build

echo "Waiting for the API..."
ready=0
for _ in $(seq 1 60); do
  if curl -fsS --max-time 3 http://127.0.0.1:18080/health >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 5
done
if [[ "$ready" != "1" ]]; then
  echo "API did not become ready. Logs:" >&2
  docker compose -f docker-compose.test.yml logs --tail 80 backend >&2 || true
  exit 1
fi

export SANDBOX_API_BASE=http://127.0.0.1:18080
bash scripts/sandbox-e2e.sh

cat <<'EOF'

Test stack is up. Payment gateways are not connected.

  API       http://127.0.0.1:18080/health
  Admin     http://127.0.0.1:18081
  Cabinet   http://127.0.0.1:18082
  Mini App  http://127.0.0.1:18083

Sign in to the admin panel with ADMIN_EMAIL and ADMIN_PASSWORD from .env.test.
A plan named "Тестовый месяц" is created on an empty database.
The sandbox purchase creates a local subscription URL (sandbox://local/...).
It is not a working VPN profile until Remnawave is connected.

Ports listen on 127.0.0.1 only. On a VDS, open them from your computer:

  ssh -L 18080:127.0.0.1:18080 -L 18081:127.0.0.1:18081 \
      -L 18082:127.0.0.1:18082 -L 18083:127.0.0.1:18083 user@SERVER

Stop: docker compose -f docker-compose.test.yml down
EOF
