# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

vp = os.path.join(BASE, "modules", "tables", "templates", "tables", "view.html")
s = open(vp, encoding="utf-8").read()
if 'class="tscroll"' in s:
    print("SKIP view.html: tscroll wrappers present")
else:
    s2, n1 = re.subn(r'<table\b[^>]*>', lambda m: '<div class="tscroll">' + m.group(0), s)
    s2, n2 = re.subn(r'</table>', '</table></div>', s2)
    if n1 and n1 == n2:
        open(vp, "w", encoding="utf-8", newline="\n").write(s2)
        print("PATCH view.html: wrapped %d table(s) in .tscroll" % n1)
    else:
        print("WARN view.html: table open/close mismatch (%d/%d), not written" % (n1, n2))

sp = os.path.join(BASE, "web", "static", "css", "style.css")
c = open(sp, encoding="utf-8").read()
if "tscroll-fix" not in c:
    c = c.rstrip("\n") + (
        "\n/* tscroll-fix: shirokie tablicy skrollyatsya vnutri kartochki, ne za kraya */\n"
        ".tscroll{overflow-x:auto;border-radius:8px}\n"
        ".tscroll::-webkit-scrollbar{height:10px}\n"
        ".tscroll::-webkit-scrollbar-thumb{background:#8a93a6;border-radius:6px}\n"
        ".tscroll::-webkit-scrollbar-thumb:hover{background:#737c8e}\n"
        ".tscroll::-webkit-scrollbar-track{background:#eef1f6;border-radius:6px}\n")
    open(sp, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH style.css: .tscroll rules added")
else:
    print("SKIP style.css: tscroll-fix present")

dp = os.path.join(BASE, "web", "static", "css", "dark.css")
c = open(dp, encoding="utf-8").read()
if "tscroll-dark" not in c:
    c = c.rstrip("\n") + (
        "\n/* tscroll-dark */\n"
        "body.dark .tscroll::-webkit-scrollbar-thumb{background:#3a3f4b}\n"
        "body.dark .tscroll::-webkit-scrollbar-thumb:hover{background:#4a5060}\n"
        "body.dark .tscroll::-webkit-scrollbar-track{background:#1a1d24}\n")
    open(dp, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH dark.css: .tscroll dark scrollbar")
else:
    print("SKIP dark.css: tscroll-dark present")

pp = os.path.join(BASE, "web", "static", "css", "print.css")
c = open(pp, encoding="utf-8").read()
if "tscroll-print" not in c:
    c = c.rstrip("\n") + "\n/* tscroll-print */\n@media print{.tscroll{overflow:visible}}\n"
    open(pp, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH print.css: tscroll visible on paper")
else:
    print("SKIP print.css: tscroll-print present")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.6" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.6", "release_date": "2026-11-18", "status": "released",
        "title": "Форма: широкие таблицы прокручиваются внутри карточки",
        "notes": "Таблица вида «Форма» с большим числом колонок вылезала за края белой карточки и страницы: у таблиц не было прокручиваемой обёртки. Теперь каждая таблица Формы обёрнута в блок с горизонтальной прокруткой внутри карточки, полоса прокрутки стилизована под светлую и тёмную темы, на печать таблица уходит целиком. Виды «Лист» и «Форма» остаются равноправными (вариант A): никаких смен вида по умолчанию не сделано."})
    data["changelog"].insert(0, {"date": "2026-11-18", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Форма: широкие таблицы больше не вылезают за края карточки — обёртка с горизонтальной прокруткой внутри карточки, стилизованная полоса прокрутки в обеих темах, корректная печать."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.6")
else:
    print("SKIP history_seed.py: 0.13.6 present")

print("=" * 60)
print("MARKER_END: form tables scroll inside card (0.13.6)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/templates/tables/view.html")
print("  web/static/css/style.css")
print("  web/static/css/dark.css")
print("  web/static/css/print.css")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")