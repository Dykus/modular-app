"""Генерирует modules/versions/history_seed.py из локальной базы.
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

_RAW = '''{raw}'''
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
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print("  history_seed.py: релизов = %d, записей журнала = %d" % (len(rels), len(chs)))
    return True


if __name__ == "__main__":
    generate()
