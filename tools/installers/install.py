import os, subprocess, sys, sqlite3

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
# ФАЙЛ 1. tools/export_history.py — генератор истории (запускать ТОЛЬКО на Windows)
# =========================================================================
os.makedirs(os.path.join(BASE, "tools"), exist_ok=True)
EXPORT = '''"""Генерирует modules/versions/history_seed.py из локальной базы.
ВАЖНО: запускать ТОЛЬКО на разработочной машине (Windows), где полная база.
На сервере (Linux) НЕ запускать — там база неполная, и история обрежется.
Запуск: python tools/export_history.py, затем commit + push."""
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
# СГЕНЕРИРОВАНО НА: {generated_on}
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
    from datetime import datetime
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = TEMPLATE.replace("{raw}", raw).replace("{generated_on}", generated)
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
# Шаг 2. Определить, где мы запущены (Windows или Linux)
# =========================================================================
is_windows = sys.platform.startswith("win")
if is_windows:
    print("  среда: Windows (разработочная машина)")
    print("  генерирую history_seed.py из полной базы...")
    sys.path.insert(0, os.path.join(BASE, "tools"))
    import export_history as EH
    hs = os.path.join(BASE, "modules", "versions", "history_seed.py")
    if os.path.exists(hs):
        os.remove(hs)
        print("  - history_seed.py (старая версия удалена)")
    if not EH.generate():
        print("MARKER_END: ГЕНЕРАЦИЯ НЕ УДАЛАСЬ")
        sys.exit(1)
    dbp = os.path.join(BASE, "data", "database.db")
    con = sqlite3.connect(dbp)
    count = con.execute("SELECT COUNT(*) FROM release").fetchone()[0]
    con.close()
    print(f"  В Windows-базе: {count} релизов")
else:
    print("  среда: Linux (сервер)")
    print("  НЕ генерирую history_seed.py — использую версию из Git")
    hs = os.path.join(BASE, "modules", "versions", "history_seed.py")
    if os.path.exists(hs):
        print("  history_seed.py уже есть в Git")
    else:
        print("  ПРЕДУПРЕЖДЕНИЕ: history_seed.py отсутствует!")
        print("  Запустите на Windows: python tools/export_history.py, затем commit + push")

# =========================================================================
# ФАЙЛ 3. sync_124.py — документация (0.12.4)
# =========================================================================
SYNC = '''"""Синхронизация документации: исправление генерации истории (0.12.4)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime
from core.app import create_app, db

CHANGELOG_BATCH = [
("fixed", "tools", "export_history.py теперь запускается ТОЛЬКО на разработочной машине (Windows), где полная база. На сервере (Linux) история берётся готовой из Git, а не генерируется из неполной локальной базы."),
("added", "tools", "Проверка платформы: генератор истории автоматически определяет Windows/Linux и на сервере не запускается."),
]

def sync():
    from modules.changelog.models import ChangelogEntry
    from modules.versions.models import Release
    from modules.settings.models import Setting

    marker = db.session.get(Setting, "docs_sync_v124")
    if marker is None or marker.value != "1":
        for typ, mod, desc in CHANGELOG_BATCH:
            db.session.add(ChangelogEntry(author="синхронизация документации",
                                          change_type=typ, module=mod, description=desc))
        db.session.add(Setting(key="docs_sync_v124", value="1"))
        db.session.commit()
        print("  changelog: записей добавлено = %d" % len(CHANGELOG_BATCH))
    else:
        print("  changelog: партия 0.12.4 уже была, пропуск")

    if not Release.query.filter_by(version="0.12.4").first():
        Release.query.update({"is_current": False})
        db.session.add(Release(version="0.12.4",
            title="Исправление генерации истории",
            notes="Генератор истории версий (tools/export_history.py) теперь запускается только на разработочной машине (Windows), где полная база. На сервере (Linux) история берётся готовой из Git, а не генерируется из неполной локальной базы — это предотвращает обрезание истории.",
            status="released", is_current=True))
        db.session.commit()
        print("  versions: релиз 0.12.4 создан и помечен текущим")
    else:
        print("  versions: релиз 0.12.4 уже есть")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        sync()
    print("Синхронизация 0.12.4 завершена.")
'''
with open(os.path.join(BASE, "sync_124.py"), "w", encoding="utf-8", newline="\n") as f:
    f.write(SYNC)
print("  + sync_124.py")

# =========================================================================
# Шаг 3. Применить синхронизацию к локальной базе (на любой платформе)
# =========================================================================
print("")
print("Применяю синхронизацию к локальной базе...")
print("-" * 50)
proc = subprocess.run([sys.executable, os.path.join(BASE, "sync_124.py")], cwd=BASE)
print("-" * 50)

if proc.returncode == 0:
    print("")
    print("=" * 56)
    print("MARKER_END: исправление генерации истории 0.12.4")
    print("=" * 56)
    if is_windows:
        print("Commit + Push: modules/versions/history_seed.py,")
        print("               sync_124.py, tools/export_history.py,")
        print("               tools/installers/install.py")
        print("")
        print("Затем на VM: git pull && ./update.sh")
        print("История дольётся из Git (полная версия с Windows).")
    else:
        print("На сервере: commit + push не нужен (генерация только на Windows)")
        print("Просто перезапустите службу: sudo systemctl restart modular-app")
else:
    print("")
    print("MARKER_END: синхронизация упала")