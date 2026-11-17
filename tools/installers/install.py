import os, subprocess, sys

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("Koren' proekta: " + BASE)

# =========================================================================
# ФАЙЛ 1. tools/export_history.py — generator istorii iz lokalnoy bazy.
# (Vnutri shablona bol'she net vlozhennyh troynyh kavychek - tolko kommentarii.)
# =========================================================================
os.makedirs(os.path.join(BASE, "tools"), exist_ok=True)
EXPORT = '''"""Generiruet modules/versions/history_seed.py iz lokalnoy bazy.
Zapuskat' na razrabotochnoy mashine (Windows) posle kazhdogo novogo releiza,
zatem kommitit', chtoby istoriya uezzhala na servery cherez Git."""
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

TEMPLATE = """# AVTOGENERACIYA: polnaya istoriya relizov i zhurnala izmeneniy.
# VRUCHNUYU NE PRAVIT'. Regeneraciya: python tools/export_history.py
import json as _json
from datetime import datetime as _dt

_RAW = \'\'\'{raw}\'\'\'
_DATA = _json.loads(_RAW)

_DATE_KEYS = ("released_at", "created_at", "updated_at", "ts")


def _date(v):
    if not isinstance(v, str) or not v:
        return None
    try:
        return _dt.fromisoformat(v.replace(" ", "T"))
    except Exception:
        return None


def apply():
    # Dobavlyaet v bazu tolko NEDOSTAYUSHCHIE relizy i zapisi zhurnala.
    # Nichego suschestvuyushchego ne perezapisyvaet.
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
        print("NET bazy: " + dbp)
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
    print("  history_seed.py: relizov = %d, zapisey zhurnala = %d" % (len(rels), len(chs)))
    return True


if __name__ == "__main__":
    generate()
'''
with open(os.path.join(BASE, "tools", "export_history.py"), "w", encoding="utf-8", newline="\n") as f:
    f.write(EXPORT)
print("  + tools/export_history.py (perezapisan ispravno)")

# =========================================================================
# Shag 2. Sgenerirovat' history_seed.py iz etoy (Windows) bazy, esli ego net
# =========================================================================
sys.path.insert(0, os.path.join(BASE, "tools"))
import export_history as EH

hs = os.path.join(BASE, "modules", "versions", "history_seed.py")
if not os.path.exists(hs):
    print("Generiruyu istoriyu iz lokalnoy bazy...")
    if not EH.generate():
        print("MARKER_END: GENERACIYA NE UDALAS'")
        input("Enter...")
        sys.exit(1)
else:
    print("  = history_seed.py uzhe est, ne regeneriruyu")

# =========================================================================
# Shag 3. Patch core/app.py: primenyat' istoriyu pri kazhdom starte
# =========================================================================
p = os.path.join(BASE, "core", "app.py")
src = open(p, encoding="utf-8").read()
if "history_seed" not in src:
    old = "        run_seed()\n"
    new = old + (
        "        try:\n"
        "            from modules.versions import history_seed as _hs\n"
        "            _r, _c = _hs.apply()\n"
        "            if _r or _c:\n"
        "                print(\"  ISTORIYA: dobavleno relizov %d, zapisey zhurnala %d\" % (_r, _c))\n"
        "        except Exception as _e:\n"
        "            print(\"PREDUPREZHDENIE: istoriya relizov ne primenena: %s\" % _e)\n"
    )
    if old in src:
        src = src.replace(old, new, 1)
        open(p, "w", encoding="utf-8", newline="\n").write(src)
        print("  ~ core/app.py: istoriya primenyaetsya pri kazhdom starte")
    else:
        print("  ! core/app.py: yakor 'run_seed()' ne naiden, soobshchi mne")
else:
    print("  = core/app.py: patch istorii uzhe stoit")

# =========================================================================
# Shag 4. Primenit' istoriyu k etoy baze srazu
# =========================================================================
print("")
print("Primenyayu istoriyu k lokalnoy baze...")
print("-" * 50)
proc = subprocess.run([sys.executable, "-c",
                       "import sys; sys.path.insert(0,'.'); from core.app import create_app; create_app()"],
                      cwd=BASE)
print("-" * 50)
print("")
print("=" * 56)
print("MARKER_END: istoriya versiy stala chast'yu koda")
print("=" * 56)
print("V GitHub Desktop teper' dolzhno byt' 4 faila:")
print("  core/app.py, modules/versions/history_seed.py,")
print("  tools/export_history.py, tools/installers/install.py")
input("Najmi Enter, aby zakryt okno...")