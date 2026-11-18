import os, re, json, base64, sys

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("ROOT: " + BASE)

AUTHOR_RU = "\u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u0438"
BAD_AUTHORS = ["sync", "sineronizatsiya dokumentacii",
               "\u0441\u0438\u043d\u0445\u0440\u043e\u043dizatsiya dokumentacii"]

# ---------------------------------------------------------------------
# 1. modules/changelog/routes.py: secondary sort by id inside same date.
# ---------------------------------------------------------------------
rp = os.path.join(BASE, "modules", "changelog", "routes.py")
if not os.path.exists(rp):
    print("WARN changelog/routes.py not found")
else:
    src = open(rp, encoding="utf-8").read()
    if "ChangelogEntry.id.desc()" in src:
        print("SKIP changelog/routes.py: id sort already present")
    else:
        new, n1 = re.subn(r"order_by\(\s*ChangelogEntry\.date\.desc\(\)\s*\)",
                          "order_by(ChangelogEntry.date.desc(), ChangelogEntry.id.desc())", src)
        new, n2 = re.subn(r"order_by\(\s*desc\(ChangelogEntry\.date\)\s*\)",
                          "order_by(ChangelogEntry.date.desc(), ChangelogEntry.id.desc())", new)
        if n1 + n2:
            open(rp, "w", encoding="utf-8", newline="\n").write(new)
            print("PATCH changelog/routes.py: order_by date+id = %d" % (n1 + n2))
        else:
            print("WARN changelog/routes.py: order_by anchor not found; lines below:")
            for ln in src.splitlines():
                if "order_by" in ln:
                    print("   | " + ln.strip())

# ---------------------------------------------------------------------
# 2. history_seed.py: normalize authors in base64 + add release 0.12.17.
# ---------------------------------------------------------------------
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
htxt = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', htxt)
if not m:
    print("FAIL history_seed.py: no _B64")
    sys.exit(1)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))

fixed_auth = 0
for c in data.get("changelog", []):
    if c.get("author") in BAD_AUTHORS:
        c["author"] = AUTHOR_RU
        fixed_auth += 1

TITLE17 = ("\u0416\u0443\u0440\u043d\u0430\u043b \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0439: "
           "\u0441\u0432\u0435\u0436\u0438\u0435 \u0437\u0430\u043f\u0438\u0441\u0438 \u0441\u0432\u0435\u0440\u0445\u0443")
NOTES17 = ("\u041b\u0435\u043d\u0442\u0430 \u0436\u0443\u0440\u043d\u0430\u043b\u0430: "
           "\u0432\u043d\u0443\u0442\u0440\u0438 \u043e\u0434\u043d\u043e\u0439 \u0434\u0430\u0442\u044b "
           "\u0441\u0432\u0435\u0436\u0438\u0435 \u0437\u0430\u043f\u0438\u0441\u0438 \u0441\u0432\u0435\u0440\u0445\u0443. "
           "\u0410\u0432\u0442\u043e\u0440 \u0441\u043b\u0443\u0436\u0435\u0431\u043d\u044b\u0445 \u0437\u0430\u043f\u0438\u0441\u0435\u0439 "
           "\u043f\u0440\u0438\u0432\u0435\u0434\u0451\u043d \u043a \u0435\u0434\u0438\u043d\u043e\u043c\u0443 \u0432\u0438\u0434\u0443.")
DESC17 = ("\u0416\u0443\u0440\u043d\u0430\u043b \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0439: "
          "\u0441\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u043a\u0430 \u043f\u043e \u0434\u0430\u0442\u0435 \u0438 id \u2014 "
          "\u0441\u0432\u0435\u0436\u0438\u0435 \u0437\u0430\u043f\u0438\u0441\u0438 \u0441\u0432\u0435\u0440\u0445\u0443 "
          "\u0434\u0430\u0436\u0435 \u043f\u0440\u0438 \u043e\u0434\u0438\u043d\u0430\u043a\u043e\u0432\u043e\u0439 \u0434\u0430\u0442\u0435.")

if any(r.get("version") == "0.12.17" for r in data.get("releases", [])):
    print("SKIP history_seed.py: 0.12.17 already present")
else:
    data["releases"].insert(0, {"version": "0.12.17", "release_date": "2026-11-18",
                                "status": "released", "title": TITLE17, "notes": NOTES17})
    data["changelog"].insert(0, {"date": "2026-11-18", "author": AUTHOR_RU,
                                 "change_type": "fixed", "module": "changelog",
                                 "ticket": "", "description": DESC17})
    print("PATCH history_seed.py: release 0.12.17 added; authors normalized = %d" % fixed_auth)

new_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
htxt = htxt[:m.start(1)] + new_b64 + htxt[m.end(1):]
open(hp, "w", encoding="utf-8", newline="\n").write(htxt)

# ---------------------------------------------------------------------
# 3. Apply to local DB: normalize authors there too, then let apply() run.
# ---------------------------------------------------------------------
sys.path.insert(0, BASE)
from core.app import create_app, db
app = create_app()
with app.app_context():
    from modules.changelog.models import ChangelogEntry
    rows = ChangelogEntry.query.filter(ChangelogEntry.author.in_(BAD_AUTHORS)).all()
    for r in rows:
        r.author = AUTHOR_RU
    if rows:
        db.session.commit()
    print("DB authors normalized = %d" % len(rows))
    from modules.versions.models import Release
    cur = Release.query.filter_by(is_current=True).first()
    print("CURRENT NOW: v%s" % (cur.version if cur else "?"))

print("=" * 60)
print("MARKER_END: changelog sort + author cleanup (0.12.17)")
print("=" * 60)
print("Commit + Push:")
print("  modules/changelog/routes.py")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")