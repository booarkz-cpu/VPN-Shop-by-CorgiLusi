"""Contracts for gateway-free checkout and the production sandbox ban."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sandbox_is_refused_in_production_and_works_without_gateways():
    mode = (ROOT / "backend/app/sandbox_mode.py").read_text()
    main = (ROOT / "backend/app/main.py").read_text()
    payments = (ROOT / "backend/app/payments.py").read_text()
    cabinet = (ROOT / "backend/app/cabinet_api.py").read_text()
    bot = (ROOT / "backend/app/bot.py").read_text()
    assert "SANDBOX_ENVS" in mode
    assert '"production"' not in mode.split("SANDBOX_ENVS", 1)[1].split(")", 1)[0]
    assert "PAYMENTS_SANDBOX is allowed only when APP_ENV is development, test, or staging" in main
    assert "sandbox_checkout_requested" in main
    assert "sandbox_local_vpn" in main
    assert "sandbox://local/" in main
    assert "Тестовый месяц" in main
    assert 'event_id = data.get("event")' not in payments
    assert "Missing RollyPay timestamp" in payments
    assert "payments_sandbox_allowed" in payments
    assert "payments_sandbox_allowed" in cabinet
    assert "Telegram polling stays idle outside production" in bot
    assert (ROOT / "docker-compose.test.yml").is_file()
    assert (ROOT / "scripts/test-up.sh").is_file()
    assert "PAYMENTS_SANDBOX=true" in (ROOT / ".env.test.example").read_text()
    assert "APP_ENV=development" in (ROOT / ".env.test.example").read_text()
