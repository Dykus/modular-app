import os, subprocess, sys, sqlite3, shutil

# Сам найти корень проекта
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("Корень проекта: " + BASE)

# =========================================================================
# ФАЙЛ 1. tools/export_history.py — генератор истории (исправлен)
# =========================================================================
os.makedirs(os.path.join(BASE, "tools"), exist_ok=True)
EXPORT = '''"""Генерирует modules/versions/history_seed.py из локальной базы.
Запускать на разработочной машине (Windows) после каждого нового релиза,
затем коммитить, чтобы история уезжала на серверы через Git."""
import os, sys, json, sqlite3

def root():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        if os.path.isfile(os.path.join(d, "run.py")):
            return d
        p = os.path.dirname(d)
        if p == d:
            break
        d = p
    return os.path.dirname(os.path.abspath(__file__))

TEMPLATE = """# АВТОГЕНЕРАЦИЯ: полная история релизов и журнала изменений.
# ВРУЧНУЮ НЕ ПРАВИТЬ'. Регенерация: python tools/export_history.py
import json as _json
from datetime import datetime as _dt

_RAW = \'\'\'{raw}\'\'\'
_DATA = _json.loads(_RAW)

_DATE_KEYS = ("released_at", "release_date", "created_at", "updated_at", "ts")


def _date(v):
    if not isinstance(v, str) or not v:
        return None
    try:
        return _dt.fromisoformat(v.replace(" ", "T"))
    except Exception:
        return None


def apply():
    # Добавляет в базу только НЕДОСТАЮЩИЕ релизы и записи журнала.
    # Ничего существующего не перезаписывает.
    from core.app import db
    from modules.versions.models import Release
    from modules.changelog.models import ChangelogEntry
    cols_r = set(Release.__table__.columns.keys())
    cols_c = set(ChangelogEntry.__table__.columns.keys())
    have_r = {r.version for r in Release.query.all()}
    added_r = 0
    for rec in _DATA["releases"]:
        if rec.get("version") in have_r:
            continue
        kw = {k: (_date(v) if k in _DATE_KEYS else v)
              for k, v in rec.items() if k in cols_r and k not in ("id", "is_current")}
        kw["is_current"] = False
        db.session.add(Release(**kw))
        added_r += 1
    have_c = {(c.module, c.description) for c in ChangelogEntry.query.all()}
    added_c = 0
    for rec in _DATA["changelog"]:
        if (rec.get("module"), rec.get("description")) in have_c:
            continue
        kw = {k: (_date(v) if k in _DATE_KEYS else v)
              for k, v in rec.items() if k in cols_c and k not in ("id",)}
        db.session.add(ChangelogEntry(**kw))
        added_c += 1
    if added_r or added_c:
        try:
            if not Release.query.filter_by(is_current=True).first():
                top = Release.query.order_by(Release.id.desc()).first()
                if top:
                    top.is_current = True
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    return added_r, added_c
"""


def generate():
    base = root()
    dbp = os.path.join(base, "data", "database.db")
    if not os.path.isfile(dbp):
        print("НЕТ базы: " + dbp)
        return False
    con = sqlite3.connect(dbp)
    con.row_factory = sqlite3.Row
    rels = [dict(r) for r in con.execute("SELECT * FROM release ORDER BY id")]
    chs = [dict(r) for r in con.execute("SELECT * FROM changelog_entry ORDER BY id")]
    con.close()
    for r in rels:
        r.pop("id", None)
        r.pop("is_current", None)
    for c in chs:
        c.pop("id", None)
    raw = json.dumps({"releases": rels, "changelog": chs}, ensure_ascii=False)
    out = TEMPLATE.replace("{raw}", raw)
    path = os.path.join(base, "modules", "versions", "history_seed.py")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\\n") as f:
        f.write(out)
    print("  history_seed.py: релизов = %d, записей журнала = %d" % (len(rels), len(chs)))
    return True


if __name__ == "__main__":
    generate()
'''
with open(os.path.join(BASE, "tools", "export_history.py"), "w", encoding="utf-8", newline="\n") as f:
    f.write(EXPORT)
print("  + tools/export_history.py (исправлен)")

# =========================================================================
# ФАЙЛ 2. update.sh — полностью по-русски
# =========================================================================
UPDATE_SH = '''#!/usr/bin/env bash
# ОДНА КОМАНДА ВЫКЛАДКИ: бэкап -> .env -> git pull -> зависимости ->
# установщик -> принудительное применение истории -> перезапуск службы -> проверка HTTP.
set -euo pipefail
cd "$(dirname "$0")"
PY=./venv/bin/python
if [ ! -x "$PY" ]; then
  echo "ОШИБКА: нет venv. Создайте: python3 -m venv venv && ./venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

echo "[1/7] Бэкап базы..."
./backup.sh

echo "[2/7] Файл .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  KEY=$($PY -c "import secrets; print(secrets.token_hex(32))")
  sed -i "s|^APP_SECRET_KEY=.*|APP_SECRET_KEY=${KEY}|" .env
  echo "  создан .env со случайным секретным ключом"
else
  echo "  .env уже есть, не трогаем"
fi

echo "[3/7] git pull..."
git pull --ff-only

echo "[4/7] Зависимости..."
$PY -m pip install -q -r requirements.txt

echo "[5/7] Установщик (если пришёл новый)..."
if [ -f tools/installers/install.py ]; then
  cp tools/installers/install.py ./install.py
  $PY install.py < /dev/null
else
  echo "  нового установщика нет, пропуск"
fi

echo "[6/7] Применение истории версий..."
$PY -c "
import sys
sys.path.insert(0, '.')
from core.app import create_app, db
app = create_app()
with app.app_context():
    try:
        from modules.versions import history_seed as hs
        added_r, added_c = hs.apply()
        if added_r or added_c:
            print(f'  история: добавлено релизов {added_r}, записей журнала {added_c}')
        else:
            print('  история: всё уже есть')
    except Exception as e:
        print(f'  ПРЕДУПРЕЖДЕНИЕ: история не применена: {e}')
"

echo "[7/7] Перезапуск службы..."
if systemctl is-enabled modular-app >/dev/null 2>&1; then
  sudo systemctl restart modular-app
  sleep 3
  echo "  служба: $(systemctl is-active modular-app)"
else
  echo "  служба ещё не установлена."
  echo "  Поставьте один раз: ./deploy/install-service.sh"
fi

PORT=$($PY -c "import config; print(config.PORT)")
echo "Проверка HTTP на порту ${PORT}:"
curl -sS -o /dev/null -w "  HTTP %{http_code}\\n" "http://127.0.0.1:${PORT}/" || echo "  сервер не ответил"
echo "Готово."
'''
with open(os.path.join(BASE, "update.sh"), "w", encoding="utf-8", newline="\n") as f:
    f.write(UPDATE_SH)
print("  + update.sh (полностью по-русски)")

# =========================================================================
# Шаг 3. Принудительно перегенерировать history_seed.py
# =========================================================================
hs = os.path.join(BASE, "modules", "versions", "history_seed.py")
if os.path.exists(hs):
    os.remove(hs)
    print("  - history_seed.py (старая версия удалена)")

print("Генерирую историю из локальной базы...")
proc = subprocess.run([sys.executable, os.path.join(BASE, "tools", "export_history.py")], cwd=BASE)
if proc.returncode != 0:
    print("MARKER_END: ГЕНЕРАЦИЯ НЕ УДАЛАСЬ")
    sys.exit(1)

# =========================================================================
# Шаг 4. Проверить количество релизов в базе
# =========================================================================
dbp = os.path.join(BASE, "data", "database.db")
con = sqlite3.connect(dbp)
count = con.execute("SELECT COUNT(*) FROM release").fetchone()[0]
con.close()
print(f"  В Windows-базе: {count} релизов")

# =========================================================================
# ФАЙЛ 5. sync_123.py — документация (0.12.3)
# =========================================================================
SYNC = '''"""Синхронизация документации: русский update.sh + принудительное применение истории (0.12.3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime
from core.app import create_app, db

CHANGELOG_BATCH = [
("changed", "deploy", "update.sh полностью на русском языке: все шаги, сообщения и проверки читаются по-русски."),
("added", "deploy", "Принудительное применение истории версий при каждом update.sh: история дольётся даже если автоприменение при старте не сработало."),
("fixed", "versions", "Гарантированное применение истории: отдельный шаг в update.sh, независимый от автоприменения при старте."),
]

def sync():
    from modules.changelog.models import ChangelogEntry
    from modules.versions.models import Release
    from modules.settings.models import Setting

    marker = db.session.get(Setting, "docs_sync_v123")
    if marker is None or marker.value != "1":
        for typ, mod, desc in CHANGELOG_BATCH:
            db.session.add(ChangelogEntry(author="синхронизация документации",
                                          change_type=typ, module=mod, description=desc))
        db.session.add(Setting(key="docs_sync_v123", value="1"))
        db.session.commit()
        print("  changelog: записей добавлено = %d" % len(CHANGELOG_BATCH))
    else:
        print("  changelog: партия 0.12.3 уже была, пропуск")

    if not Release.query.filter_by(version="0.12.3").first():
        Release.query.update({"is_current": False})
        db.session.add(Release(version="0.12.3",
            title="Русский update.sh + принудительная история",
            notes="Скрипт update.sh полностью переписан по-русски. Добавлен отдельный шаг принудительного применения истории версий — история дольётся на сервер даже если автоприменение при старте не сработало.",
            status="released", is_current=True))
        db.session.commit()
        print("  versions: релиз 0.12.3 создан и помечен текущим")
    else:
        print("  versions: релиз 0.12.3 уже есть")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        sync()
    print("Синхронизация 0.12.3 завершена.")
'''
with open(os.path.join(BASE, "sync_123.py"), "w", encoding="utf-8", newline="\n") as f:
    f.write(SYNC)
print("  + sync_123.py")

# =========================================================================
# Шаг 5. Применить синхронизацию к локальной базе
# =========================================================================
print("")
print("Применяю синхронизацию к локальной базе...")
print("-" * 50)
proc = subprocess.run([sys.executable, os.path.join(BASE, "sync_123.py")], cwd=BASE)
print("-" * 50)

if proc.returncode == 0:
    print("")
    print("=" * 56)
    print("MARKER_END: русский update.sh + история 0.12.3")
    print("=" * 56)
    print("Commit + Push: update.sh, modules/versions/history_seed.py,")
    print("               sync_123.py, tools/export_history.py,")
    print("               tools/installers/install.py")
    print("")
    print("Затем на VM: ./update.sh")
    print("Вывод теперь полностью по-русски!")
    print("История дольётся принудительно на шаге [6/7].")
else:
    print("")
    print("MARKER_END: синхронизация упала")