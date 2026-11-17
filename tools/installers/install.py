import os, subprocess, sys, sqlite3

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("Корень проекта: " + BASE)

# =========================================================================
# ФАЙЛ 1. tools/export_history.py — с исправленным списком дат
# Добавил "date" (колонка в changelog_entry) и разделил коммиты,
# чтобы autoflush не ломал всю сессию при ошибке в журнале.
# =========================================================================
os.makedirs(os.path.join(BASE, "tools"), exist_ok=True)
EXPORT = '''"""Генерирует modules/versions/history_seed.py из локальной базы.
ВАЖНО: запускать ТОЛЬКО на разработочной машине (Windows), где полная база.
На сервере (Linux) НЕ запускать — там база неполная, история обрежется.
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

# Все возможные имена колонок с датами во всех таблицах проекта.
# Если новое поле-дата появится в модели — добавить сюда, иначе будет TypeError.
_DATE_KEYS = ("released_at", "release_date", "date", "created_at", "updated_at", "ts")


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

    # РЕЛИЗЫ: отдельная транзакция, чтобы autoflush журнала её не сломал.
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
    if added_r:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    # ЖУРНАЛ: отдельная транзакция.
    have_c = {(c.module, c.description) for c in ChangelogEntry.query.all()}
    added_c = 0
    for rec in _DATA["changelog"]:
        if (rec.get("module"), rec.get("description")) in have_c:
            continue
        kw = {k: (_date(v) if k in _DATE_KEYS else v)
              for k, v in rec.items() if k in cols_c and k not in ("id",)}
        db.session.add(ChangelogEntry(**kw))
        added_c += 1
    if added_c:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    # Гарантируем, что текущий релиз помечен.
    if not Release.query.filter_by(is_current=True).first():
        top = Release.query.order_by(Release.id.desc()).first()
        if top:
            top.is_current = True
            db.session.commit()

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
print("  + tools/export_history.py (добавлено 'date' в _DATE_KEYS, разделены транзакции)")

# =========================================================================
# Шаг 2. Определить платформу и действовать соответственно
# =========================================================================
is_windows = sys.platform.startswith("win")
if is_windows:
    print("  среда: Windows (разработочная машина)")
    print("  перегенерирую history_seed.py из полной базы...")
    sys.path.insert(0, os.path.join(BASE, "tools"))
    # Перезагружаем модуль, если он уже импортировался в предыдущих запусках
    import importlib
    import export_history as EH
    importlib.reload(EH)
    hs = os.path.join(BASE, "modules", "versions", "history_seed.py")
    if os.path.exists(hs):
        os.remove(hs)
        print("  - history_seed.py (старая версия удалена)")
    if not EH.generate():
        print("MARKER_END: ГЕНЕРАЦИЯ НЕ УДАЛАСЬ")
        sys.exit(1)
    dbp = os.path.join(BASE, "data", "database.db")
    con = sqlite3.connect(dbp)
    count_r = con.execute("SELECT COUNT(*) FROM release").fetchone()[0]
    count_c = con.execute("SELECT COUNT(*) FROM changelog_entry").fetchone()[0]
    con.close()
    print(f"  В Windows-базе: {count_r} релизов, {count_c} записей журнала")
else:
    print("  среда: Linux (сервер)")
    print("  НЕ генерирую history_seed.py — использую версию из Git")
    hs = os.path.join(BASE, "modules", "versions", "history_seed.py")
    if os.path.exists(hs):
        print("  history_seed.py уже есть в Git")
    else:
        print("  ПРЕДУПРЕЖДЕНИЕ: history_seed.py отсутствует!")

# =========================================================================
# ФАЙЛ 3. sync_125.py — документация (0.12.5)
# =========================================================================
SYNC = '''"""Синхронизация документации: исправление истории версий (0.12.5)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime
from core.app import create_app, db

CHANGELOG_BATCH = [
("fixed", "versions", "История версий наконец применяется полностью: колонка «date» в таблице changelog_entry добавлена в список дат, транзакции разделены (релизы и журнал коммитятся отдельно) — autoflush больше не ломает сессию. Сервер получает все релизы 0.6.0–0.12.4 и полный журнал изменений."),
]

def sync():
    from modules.changelog.models import ChangelogEntry
    from modules.versions.models import Release
    from modules.settings.models import Setting

    marker = db.session.get(Setting, "docs_sync_v125")
    if marker is None or marker.value != "1":
        for typ, mod, desc in CHANGELOG_BATCH:
            db.session.add(ChangelogEntry(author="синхронизация документации",
                                          change_type=typ, module=mod, description=desc))
        db.session.add(Setting(key="docs_sync_v125", value="1"))
        db.session.commit()
        print("  changelog: записей добавлено = %d" % len(CHANGELOG_BATCH))
    else:
        print("  changelog: партия 0.12.5 уже была, пропуск")

    if not Release.query.filter_by(version="0.12.5").first():
        Release.query.update({"is_current": False})
        db.session.add(Release(version="0.12.5",
            title="Полная история версий на сервере",
            notes="История релизов и журнала изменений наконец применяется полностью на сервере. Исправлены две ошибки: колонка «date» в таблице changelog_entry добавлена в список дат; транзакции релизов и журнала разделены — autoflush больше не ломает сессию. Все релизы от 0.6.0 до 0.12.4 и полный журнал теперь видны.",
            status="released", is_current=True))
        db.session.commit()
        print("  versions: релиз 0.12.5 создан и помечен текущим")
    else:
        print("  versions: релиз 0.12.5 уже есть")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        sync()
    print("Синхронизация 0.12.5 завершена.")
'''
with open(os.path.join(BASE, "sync_125.py"), "w", encoding="utf-8", newline="\n") as f:
    f.write(SYNC)
print("  + sync_125.py")

# =========================================================================
# Шаг 3. Применить синхронизацию к локальной базе (на Windows это нужно,
# на сервере уже есть в истории из Git)
# =========================================================================
print("")
print("Применяю синхронизацию к локальной базе...")
print("-" * 50)
proc = subprocess.run([sys.executable, os.path.join(BASE, "sync_125.py")], cwd=BASE)
print("-" * 50)

if proc.returncode == 0:
    print("")
    print("=" * 56)
    print("MARKER_END: полная история версий 0.12.5")
    print("=" * 56)
    if is_windows:
        print("Commit + Push:")
        print("  modules/versions/history_seed.py")
        print("  sync_125.py")
        print("  tools/export_history.py")
        print("  tools/installers/install.py")
        print("")
        print("Затем на VM: git pull && ./update.sh")
        print("Сервер получит ВСЕ релизы 0.6.0–0.12.5 и полный журнал.")
    else:
        print("На сервере: просто перезапустите службу:")
        print("  sudo systemctl restart modular-app")
else:
    print("")
    print("MARKER_END: синхронизация упала")