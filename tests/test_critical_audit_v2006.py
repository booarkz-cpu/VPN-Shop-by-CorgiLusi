"""20.0.6: a staging help line must not open the production payment gate."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_live_version_is_20_0_6():
    main = (ROOT / "backend/app/main.py").read_text()
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    builder = (ROOT / "scripts/build-release.sh").read_text()
    assert main.index('APP_VERSION = "20.0.7"') < main.index('APP_VERSION = "20.0.6"')
    assert main.index('APP_VERSION = "20.0.6"') < main.index('APP_VERSION = "20.0.5"')
    assert main.index('APP_VERSION = "20.0.5"') < main.index('APP_VERSION = "20.0.4"')
    assert main.index('APP_VERSION = "3.1.6"') < main.index('APP_VERSION = "3.1.5"')
    assert installer.index('INSTALLER_VERSION="20.0.7"') < installer.index('INSTALLER_VERSION="20.0.6"')
    assert installer.index('INSTALLER_VERSION="20.0.6"') < installer.index('INSTALLER_VERSION="20.0.5"')
    assert installer.index('INSTALLER_VERSION="3.1.6"') < installer.index('INSTALLER_VERSION="3.1.5"')
    assert builder.index('VERSION="20.0.7"') < builder.index('VERSION="20.0.6"')
    assert builder.index('VERSION="20.0.6"') < builder.index('VERSION="20.0.5"')
    assert builder.index('VERSION="3.1.6"') < builder.index('VERSION="3.1.5"')
    first = main.index('APP_VERSION = "')
    assert main[first:first + len('APP_VERSION = "20.0.7"')] == 'APP_VERSION = "20.0.7"'


def test_full_pass_requires_its_own_line_and_localhost_checks():
    main = (ROOT / "backend/app/main.py").read_text()
    assert '"FULL_E2E_PASS" in text' in main
    assert 'any(line.strip()=="FULL_E2E_PASS" for line in text.splitlines())' in main
    assert 'client_host not in {"127.0.0.1","::1"}' in main
    for path in ("/api/internal/staging-e2e/verify", "/api/internal/staging-e2e/refund", "/api/internal/staging-e2e/refund-status", "/api/internal/staging-e2e/remnawave"):
        assert path in main
    assert "platega_refund_url" in main and "rollypay_refund_status_url" in main


def test_runner_prints_the_marker_only_as_the_final_line():
    host = (ROOT / "scripts/staging-e2e.sh").read_text()
    image = (ROOT / "backend/scripts/staging-e2e.sh").read_text()
    assert host == image
    assert (ROOT / "scripts/staging-e2e.sh").stat().st_mode & 0o111
    lines = [line for line in host.splitlines() if "FULL_E2E_PASS" in line]
    assert lines == ["echo FULL_E2E_PASS"]
    assert host.strip().splitlines()[-1] == "echo FULL_E2E_PASS"
    assert "[CHECKOUT]" in host and "awaiting_checkout" in host
    assert "в контейнере backend нет curl" in host
    assert "/api/internal/staging-e2e/verify" in host
    assert "/api/internal/staging-e2e/refund" in host


def test_readme_explains_staging_in_three_languages():
    readme = (ROOT / "README.md").read_text()
    assert "## Changelog" in readme and "### 20.0.6" in readme
    assert "## Русский" in readme and "## English" in readme and "## Українська" in readme
    assert "Как пройти staging E2E" in readme
    assert "How to pass staging E2E" in readme
    assert "Як пройти staging E2E" in readme
    assert "FULL_E2E_PASS" in readme
    assert "Ниже сохранена история релизов." in readme
    assert "20.0.6" in (ROOT / "SECURITY.md").read_text()
