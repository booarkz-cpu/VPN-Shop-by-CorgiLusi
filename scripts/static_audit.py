"""Fast source-level regression audit for VPN Shop by Corgi."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
errors=[]

# Python syntax / duplicate route guard.
for path in (ROOT / "backend" / "app").glob("*.py"):
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        errors.append(f"Python syntax: {path}: {exc}")

main=(ROOT/"backend"/"app"/"main.py").read_text(encoding="utf-8")
for marker in ["CSRF validation failed", "TrustedHostMiddleware", "X-Content-Type-Options", "require_permission("]:
    if marker not in main:
        errors.append(f"Security control missing: {marker}")

# Frontend regression that previously caused a broken JSX tree.
cab=(ROOT/"cabinet"/"src"/"main.tsx").read_text(encoding="utf-8")
if cab.count('option key={p} value={p}') != 1:
    errors.append("Cabinet payment-provider option block is malformed or duplicated")
if "VPN Shop by Corgi" not in cab:
    errors.append("Cabinet brand marker missing")

admin=(ROOT/"admin"/"src"/"main.tsx").read_text(encoding="utf-8")
if "navigate={setTab}" not in admin:
    errors.append("Admin dashboard navigation wiring missing")
if "design-system.css" not in admin:
    errors.append("Admin design-system import missing")

if errors:
    print("FAIL")
    print("\n".join(f"- {x}" for x in errors))
    raise SystemExit(1)
print("PASS: static audit checks passed")
