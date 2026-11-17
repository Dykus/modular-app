import os, re, json, base64, sys

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("Корень проекта: " + BASE)

DOCS_TEMPLATE = """# ЭТАЛОН СПРАВКИ И РУКОВОДСТВА — СТАТИЧЕСКИЙ КОД В GIT.
# Данные упакованы в base64, чтобы переводы строк и кавычки не ломали импорт.
import base64 as _b64
import json as _json
from datetime import datetime as _dt

_B64 = "{b64}"
_DATA = _json.loads(_b64.b64decode(_B64).decode("utf-8"))

def apply():
    from core.app import db
    try:
        from modules.help.models import HelpArticle, CATEGORIES
    except ImportError:
        from modules.help.models import HelpArticle
        CATEGORIES = []
    from modules.manual.models import ManualSection

    n_h = 0
    for rec in _DATA["help"]:
        cat = rec.get("category") or ""
        if CATEGORIES and cat not in CATEGORIES:
            cat = CATEGORIES[0]
        a = HelpArticle.query.filter_by(title=rec["title"]).first()
        if not a:
            a = HelpArticle(title=rec["title"], category=cat,
                            order=rec.get("order", 0), body=rec["body"],
                            edited_by="docs_seed")
            db.session.add(a)
        else:
            a.category = cat
            a.order = rec.get("order", a.order)
            a.body = rec["body"]
            a.edited_by = "docs_seed"
            a.updated_at = _dt.utcnow()
        n_h += 1
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    n_m = 0
    for rec in _DATA["manual"]:
        s = ManualSection.query.filter_by(code=rec["code"]).first()
        if not s:
            s = ManualSection(code=rec["code"],
                              title=rec.get("title") or rec["code"],
                              order=rec.get("order", 0), body=rec["body"],
                              updated_by="docs_seed")
            db.session.add(s)
        else:
            if rec.get("title"):
                s.title = rec["title"]
            if rec.get("order") is not None:
                s.order = rec["order"]
            s.body = rec["body"]
            s.updated_by = "docs_seed"
            s.updated_at = _dt.utcnow()
        n_m += 1
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return n_h, n_m
"""

HISTORY_TEMPLATE = """# ИСТОРИЯ ВЕРСИЙ И ЖУРНАЛА — СТАТИЧЕСКИЙ КОД В GIT.
# Данные упакованы в base64. apply() доливает только недостающее.
import base64 as _b64
import json as _json
from datetime import datetime as _dt

_B64 = "{b64}"
_DATA = _json.loads(_b64.b64decode(_B64).decode("utf-8"))

_DATE_KEYS = ("released_at", "release_date", "date", "created_at", "updated_at", "ts")

def _date(v):
    if not isinstance(v, str) or not v:
        return None
    try:
        return _dt.fromisoformat(v.replace(" ", "T"))
    except Exception:
        return None

def apply():
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
              for k, v in rec.items() if k in cols_r and k != "id"}
        kw.setdefault("is_current", False)
        db.session.add(Release(**kw))
        added_r += 1
    if added_r:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    have_c = {(c.module, c.description) for c in ChangelogEntry.query.all()}
    added_c = 0
    for rec in _DATA["changelog"]:
        if (rec.get("module"), rec.get("description")) in have_c:
            continue
        kw = {k: (_date(v) if k in _DATE_KEYS else v)
              for k, v in rec.items() if k in cols_c and k != "id"}
        db.session.add(ChangelogEntry(**kw))
        added_c += 1
    if added_c:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    if not Release.query.filter_by(is_current=True).first():
        top = Release.query.order_by(Release.id.desc()).first()
        if top:
            top.is_current = True
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

    return added_r, added_c
"""

def extract_inner_raw(path):
    txt = open(path, encoding="utf-8").read()
    m = re.search(r"_RAW = '''(.*?)'''\s*\r?\n\s*_DATA", txt, re.S)
    if not m:
        m = re.search(r"_RAW = '''(.*?)'''", txt, re.S)
    if not m:
        return None, txt
    return m.group(1), txt

def normalize_json(s):
    try:
        json.loads(s)
        return s
    except Exception:
        esc = []
        for ch in s:
            if ch == "\n":
                esc.append("\\n")
            elif ch == "\r":
                esc.append("\\r")
            elif ch == "\t":
                esc.append("\\t")
            elif ord(ch) < 32:
                esc.append("\\u%04x" % ord(ch))
            else:
                esc.append(ch)
        s2 = "".join(esc)
        json.loads(s2)
        return s2

def repair_file(rel_path, template, label):
    path = os.path.join(BASE, *rel_path.split("/"))
    if not os.path.exists(path):
        print("  ! %s: файл не найден" % label)
        return False

    inner, txt = extract_inner_raw(path)
    if inner is None:
        if "_B64 =" in txt:
            print("  = %s: уже в безопасной упаковке base64" % label)
            return True
        print("  ! %s: не найден старый блок _RAW" % label)
        return False

    try:
        inner = normalize_json(inner)
    except Exception as e:
        print("  ! %s: JSON внутри файла битый: %s" % (label, e))
        return False

    b64 = base64.b64encode(inner.encode("utf-8")).decode("ascii")
    content = template.replace("{b64}", b64)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("  + %s: переупакован в base64" % label)
    return True

ok1 = repair_file("modules/versions/docs_seed.py", DOCS_TEMPLATE, "docs_seed.py")
ok2 = repair_file("modules/versions/history_seed.py", HISTORY_TEMPLATE, "history_seed.py")

# Чтобы сообщения при старте службы были видны в journalctl
cp = os.path.join(BASE, "core", "app.py")
if os.path.exists(cp):
    src = open(cp, encoding="utf-8").read()
    pairs = [
        ('print("  ДОКУМЕНТАЦИЯ: статей справки %d, разделов руководства %d" % (_h, _m))',
         'print("  ДОКУМЕНТАЦИЯ: статей справки %d, разделов руководства %d" % (_h, _m), flush=True)'),
        ('print("PREDUPREZHDENIE: документация не применена: %s" % _e)',
         'print("PREDUPREZHDENIE: документация не применена: %s" % _e, flush=True)'),
        ('print("  ISTORIYA: dobavleno relizov %d, zapisey zhurnala %d" % (_r, _c))',
         'print("  ISTORIYA: dobavleno relizov %d, zapisey zhurnala %d" % (_r, _c), flush=True)'),
        ('print("PREDUPREZHDENIE: istoriya relizov ne primenena: %s" % _e)',
         'print("PREDUPREZHDENIE: istoriya relizov ne primenena: %s" % _e, flush=True)'),
    ]
    changed = False
    for old, new in pairs:
        if old in src and new not in src:
            src = src.replace(old, new, 1)
            changed = True
    if changed:
        with open(cp, "w", encoding="utf-8", newline="\n") as f:
            f.write(src)
        print("  ~ core/app.py: печать сообщений принудительно обновляется")
    else:
        print("  = core/app.py: печать уже в порядке или якоря не найдены")

print("")
print("=" * 60)
if ok1 and ok2:
    print("MARKER_END: справка и история переупакованы безопасно")
else:
    print("MARKER_END: есть проблемы, смотри строки выше")
print("=" * 60)
print("")
print("Дальше:")
print("1) GitHub Desktop: Commit to main -> Push origin")
print("2) На VM: git reset --hard HEAD && git pull && ./update.sh")