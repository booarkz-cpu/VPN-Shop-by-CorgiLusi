"""Exercise the release config writer and the destructive update boundary."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_installer_produces_both_env_files_without_corrupting_secrets(tmp_path):
    script = (ROOT / "deploy/install-vps.sh").read_text()
    functions = script[script.index("env_line() {"):script.index("# Previous release contract:")]
    writer = script[script.index("umask 077\n{"):script.index("# Strict production firewall:")]
    # The writer runs in a disposable directory, before any apt, Docker, or UFW step.
    inputs = {name: "value" for name in (
        "APP_SECRET", "DB_PASSWORD", "SUPPORT_PRO_DB_PASSWORD", "SUPPORT_PRO_SSO_SECRET",
        "SUPPORT_PRO_SESSION_SECRET", "SUPPORT_PRO_ADMIN_PASSWORD", "API_DOMAIN",
        "ADMIN_DOMAIN", "APP_DOMAIN", "CABINET_DOMAIN", "SUPPORT_PRO_DOMAIN",
        "ADMIN_EMAIL", "ADMIN_PASSWORD", "BOT_TOKEN", "BOT_USERNAME", "ADMIN_TELEGRAM_ID",
        "REMNAWAVE_URL", "REMNAWAVE_TOKEN", "YOOKASSA_SHOP_ID", "YOOKASSA_SECRET_KEY",
        "PLATEGA_MERCHANT_ID", "PLATEGA_SECRET", "PLATEGA_REFUND_URL",
        "ROLLYPAY_API_KEY", "ROLLYPAY_SIGNING_SECRET", "ROLLYPAY_REFUND_URL",
        "DEFAULT_CURRENCY", "DEFAULT_LANGUAGE", "TZ_VALUE", "PRICE_1", "PRICE_3",
        "PRICE_6", "PRICE_12", "AUTO_RENEW_ENABLED", "AUTO_RENEW_LEAD_DAYS",
        "REQUIRED_TELEGRAM_CHANNEL", "ALERT_TELEGRAM_CHAT_ID", "REFERRAL_REWARD_PERCENT",
        "NOTIFICATION_EXPIRY_DAYS", "CADDY_EMAIL", "WEBHOOK_DOMAIN", "MINIAPP_DOMAIN",
        "BOT_DOMAIN", "PANEL_DOMAIN", "YANDEX_CLIENT_ID", "YANDEX_CLIENT_SECRET",
        "VK_CLIENT_ID", "VK_CLIENT_SECRET", "PAYMENTS_SANDBOX", "TRIAL_MAX_DAYS",
        "S3_ENDPOINT_URL", "S3_BUCKET", "S3_REGION", "S3_ACCESS_KEY", "S3_SECRET_KEY",
        "SUPPORT_REDIS_PASSWORD", "INSTALLER_VERSION",
    )}
    inputs.update(API_DOMAIN="api.example.com", ADMIN_DOMAIN="admin.example.com",
                  CABINET_DOMAIN="cabinet.example.com", SUPPORT_PRO_DOMAIN="support.example.com",
                  BOT_TOKEN="a'long$token", YOOKASSA_SECRET_KEY="configured-key")
    (tmp_path / "support-pro").mkdir()
    env = {**os.environ, **inputs}
    run = subprocess.run(["bash", "-c", "set -Eeuo pipefail\ndie(){ echo \"$*\" >&2; exit 1; }\n" + functions + writer],
                         cwd=tmp_path, env=env, text=True, capture_output=True)
    assert run.returncode == 0, run.stderr
    shop = (tmp_path / ".env").read_text()
    support = (tmp_path / "support-pro/.env").read_text()
    assert "SUPPORT_PRO_DB_PASSWORD='value'" in shop
    assert "SUPPORT_PRO_SSO_SECRET='value'" in shop
    assert "SUPPORT_PRO_DOMAIN='support.example.com'" in shop
    assert "ADMIN_CORS_ORIGINS='https://admin.example.com'" in shop
    assert "CABINET_CORS_ORIGINS='https://cabinet.example.com'" in shop
    assert "YOOKASSA_SECRET_KEY='configured-key'" in shop
    assert "BOT_TOKEN='a\\'long$token'" in shop
    assert "SESSION_SECRET='value'" in support
    assert "PUBLIC_ORIGIN='https://support.example.com'" in support
    assert (tmp_path / ".env").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "support-pro/.env").stat().st_mode & 0o777 == 0o600


def test_failed_database_dump_cancels_update_before_copy(tmp_path):
    (tmp_path / ".env").write_text("APP_ENV=production\n")
    (tmp_path / "marker").write_text("unchanged")
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    docker = fakebin / "docker"
    docker.write_text("#!/bin/sh\ncase \"$*\" in *'up -d db'*) exit 0;; *'exec -T db pg_dump'*) exit 1;; esac\nexit 0\n")
    docker.chmod(0o755)
    run = subprocess.run(["bash", str(ROOT / "scripts/update.sh")], cwd=tmp_path,
                         env={**os.environ, "APP_DIR": str(tmp_path), "PATH": f"{fakebin}:{os.environ['PATH']}"},
                         text=True, capture_output=True)
    assert run.returncode != 0
    assert "dump failed" in run.stderr
    assert (tmp_path / "marker").read_text() == "unchanged"
