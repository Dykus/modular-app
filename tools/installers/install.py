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
# ПРАВКА 1. dark.css — второстепенный текст должен быть СВЕТЛЕЕ на тёмном,
# а не темнее. Поднимаем #6b7280 -> #9aa3b2 для .empty / .note / footer.
# =========================================================================
dp = os.path.join(BASE, "web", "static", "css", "dark.css")
if not os.path.exists(dp):
    dp = os.path.join(BASE, "static", "css", "dark.css")  # запасной путь
src = open(dp, encoding="utf-8").read()
pairs = [
    ("body.dark .empty { color:#6b7280; }", "body.dark .empty { color:#9aa3b2; }"),
    ("body.dark .note { color:#6b7280; }",  "body.dark .note { color:#9aa3b2; }"),
    ("body.dark footer { color:#6b7280; }", "body.dark footer { color:#9aa3b2; }"),
]
chg = False
for old, new in pairs:
    if old in src:
        src = src.replace(old, new, 1); chg = True
        print("  ~ dark.css: %s -> светлее" % old.split('{')[0].strip())
    elif new in src:
        print("  = dark.css: %s уже починен" % new.split('{')[0].strip())
    else:
        print("  ! dark.css: якорь не найден: %s" % old)
# Ссылки в контенте (покрывает неизвестные классы help/list): акцент вместо тёмного.
LINK_BLOCK = ("\nbody.dark main a:not(.btn){color:#8ea2ff}\n"
              "body.dark main a:not(.btn):hover{color:#b3c2ff}\n")
if "body.dark main a:not(.btn)" not in src:
    src = src.rstrip("\n") + "\n" + LINK_BLOCK
    chg = True
    print("  + dark.css: ссылки в контенте получили акцентный цвет")
else:
    print("  = dark.css: акцент ссылок уже стоит")
if chg:
    open(dp, "w", encoding="utf-8", newline="\n").write(src)

# =========================================================================
# ПРАВКА 2. style.css — подсветка АКТИВНОГО пункта меню (работает в обеих
# темах, потому что шапка цветная и в light, и в dark).
# =========================================================================
sp = os.path.join(BASE, "web", "static", "css", "style.css")
if not os.path.exists(sp):
    sp = os.path.join(BASE, "static", "css", "style.css")
ssrc = open(sp, encoding="utf-8").read()
ACTIVE = "nav a.active{background:rgba(255,255,255,.28);box-shadow:inset 0 -2px 0 rgba(255,255,255,.9)}\n"
if "nav a.active" not in ssrc:
    ssrc = ssrc.rstrip("\n") + "\n" + ACTIVE
    open(sp, "w", encoding="utf-8", newline="\n").write(ssrc)
    print("  + style.css: правило подсветки активного пункта меню")
else:
    print("  = style.css: подсветка активного пункта уже стоит")

# =========================================================================
# ПРАВКА 3. base.html — JS-подсветка текущего раздела.
# Вставка каскадом якорей (</body> -> блок content), идемпотентно по маркеру.
# Не зависит от реальных классов/тегов ссылок: ищет nav a по DOM.
# =========================================================================
bp = os.path.join(BASE, "web", "templates", "base.html")
if not os.path.exists(bp):
    bp = os.path.join(BASE, "templates", "base.html")
bsrc = open(bp, encoding="utf-8").read()
MARK = "menu-active"
SCRIPT = (
"\n<script>\n"
"/* " + MARK + ": podsvetka tekushchego razdela (obe temy) */\n"
"(function(){\n"
"  var path = location.pathname.replace(/\\/+$/,'');\n"
"  var links = document.querySelectorAll('nav a');\n"
"  for (var i=0;i<links.length;i++){\n"
"    var a = links[i];\n"
"    var href = (a.getAttribute('href')||'').split('?')[0].split('#')[0];\n"
"    var hh = href.replace(/\\/+$/,'');\n"
"    var ok = (hh==='') ? (path==='') : (path===hh || path.indexOf(hh+'/')===0);\n"
"    if (ok) a.classList.add('active');\n"
"  }\n"
"})();\n"
"</script>\n"
)
if MARK in bsrc:
    print("  = base.html: подсветка меню уже вставлена")
else:
    inserted = False
    if "</body>" in bsrc:
        bsrc = bsrc.replace("</body>", SCRIPT + "</body>", 1)
        inserted = True
        print("  + base.html: JS-подсветка вставлена перед </body>")
    else:
        m = re.search(r"\{%\s*block\s+content\s*%\}[\s\S]*?\{%\s*endblock\s*%\}", bsrc)
        if m:
            bsrc = bsrc[:m.end()] + SCRIPT + bsrc[m.end():]
            inserted = True
            print("  + base.html: JS-подсветка вставлена после блока content")
    if inserted:
        open(bp, "w", encoding="utf-8", newline="\n").write(bsrc)
    else:
        print("  ! base.html: не найдено ни </body>, ни блока content — пришли base.html ФАЙЛОМ")

# =========================================================================
# ПРАВКА 4. history_seed.py (base64) — релиз 0.12.10 + журнал.
# =========================================================================
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
if not os.path.exists(hp):
    print("  ! history_seed.py не найден")
else:
    htxt = open(hp, encoding="utf-8").read()
    m = re.search(r'_B64\s*=\s*"([^"]*)"', htxt)
    if not m:
        print("  ! history_seed.py: нет блока _B64 (не в base64?)")
    else:
        data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
        if any(r.get("version") == "0.12.10" for r in data["releases"]):
            print("  = history_seed.py: 0.12.10 уже есть")
        else:
            data["releases"].insert(0, {
                "version": "0.12.10", "release_date": "2026-11-18", "status": "released",
                "title": "Контраст тёмной темы и подсветка текущего раздела",
                "notes": "В тёмной теме второстепенный текст (заметки .note, пустые состояния .empty, подвал) стал светлее и читается на тёмном фоне вместо прежнего тёмно-серого; ссылки в контенте (в т.ч. названия статей в Справке) получили акцентный цвет вместо тёмного. В меню шапки текущий раздел теперь подсвечивается (работает и в светлой, и в тёмной теме). Светлая тема не изменена."})
            A = "sineronizatsiya dokumentacii"
            data["changelog"].insert(0, {"date": "2026-11-18", "author": A, "change_type": "fixed", "module": "web", "ticket": "", "description": "Тёмная тема: второстепенный текст (.note/.empty/footer) поднят с #6b7280 до #9aa3b2 — читается на тёмном фоне; раньше был темнее светлой темы при инвертированном фоне."})
            data["changelog"].insert(1, {"date": "2026-11-18", "author": A, "change_type": "fixed", "module": "web", "ticket": "", "description": "Тёмная тема: ссылки в контенте (main a, кроме кнопок .btn) получили акцентный цвет #8ea2ff — названия статей в Справке и прочие внутристраничные ссылки больше не тонут в тёмном фоне."})
            data["changelog"].insert(2, {"date": "2026-11-18", "author": A, "change_type": "added", "module": "web", "ticket": "", "description": "Подсветка активного пункта меню: текущий раздел выделяется фоном и нижней линией в обеих темах (JS по DOM nav a + правило nav a.active)."})
            new_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
            htxt = htxt[:m.start(1)] + new_b64 + htxt[m.end(1):]
            open(hp, "w", encoding="utf-8", newline="\n").write(htxt)
            print("  + history_seed.py: релиз 0.12.10 и 3 записи журнала (base64 пересобран)")

print("")
print("=" * 60)
print("MARKER_END: kontrast tёмnoy temy + podsvetka razdela (0.12.10)")
print("=" * 60)
print("Commit + Push:")
print("  web/static/css/dark.css   (muted светлее + акцент ссылок)")
print("  web/static/css/style.css  (nav a.active)")
print("  web/templates/base.html   (JS-подсветка меню)")
print("  modules/versions/history_seed.py (0.12.10)")
print("  tools/installers/install.py")
print("")
print("VM SEGYODNYA NE TROGAEM (net dostupa) — doeedet domoy cheres ./update.sh")