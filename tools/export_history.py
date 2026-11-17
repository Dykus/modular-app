"""Генерирует modules/versions/history_seed.py из локальной базы.
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

_RAW = '''{raw}'''
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
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print("  history_seed.py: релизов = %d, записей журнала = %d" % (len(rels), len(chs)))
    return True


if __name__ == "__main__":
    generate()
