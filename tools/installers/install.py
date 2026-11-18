import os, re, json, base64, sys

d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d:
        break
    d = p
BASE = d
print("Koren' proekta: " + BASE)

# =========================================================================
# ЭТАЛОН dark.css (чистый, из Git) + contrast-dark-fix v2.
# Перезаписываем whole-file, чтобы убрать мусор прошлых попыток.
# =========================================================================
DARK_BASE = """/* Temnaya tema - primenyaetsya k body.dark */
body.dark { background:#15171c; color:#d7dae0; }
body.dark main { background:#1e2128; box-shadow:0 2px 6px rgba(0,0,0,.4); }
body.dark header { background:linear-gradient(135deg,#3b4270,#4a2f63); }
body.dark .welcome h2 { color:#8ea2ff; }
body.dark .welcome p, body.dark .card h3 { color:#9aa3b2; }
body.dark .card { background:#23262e; border-left-color:#8ea2ff; box-shadow:0 2px 4px rgba(0,0,0,.3); }
body.dark .card p { color:#e7eaf0; }
body.dark th { background:#23262e; color:#9aa3b2; border-bottom-color:#333844; }
body.dark td { border-bottom-color:#2a2e37; }
body.dark tr:hover td { background:#262a33; }
body.dark .form-row { background:#23262e; border-color:#3a3f4b; }
body.dark .form-row input, body.dark .form-row select,
body.dark .toolbar input[type=text] { background:#1a1d24; border-color:#3a3f4b; color:#e7eaf0; }
body.dark .btn.gray { background:#3a3f4b; } body.dark .btn.gray:hover { background:#4a5060; }
body.dark .info { background:#1c2733; border-left-color:#3b82f6; }
body.dark .info h3 { color:#60a5fa; }
body.dark .flash { background:#3a2f12; border-left-color:#f39c12; color:#ffd97a; }
body.dark .empty { color:#6b7280; }
body.dark .note { color:#6b7280; }
body.dark footer { color:#6b7280; }
body.dark .theme-btn { background:rgba(255,255,255,.12); color:#fff; }
.theme-btn { background:rgba(255,255,255,.2); color:#fff; border:none; border-radius:6px;
padding:6px 10px; cursor:pointer; font-size:16px; vertical-align:middle; margin-left:6px; }
.theme-btn:hover { background:rgba(255,255,255,.32); }
"""

CONTRAST_FIX = """
/* contrast-dark-fix v2: perebivaem inline-cveta šablonov (#2c3e50 na ssylkah
   spravki, #5a6b85 na yacheykah roley) i tёmnye klassy (#6b7280 note/empty/
   footer), kotorye v tёmnoy teme ostayutsya tёmnymi na tёmnom. !important
   obyazaten protiv inline. Accenty NE trogaem: zagolovki h1-h4 (sirenevye
   kategorii), cifry statistiki (.card p), bejdži/knopki/infо/flash zashisheny
   cherez :not. p/div v spisok NE vklюčeny, čtoby ne poblekli cifry i kategorii. */
body.dark main a:not(.btn):not(.badge):not([class*="b-"]) { color:#8ea2ff !important; }
body.dark main a:not(.btn):not(.badge):not([class*="b-"]):hover { color:#b3c2ff !important; }
body.dark main td:not(.badge):not(.btn):not([class*="b-"]),
body.dark main span:not(.badge):not(.btn):not([class*="b-"]):not(.uname),
body.dark main small,
body.dark main li,
body.dark main .note,
body.dark main .empty { color:#c4ccd8 !important; }
body.dark footer { color:#9aa3b2 !important; }
"""

dp = os.path.join(BASE, "web", "static", "css", "dark.css")
if not os.path.exists(dp):
    dp = os.path.join(BASE, "static", "css", "dark.css")
open(dp, "w", encoding="utf-8", newline="\n").write(DARK_BASE + CONTRAST_FIX)
print("  ~ dark.css: pere zapisan čistym etalonon + contrast-dark-fix v2")

# =========================================================================
# reliz 0.12.13 v history_seed.py (base64).
# =========================================================================
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
if not os.path.exists(hp):
    print("  ! history_seed.py ne naiden")
else:
    htxt = open(hp, encoding="utf-8").read()
    m = re.search(r'_B64\s*=\s*"([^"]*)"', htxt)
    if not m:
        print("  ! history_seed.py: net bloka _B64")
    else:
        data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
        if any(r.get("version") == "0.12.13" for r in data["releases"]):
            print("  = history_seed.py: 0.12.13 uzhe est")
        else:
            data["releases"].insert(0, {
                "version": "0.12.13", "release_date": "2026-11-18", "status": "released",
                "title": "Контраст тёмной темы: ссылки и ячейки (в2)",
                "notes": "Прошлый фикс контраста не сработал для названий статей в Справке, потому что шаблоны хардкодят inline-стиль color:#2c3e50 на ссылках, а правило без !important inline не перебивает. Теперь !important применён точечно: к ссылкам (стали акцентными), к ячейкам td (описания ролей), к классам .note/.empty/footer (заметки в Версиях). При этом p и div из перекраски исключены, чтобы не поблекли цифры статистики (.card p) и сиреневые заголовки категорий. dark.css перезаписан чистым эталоном, мусор прошлых попыток удалён."})
            A = "sineronizatsiya dokumentacii"
            data["changelog"].insert(0, {"date": "2026-11-18", "author": A, "change_type": "fixed", "module": "web", "ticket": "", "description": "Тёмная тема (в2): названия статей в Справке и описания ролей стали читаемыми — !important применён к ссылкам и td, перебивая inline-цвета шаблонов (#2c3e50/#5a6b85); заметки .note/.empty/footer подняты из #6b7280; p/div не тронуты, чтобы сохранить цифры статистики и сиреневые заголовки категорий."})
            new_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
            htxt = htxt[:m.start(1)] + new_b64 + htxt[m.end(1):]
            open(hp, "w", encoding="utf-8", newline="\n").write(htxt)
            print("  + history_seed.py: reliz 0.12.13 (base64 peresobran)")

print("")
print("=" * 60)
print("MARKER_END: kontrast tёмnoy temy v2 (0.12.13)")
print("=" * 60)