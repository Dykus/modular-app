# ASCII-only diagnostic. Reads seed vs DB, retries apply(), writes report.
import os, re, json, base64, sys, traceback

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
REPORT = os.path.join(BASE, "_diag_changelog.txt")

def w(f, s):
    f.write(s + "\n")

# ---- load seed (base64) ----
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
htxt = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', htxt)
if not m:
    print("FAIL: no _B64 block in history_seed.py")
    sys.exit(1)
seed = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
seed_rel = [r.get("version") for r in seed.get("releases", [])]
seed_cl = seed.get("changelog", [])
seed_cl_keys = set((c.get("module"), c.get("description")) for c in seed_cl)
seed_cl_1811 = [c for c in seed_cl if c.get("date", "").startswith("2026-11-18")]

# ---- open app + DB ----
sys.path.insert(0, BASE)
from core.app import create_app, db
app = create_app()
with app.app_context():
    from modules.versions.models import Release
    from modules.changelog.models import ChangelogEntry

    db_rel = [r.version for r in Release.query.all()]
    db_cl_rows = ChangelogEntry.query.all()
    db_cl_keys = set((c.module, c.description) for c in db_cl_rows)
    db_cl_1811 = [c for c in db_cl_rows
                  if c.date and str(c.date).startswith("2026-11-18")]

    miss_rel = [v for v in seed_rel if v not in set(db_rel)]
    miss_cl  = [k for k in seed_cl_keys if k not in db_cl_keys]

    # retry apply() to catch the real exception
    retry_note = ""
    try:
        from modules.versions import history_seed as hs
        r, c = hs.apply()
        retry_note = "RETRY apply ok: added_r=%d added_c=%d" % (r, c)
    except Exception as e:
        retry_note = "RETRY apply EXCEPTION type=%s" % type(e).__name__
        err_full = "%s\n%s" % (e, traceback.format_exc())

    # ---- console: ASCII summary only ----
    print("SEED releases: %d | DB releases: %d | missing in DB: %s"
          % (len(seed_rel), len(db_rel), ",".join(miss_rel) or "none"))
    print("SEED changelog: %d | DB changelog: %d | missing in DB: %d"
          % (len(seed_cl), len(db_cl_rows), len(miss_cl)))
    print("SEED 18.11 cl: %d | DB 18.11 cl: %d"
          % (len(seed_cl_1811), len(db_cl_1811)))
    print(retry_note)

    # ---- report file: full detail (cyrillic ok here) ----
    with open(REPORT, "w", encoding="utf-8") as f:
        w(f, "=== DIAG CHANGELOG ===")
        w(f, "SEED releases (%d): %s" % (len(seed_rel), ", ".join(seed_rel)))
        w(f, "DB releases (%d): %s" % (len(db_rel), ", ".join(sorted(db_rel))))
        w(f, "missing releases in DB: %s" % (", ".join(miss_rel) or "none"))
        w(f, "")
        w(f, "SEED changelog total: %d" % len(seed_cl))
        w(f, "DB changelog total: %d" % len(db_cl_rows))
        w(f, "missing changelog in DB: %d" % len(miss_cl))
        w(f, "")
        w(f, "--- SEED changelog dated 2026-11-18 (%d) ---" % len(seed_cl_1811))
        for c in seed_cl_1811:
            w(f, "[%s|%s] %s" % (c.get("change_type"), c.get("module"),
                                 (c.get("description") or "")[:120]))
        w(f, "")
        w(f, "--- DB changelog dated 2026-11-18 (%d) ---" % len(db_cl_1811))
        for c in db_cl_1811:
            w(f, "[%s|%s] %s" % (c.change_type, c.module,
                                 (c.description or "")[:120]))
        w(f, "")
        w(f, "--- missing in DB (seed minus db), first 40 ---")
        for (mod, desc) in list(miss_cl)[:40]:
            w(f, "[%s] %s" % (mod, (desc or "")[:120]))
        w(f, "")
        w(f, "RETRY: %s" % retry_note)
        if "err_full" in dir():
            w(f, "EXCEPTION DETAIL:\n%s" % err_full)

print("REPORT written: " + REPORT)