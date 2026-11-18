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
# 1. core/app.py — rollback в except (чиняет каскад PendingRollback,
#    из-за которого релизы/журнал перестали доливатися).
# =========================================================================
cp = os.path.join(BASE, "core", "app.py")
src = open(cp, encoding="utf-8").read()
chg = False
for marker, fix in [
    ('print("PREDUPREZHDENIE: документация не применена: %s" % _e)',
     'db.session.rollback()\n            print("PREDUPREZHDENIE: документация не применена: %s" % _e, flush=True)'),
    ('print("PREDUPREZHDENIE: istoriya relizov ne primenena: %s" % _e)',
     'db.session.rollback()\n            print("PREDUPREZHDENIE: istoriya relizov ne primenena: %s" % _e, flush=True)'),
]:
    if marker in src and "db.session.rollback()" not in src.split(marker)[0][-200:]:
        src = src.replace(marker, fix, 1)
        chg = True
        print("  ~ core/app.py: rollback dobavlen pered '%s'" % marker[:40])
    else:
        print("  = core/app.py: rollback uzhe est ili yaкорь ne naiden: %s" % marker[:40])
if chg:
    open(cp, "w", encoding="utf-8", newline="\n").write(src)

# =========================================================================
# 2. dark.css — эталон + широкий контраст (pokryvaet ALL tekstovye tagi
#    vnutri main, krome accentov; chyto versii bez DevTools).
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
CONTRAST_WIDE = """
/* contrast-wide: perekrashivaem LYUBOY tekstovyy kontent vnutri main,
   krome accentov (bejdži/knopki/ssylki/zagolovki/kcifry statistiki).
   Pokryvaet time/dt/dd/em/i/strong/b/code vdobavok k div/p/span/small/li/td,
   chtoby pojmat' kartochki relizov bez DevTools. !important protiv inline. */
body.dark main a:not(.btn):not(.badge):not([class*="b-"]){color:#8ea2ff !important}
body.dark main a:not(.btn):not(.badge):not([class*="b-"]):hover{color:#b3c2ff !important}
body.dark main td:not(.badge):not(.btn):not([class*="b-"]),
body.dark main span:not(.badge):not(.btn):not([class*="b-"]):not(.uname),
body.dark main small,
body.dark main li,
body.dark main time,
body.dark main dt,
body.dark main dd,
body.dark main em,
body.dark main i,
body.dark main strong,
body.dark main b,
body.dark main code,
body.dark main div:not(.badge):not(.btn):not([class*="b-"]):not(.info):not(.flash):not(.form-row):not(.toolbar):not(.stats),
body.dark main p:not(.badge):not(.btn):not([class*="b-"]):not(.info):not(.flash):not(.form-row):not(.toolbar):not(.stats),
body.dark main .note,
body.dark main .empty { color:#c4ccd8 !important; }
body.dark main .card p { color:#e7eaf0 !important; }
body.dark footer { color:#9aa3b2 !important; }
"""
dp = os.path.join(BASE, "web", "static", "css", "dark.css")
if not os.path.exists(dp):
    dp = os.path.join(BASE, "static", "css", "dark.css")
open(dp, "w", encoding="utf-8", newline="\n").write(DARK_BASE + CONTRAST_WIDE)
print("  ~ dark.css: pere zapisan etalonon + contrast-wide (pokryvaet versii)")

# =========================================================================
# 3. history_seed.py (base64) — inkrementno dopisivaem propuschennye
#    relizy 0.12.10-0.12.14 + ih zhurnal. Esli dekoder upal (base64 povrezhden)
#    — govorim jasno i NE pishem, chtoby ne usugubit'.
# =========================================================================
MISSING_RELEASES = [
 {"version":"0.12.10","release_date":"2026-11-18","status":"released","title":"Контраст тёмной темы и подсветка текущего раздела","notes":"В тёмной теме второстепенный текст стал светлее и читается на тёмном фоне; ссылки в контенте получили акцентный цвет; текущий раздел меню подсвечивается в обеих темах. Светлая тема не изменена."},
 {"version":"0.12.11","release_date":"2026-11-18","status":"released","title":"Подсветка активного пункта меню для производства","notes":"Пункт «Производство» не выделялся, потому что его адрес в реестре редиректит на канонический, а подсветка сравнивала адреса только в одну сторону. Добавлена обратная проверка: текущий раздел подсвечивается и на производстве, и на вложенных страницах."},
 {"version":"0.12.12","release_date":"2026-11-18","status":"released","title":"Читаемый приглушённый текст в тёмной теме","notes":"Шаблоны хардкодили inline-цвет на описаниях ролей, названиях статей и подписях, из-за чего в тёмной теме текст был тёмным на тёмном. Прицельное переопределение через !important только для приглушённых тегов, с защитой акцентов."},
 {"version":"0.12.13","release_date":"2026-11-18","status":"released","title":"Контраст тёмной темы: ссылки и ячейки (в2)","notes":"Названия статей в Справке и описания ролей стали читаемыми: !important применён к ссылкам и td, перебивая inline-цвета шаблонов; заметки подняты из тёмно-серого."},
 {"version":"0.12.14","release_date":"2026-11-18","status":"released","title":"Контраст тёмной темы: карточки релизов (в3)","notes":"Дата, заголовок и описание в карточках релизов стали читаемыми: div/p перекрашены в цвет основного текста, цифры статистики защищены отдельным правилом, заголовки категорий не затронуты."},
]
MISSING_CHANGELOG = [
 {"date":"2026-11-18","change_type":"fixed","module":"web","description":"Тёмная тема: второстепенный текст и ссылки в контенте стали читаемыми; текущий раздел меню подсвечивается в обеих темах."},
 {"date":"2026-11-18","change_type":"fixed","module":"web","description":"Подсветка активного пункта меню починена для производства (обратное совпадение префикса URL)."},
 {"date":"2026-11-18","change_type":"fixed","module":"web","description":"Тёмная тема: приглушённый текст с inline-цветом переопределён на читаемый через !important, акценты защищены."},
 {"date":"2026-11-18","change_type":"fixed","module":"web","description":"Тёмная тема (в2): названия статей в Справке и описания ролей стали читаемыми (!important на ссылках и td)."},
 {"date":"2026-11-18","change_type":"fixed","module":"web","description":"Тёмная тема (в3): карточки релизов стали читаемыми (div/p перекрашены, цифры статистики защищены)."},
]
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
seed_ok = False
if not os.path.exists(hp):
    print("  ! history_seed.py ne naiden")
else:
    htxt = open(hp, encoding="utf-8").read()
    m = re.search(r'_B64\s*=\s*"([^"]*)"', htxt)
    if not m:
        print("  ! history_seed.py: net bloka _B64 (ne v base64?)")
    else:
        try:
            data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
            have_r = {r.get("version") for r in data["releases"]}
            add_r = 0
            for rec in MISSING_RELEASES:
                if rec["version"] not in have_r:
                    data["releases"].insert(0, rec); add_r += 1
            have_c = {(c.get("module"), c.get("description")) for c in data["changelog"]}
            A = "sineronizatsiya dokumentacii"
            add_c = 0
            for rec in MISSING_CHANGELOG:
                key = (rec["module"], rec["description"])
                if key not in have_c:
                    rec2 = dict(rec); rec2["author"] = A; rec2["ticket"] = ""
                    data["changelog"].insert(0, rec2); add_c += 1
            if add_r or add_c:
                new_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
                htxt = htxt[:m.start(1)] + new_b64 + htxt[m.end(1):]
                open(hp, "w", encoding="utf-8", newline="\n").write(htxt)
                print("  + history_seed.py: dopisano relizov = %d, zhurnala = %d" % (add_r, add_c))
            else:
                print("  = history_seed.py: 0.12.10-0.12.14 uzhe v file")
            seed_ok = True
        except Exception as e:
            print("  ! history_seed.py: base64 POVREZHDEN (dekoder upal: %s)" % e)
            print("     Skazhi 'peresoberi' — dayem polnyy peresbor faila s nulya.")

# =========================================================================
# 4. base.html — idempotentno dogonyaem podsvetku proizvodstva.
# =========================================================================
bp = os.path.join(BASE, "web", "templates", "base.html")
if not os.path.exists(bp):
    bp = os.path.join(BASE, "templates", "base.html")
bsrc = open(bp, encoding="utf-8").read()
if "hh.indexOf(path+'/')" in bsrc:
    print("  = base.html: podsvetka proizvodstva uzhe est")
else:
    SCRIPT = ("<script>\n/* menu-active */\n(function(){\n"
      "  var path=location.pathname.replace(/\\/+$/,'');var links=document.querySelectorAll('nav a');\n"
      "  for(var i=0;i<links.length;i++){var a=links[i];var href=(a.getAttribute('href')||'').split('?')[0].split('#')[0];\n"
      "    var hh=href.replace(/\\/+$/,'');var ok=false;\n"
      "    if(hh===''){ok=(path==='');}else if(path===hh){ok=true;}else if(path.indexOf(hh+'/')===0){ok=true;}\n"
      "    else if(path!==''&&hh.indexOf(path+'/')===0){ok=true;}\n"
      "    if(ok)a.classList.add('active');}\n})();\n</script>")
    if "</body>" in bsrc:
        bsrc = bsrc.replace("</body>", SCRIPT + "\n</body>", 1)
        open(bp, "w", encoding="utf-8", newline="\n").write(bsrc)
        print("  + base.html: podsvetka proizvodstva vstavlena")
    else:
        print("  ! base.html: net </body> — prišli base.html FAJLOM")

print("")
print("=" * 60)
print("MARKER_END: kaschad rollback + propuschennye relizy + kontrast versiy")
print("=" * 60)
print("Commit + Push:")
print("  core/app.py                        (rollback v except)")
print("  web/static/css/dark.css            (contrast-wide)")
print("  modules/versions/history_seed.py   (0.12.10-0.12.14)")
print("  web/templates/base.html            (podsvetka proizvodstva)")
print("  tools/installers/install.py")
print("")
print("VM SEGODNYA NE TROGAEM (net dostupa) — doeedet domoy cheres ./update.sh")