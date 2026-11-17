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
# ФАЙЛ 1. tools/export_history.py — generator istorii (ispravlen)
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

_DATE_KEYS = ("released_at", "release_date", "created_at", "updated_at", "ts")


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
print("  + tools/export_history.py (ispravlen)")

# =========================================================================
# Shag 2. PEREGENERIROVAT' history_seed.py (staraya versiya slomana)
# =========================================================================
sys.path.insert(0, os.path.join(BASE, "tools"))
import export_history as EH

hs = os.path.join(BASE, "modules", "versions", "history_seed.py")
if os.path.exists(hs):
    os.remove(hs)
    print("  - history_seed.py (staraya versiya)")
print("Generiruyu istoriyu iz lokalnoy bazy...")
if not EH.generate():
    print("MARKER_END: GENERACIYA NE UDALAS'")
    sys.exit(1)

# =========================================================================
# Shag 3. Udalit' testovyy modul test_update i metku [TEST-UPDATE]
# =========================================================================
test_mod = os.path.join(BASE, "modules", "test_update")
if os.path.exists(test_mod):
    import shutil
    shutil.rmtree(test_mod)
    print("  - modules/test_update/ (udalyon)")

p = os.path.join(BASE, "web", "templates", "base.html")
if os.path.exists(p):
    src = open(p, encoding="utf-8").read()
    if "[TEST-UPDATE]" in src:
        src = src.replace("<title>[TEST-UPDATE] ", "<title>")
        open(p, "w", encoding="utf-8", newline="\n").write(src)
        print("  ~ web/templates/base.html: metka [TEST-UPDATE] ubrana")

p = os.path.join(BASE, "core", "app.py")
if os.path.exists(p):
    src = open(p, encoding="utf-8").read()
    if "test_update_bp" in src:
        src = src.replace("\n    from modules.test_update.routes import test_update_bp\n    app.register_blueprint(test_update_bp)", "")
        open(p, "w", encoding="utf-8", newline="\n").write(src)
        print("  ~ core/app.py: registraciya test_update ubrana")

# =========================================================================
# Shag 4. sync_122.py — dokumentaciya po reglamentu (0.12.2)
# =========================================================================
SYNC = '''"""Sinhronizaciya dokumentacii: istoriya versiy + ochistka testa (0.12.2)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime
from core.app import create_app, db

CHANGELOG_BATCH = [
("added", "versions", "Polnaya istoriya relizov i zhurnala izmeneniy stala chast'yu koda: fayl modules/versions/history_seed.py generiruetsya iz lokalnoy bazy i primenyaetsya pri kazhdom starte prilozheniya. Lyubaya novaya mashina (VM, malina) s pervogo zapuska poluchaet polnuyu i odinakovyuyu istoriyu."),
("added", "tools", "Skript tools/export_history.py dlya regeneracii history_seed.py posle kazhdogo novogo reliza."),
("fixed", "versions", "Avtomaticheskoe primenenie istorii: obrabotka dat (release_date) i otkat sessii pri oshibkah."),
("removed", "test_update", "Testovyy modul' dlya proverki obnovleniya udalen posle uspeshnogo testa."),
("changed", "web", "Testovaya metka [TEST-UPDATE] ubrana iz zagolovkov stranic."),
]

def sync():
    from modules.changelog.models import ChangelogEntry
    from modules.versions.models import Release
    from modules.settings.models import Setting

    marker = db.session.get(Setting, "docs_sync_v122")
    if marker is None or marker.value != "1":
        for typ, mod, desc in CHANGELOG_BATCH:
            db.session.add(ChangelogEntry(author="sinxronizaciya dokumentacii",
                                          change_type=typ, module=mod, description=desc))
        db.session.add(Setting(key="docs_sync_v122", value="1"))
        db.session.commit()
        print("  changelog: zapisey dobavleno = %d" % len(CHANGELOG_BATCH))
    else:
        print("  changelog: partiya 0.12.2 uzhe byla, propusk")

    if not Release.query.filter_by(version="0.12.2").first():
        Release.query.update({"is_current": False})
        db.session.add(Release(version="0.12.2",
            title="Polnaya istoriya versiy",
            notes="Istoriya relizov i zhurnala izmeneniy stala chast'yu koda: generiruetsya iz lokal'noy bazy i avtomaticheski primenyaetsya pri kazhdom starte. Lyubaya novaya ustanovka (VM, malina) poluchaet polnuyu i odinakovyuyu istoriyu s pervogo zapuska.",
            status="released", is_current=True))
        db.session.commit()
        print("  versions: releiz 0.12.2 sozdan i pomachen tekushchim")
    else:
        print("  versions: releiz 0.12.2 uzhe est")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        sync()
    print("Sinxronizaciya 0.12.2 zavershena.")
'''
with open(os.path.join(BASE, "sync_122.py"), "w", encoding="utf-8", newline="\n") as f:
    f.write(SYNC)
print("  + sync_122.py")

# =========================================================================
# Shag 5. Primenit' istoriyu i sinhronizaciyu k etoy baze
# =========================================================================
print("")
print("Primenyayu istoriyu i sinhronizaciyu k lokal'noy baze...")
print("-" * 50)
subprocess.run([sys.executable, os.path.join(BASE, "sync_122.py")], cwd=BASE)
print("-" * 50)
print("")
print("=" * 56)
print("MARKER_END: istoriya ispravlena, test ochishchen, docs 0.12.2")
print("=" * 56)
print("Commit + Push: modules/versions/history_seed.py,")
print("               tools/export_history.py, sync_122.py,")
print("               web/templates/base.html, core/app.py,")
print("               tools/installers/install.py")
print("(-modules/test_update/ - udalen)")
print("")
print("Zatem na VM: ./update.sh")