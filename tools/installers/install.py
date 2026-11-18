import os, re, json, base64, sys

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("ROOT: " + BASE)

# ---------------------------------------------------------------------
# 1. core/app.py: add rollback before PREDUPREZHDENIE prints.
#    This prevents one failed apply from poisoning SQLAlchemy session.
# ---------------------------------------------------------------------
cp = os.path.join(BASE, "core", "app.py")
if os.path.exists(cp):
    src = open(cp, encoding="utf-8").read()
    pat = re.compile(r'(except Exception as _e:\r?\n(\s*)print\("PREDUPREZHDENIE)')

    def repl(m):
        return (
            "except Exception as _e:\n"
            + m.group(2)
            + "db.session.rollback()\n"
            + m.group(2)
            + 'print("PREDUPREZHDENIE'
        )

    new, n = pat.subn(repl, src)
    if n:
        open(cp, "w", encoding="utf-8", newline="\n").write(new)
        print("PATCH core/app.py: rollback added = %d" % n)
    elif "db.session.rollback()" in src:
        print("SKIP core/app.py: rollback already present")
    else:
        print("WARN core/app.py: PREDUPREZHDENIE except pattern not found")
else:
    print("WARN core/app.py not found")

# ---------------------------------------------------------------------
# 2. history_seed.py: current version must follow newest semver release.
# ---------------------------------------------------------------------
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
if not os.path.exists(hp):
    print("FAIL history_seed.py not found")
    sys.exit(1)

htxt = open(hp, encoding="utf-8").read()

OLD_EXACT = """    if not Release.query.filter_by(is_current=True).first():
        top = Release.query.order_by(Release.id.desc()).first()
        if top:
            top.is_current = True
            try: db.session.commit()
            except Exception: db.session.rollback(); raise
    return added_r, added_c
"""

NEW_BLOCK = """    def _vk(v):
        parts = []
        for chunk in (v or "0").split("."):
            num = "".join(ch for ch in chunk if ch.isdigit())
            parts.append(int(num) if num else 0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])

    rows = Release.query.all()
    if rows:
        newest = max(rows, key=lambda r: (_vk(r.version), r.id))
        if not newest.is_current:
            Release.query.update({"is_current": False})
            newest.is_current = True
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
    return added_r, added_c
"""

if "_vk" in htxt:
    print("SKIP history_seed.py: newest-current logic already present")
elif OLD_EXACT in htxt:
    htxt = htxt.replace(OLD_EXACT, NEW_BLOCK, 1)
    print("PATCH history_seed.py: exact apply block replaced")
else:
    start = htxt.find("    if not Release.query.filter_by(is_current=True).first():")
    end = htxt.find("    return added_r, added_c", start)
    if start != -1 and end != -1:
        htxt = (
            htxt[:start]
            + NEW_BLOCK
            + htxt[end + len("    return added_r, added_c"):]
        )
        print("PATCH history_seed.py: apply block replaced by slice")
    else:
        print("WARN history_seed.py: apply block not found; will only try to add release")

# ---------------------------------------------------------------------
# 3. Add release 0.12.16 into base64 data without putting Cyrillic here.
#    Text is derived from existing 0.12.15 and appended with ASCII note.
# ---------------------------------------------------------------------
m = re.search(r'_B64\s*=\s*"([^"]*)"', htxt)
if not m:
    print("FAIL history_seed.py: _B64 block not found")
    sys.exit(1)

try:
    data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
except Exception as e:
    print("FAIL history_seed.py base64 decode: %s" % e)
    sys.exit(1)

if any(r.get("version") == "0.12.16" for r in data.get("releases", [])):
    print("SKIP history_seed.py: 0.12.16 already present")
else:
    base = None
    for r in data.get("releases", []):
        if r.get("version") == "0.12.15":
            base = r
            break

    if base is None and data.get("releases"):
        base = data["releases"][0]

    if base:
        newr = dict(base)
        newr["version"] = "0.12.16"
        newr["release_date"] = "2026-11-18"
        newr["status"] = "released"
        newr["title"] = (base.get("title") or "") + " + current pointer fix"
        newr["notes"] = (
            (base.get("notes") or "")
            + " Fix: current version is now always the newest release by version number,"
            + " not only when no current release exists."
        )
        data["releases"].insert(0, newr)

        author = "sync"
        if data.get("changelog"):
            author = data["changelog"][0].get("author") or author

        data["changelog"].insert(0, {
            "date": "2026-11-18",
            "author": author,
            "change_type": "fixed",
            "module": "versions",
            "ticket": "",
            "description": (
                "Current version pointer fixed: newest release by semantic version "
                "becomes current; fixes stuck current 0.12.9 after history rebuild."
            )
        })

        new_b64 = base64.b64encode(
            json.dumps(data, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")

        htxt = htxt[:m.start(1)] + new_b64 + htxt[m.end(1):]
        print("PATCH history_seed.py: added 0.12.16 (ASCII-safe, derived from 0.12.15)")
    else:
        print("WARN history_seed.py: no base release to derive 0.12.16")

open(hp, "w", encoding="utf-8", newline="\n").write(htxt)

# ---------------------------------------------------------------------
# 4. Apply to local DB. create_app() will run patched history_seed.apply().
# ---------------------------------------------------------------------
print("APPLY to local DB...")
sys.path.insert(0, BASE)

try:
    from core.app import create_app
    app = create_app()
    with app.app_context():
        from modules.versions.models import Release
        cur = Release.query.filter_by(is_current=True).first()
        cnt = Release.query.count()
        print("RELEASES IN DB: %d" % cnt)
        print("CURRENT NOW: v%s" % (cur.version if cur else "?"))
except Exception as e:
    print("FAIL apply: %s" % e)
    sys.exit(1)

print("=" * 60)
print("MARKER_END: ASCII installer finished; current should be 0.12.16")
print("=" * 60)
print("Commit + Push:")
print("  core/app.py")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")
print("VM today: do not touch; later git pull + ./update.sh")