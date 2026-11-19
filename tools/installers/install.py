# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

rp = os.path.join(BASE, "modules", "tables", "routes.py")
s = open(rp, encoding="utf-8").read()
chg = 0

# 1. Dobavit' session k flaskskim importam.
OLD_FIMP = "from flask import Blueprint, render_template, request, redirect, url_for, flash, abort"
NEW_FIMP = "from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session"
if NEW_FIMP in s:
    print("SKIP routes.py: session already imported")
elif OLD_FIMP in s:
    s = s.replace(OLD_FIMP, NEW_FIMP, 1); chg += 1
    print("PATCH routes.py: added 'session' to flask imports")
else:
    m = re.search(r'^from flask import\s+[^\n]+\Z', s, re.M)
    if m:
        line = m.group(0)
        if ", session" not in line:
            new_line = line.rstrip() + ", session"
            s = s[:m.start()] + new_line + s[m.end():]
            chg += 1
            print("PATCH routes.py: appended ', session' via regex fallback")
        else:
            print("SKIP routes.py: session present in flask import")
    else:
        print("WARN routes.py: flask import anchor not found — manual fix needed")

# 2. Zamenit' request.session -> session vnutri texpimp-v2.
blk_start = s.find("# texpimp-v2:")
if blk_start != -1:
    tail = s[blk_start:]
    n_before = tail.count("request.session")
    if n_before:
        tail = tail.replace("request.session", "session")
        s = s[:blk_start] + tail
        chg += 1
        print("PATCH routes.py: replaced %d occurrences of request.session with session inside texpimp-v2" % n_before)
    else:
        print("SKIP routes.py: no request.session left inside texpimp-v2")
else:
    print("WARN routes.py: texpimp-v2 block marker not found")

if chg:
    open(rp, "w", encoding="utf-8", newline="\n").write(s)

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.33" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.33", "release_date": "2026-11-19", "status": "released",
        "title": "Импорт таблицы (.json): исправлено обращение к сессии Flask",
        "notes": "Страница «/tables/import-json» падала с 500 AttributeError: в 0.13.31 для передачи имени временного файла между шагами предпросмотра и применения я использовал request.session[...], но в Flask сессия доступна только через объект session из пакета flask (from flask import session), а не как атрибут request. Исправлено добавлением session в существующую строку импортов и заменой всех обращений request.session на session внутри блока texpimp-v2. Рабочие маршруты экспорта, кода листа, service.py и models.py не изменялись."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Импорт таблицы (.json): исправлен AttributeError (не хватало import session; использован request.session вместо session), страница предпросмотра и применения больше не падает с 500."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.33")
else:
    print("SKIP history_seed.py: 0.13.33 present")

print("=" * 60)
print("MARKER_END: import session fix (0.13.33)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/routes.py")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")