import os, subprocess, sys

# Sam naht koren' proekta (rabotaet iz kornya i iz tools/installers/)
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    parent = os.path.dirname(d)
    if parent == d:
        break
    d = parent
BASE = d
print("Koren' proekta: " + BASE)

FILES = {
# =========================================================================
# ФАЙЛ 1. update.sh — ispravlena proverka sluzhby (systemctl is-enabled,
# bez pipe/grep, kotoryy vrал iz-za SIGPIPE pri pipefail).
# =========================================================================
"update.sh": '''#!/usr/bin/env bash
# ODNA KOMANDA VYKLADKI: bekap -> .env -> git pull -> zavisimosti ->
# ustanovshchik -> restart sluzhby -> proverka HTTP.
set -euo pipefail
cd "$(dirname "$0")"
PY=./venv/bin/python
if [ ! -x "$PY" ]; then
  echo "OSHIBKA: net venv. Sozdayte: python3 -m venv venv && ./venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

echo "[1/6] Bekap bazy..."
./backup.sh

echo "[2/6] Fayl .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  KEY=$($PY -c "import secrets; print(secrets.token_hex(32))")
  sed -i "s|^APP_SECRET_KEY=.*|APP_SECRET_KEY=${KEY}|" .env
  echo "  sozdan .env so sluchaynym sekretnym klyuchom"
else
  echo "  .env uzhe est, ne trogaem"
fi

echo "[3/6] git pull..."
git pull --ff-only

echo "[4/6] Zavisimosti..."
$PY -m pip install -q -r requirements.txt

echo "[5/6] Ustanovshchik (esli prishel novyy)..."
if [ -f tools/installers/install.py ]; then
  cp tools/installers/install.py ./install.py
  $PY install.py < /dev/null
else
  echo "  novogo ustanovshchika net, propusk"
fi

echo "[6/6] Perezaпуск sluzhby..."
if systemctl is-enabled modular-app >/dev/null 2>&1; then
  sudo systemctl restart modular-app
  sleep 3
  echo "  sluzhba: $(systemctl is-active modular-app)"
else
  echo "  sluzhba eshe ne ustanovlena."
  echo "  Postavte odin raz: ./deploy/install-service.sh"
fi

PORT=$($PY -c "import config; print(config.PORT)")
echo "Proverka HTTP na portu ${PORT}:"
curl -sS -o /dev/null -w "  HTTP %{http_code}\\n" "http://127.0.0.1:${PORT}/" || echo "  server ne otvetil"
echo "Gotovo."
''',
# =========================================================================
# ФАЙЛ 2. sync_121.py — tot zhe, chto byl na Windows: primeniт na servere
# releiz 0.12.1 i zapisi zhurnala (bazы Windows i VM srovnyayutsya).
# =========================================================================
"sync_121.py": '''"""Sinhronizaciya dokumentacii: test obnovleniya (0.12.1)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime
from core.app import create_app, db

CHANGELOG_BATCH = [
("added", "test_update", "\u0422\u0435\u0441\u0442\u043e\u0432\u044b\u0439 \u043c\u043e\u0434\u0443\u043b\u044c \u0434\u043b\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u0430 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f \u0447\u0435\u0440\u0435\u0437 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0449\u0438\u043a."),
("changed", "web", "\u0422\u0435\u0441\u0442\u043e\u0432\u0430\u044f \u043c\u0435\u0442\u043a\u0430 [TEST-UPDATE] \u0432 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043a\u0435 \u0441\u0442\u0440\u0430\u043d\u0438\u0446 \u0434\u043b\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f."),
]

def sync():
    from modules.changelog.models import ChangelogEntry
    from modules.versions.models import Release
    from modules.settings.models import Setting

    marker = db.session.get(Setting, "docs_sync_v121")
    if marker is None or marker.value != "1":
        for typ, mod, desc in CHANGELOG_BATCH:
            db.session.add(ChangelogEntry(author="\u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u0438",
                                          change_type=typ, module=mod, description=desc))
        db.session.add(Setting(key="docs_sync_v121", value="1"))
        db.session.commit()
        print("  changelog: zapisey dobavleno = %d" % len(CHANGELOG_BATCH))
    else:
        print("  changelog: partiya 0.12.1 uzhe byla, propusk")

    if not Release.query.filter_by(version="0.12.1").first():
        Release.query.update({"is_current": False})
        db.session.add(Release(version="0.12.1",
            title="\u0422\u0435\u0441\u0442 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f",
            notes="\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u0430 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f \u0447\u0435\u0440\u0435\u0437 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0449\u0438\u043a: \u0442\u0435\u0441\u0442\u043e\u0432\u044b\u0439 \u043c\u043e\u0434\u0443\u043b\u044c test_update, \u043c\u0435\u0442\u043a\u0430 \u0432 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043a\u0435.",
            status="released", is_current=True))
        db.session.commit()
        print("  versions: releiz 0.12.1 sozdan i pomachen tekushchim")
    else:
        print("  versions: releiz 0.12.1 uzhe est")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        sync()
    print("Sinhronizaciya 0.12.1 zavershena.")
''',
}

print("Kladu faily...")
print("")
n = 0
for rel, content in FILES.items():
    full = os.path.join(BASE, *rel.split("/"))
    d2 = os.path.dirname(full)
    if d2:
        os.makedirs(d2, exist_ok=True)
    nl = "\n" if rel.endswith(".sh") else None
    with open(full, "w", encoding="utf-8", newline=nl) as f:
        f.write(content)
    print("  + " + rel)
    n += 1

print("")
print("Zapuskayu sinhronizaciyu 0.12.1 (na etoy mashine)...")
print("-" * 50)
proc = subprocess.run([sys.executable, os.path.join(BASE, "sync_121.py")], cwd=BASE)
print("-" * 50)
if proc.returncode == 0:
    print("")
    print("=" * 56)
    print("MARKER_END: update.sh ispravlen, sync 0.12.1 v komplekte")
    print("=" * 56)
else:
    print("")
    print("=" * 56)
    print("MARKER_END: sinhronizaciya upala, sm. vyshe")
    print("=" * 56)
print("Dal'she: Commit + Push, potom na VM: ./update.sh")
input("Najmi Enter, aby zakryt okno...")