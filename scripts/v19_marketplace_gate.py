from pathlib import Path
import ast, json
root=Path(__file__).resolve().parents[1]
checks=[]
def ok(name, cond):
    checks.append((name, bool(cond)))

for rel in ["backend/app/marketplace_api.py","backend/app/remnawave_shop_api.py","backend/alembic/versions/0039_v19_marketplace.py","backend/app/bot.py"]:
    path=root/rel
    try: ast.parse(path.read_text())
    except Exception as e: ok(f"ast:{rel}", False); print(e)
    else: ok(f"ast:{rel}", True)
main=(root/"backend/app/main.py").read_text()
models=(root/"backend/app/models.py").read_text()
checks_text=[
    ("marketplace_router", "marketplace_router" in main),
    ("reseller_model", "class Reseller" in models),
    ("payment_reseller_attribution", "reseller_id" in models and "reseller_id=reseller_id" in main),
    ("telegram_buy", 'Command("buy")' in (root/"backend/app/bot.py").read_text()),
    ("telegram_subscription", 'Command("subscription")' in (root/"backend/app/bot.py").read_text()),
    ("migration", "0039_v19_marketplace" in (root/"backend/alembic/versions/0039_v19_marketplace.py").read_text()),
]
for n,c in checks_text: ok(n,c)
failed=[n for n,c in checks if not c]
print(f"v19 marketplace gate: {len(checks)-len(failed)}/{len(checks)}")
if failed:
    print("FAILED:", ", ".join(failed)); raise SystemExit(1)
