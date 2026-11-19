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
OLD_IMP = "import json, os, datetime"
NEW_IMP = "import json, os, datetime, re"
if NEW_IMP in s:
    print("SKIP routes.py: re already imported")
elif OLD_IMP in s:
    s = s.replace(OLD_IMP, NEW_IMP, 1)
    open(rp, "w", encoding="utf-8", newline="\n").write(s)
    print("PATCH routes.py: added 're' to imports (fixes NameError on export)")
else:
    # fallback: find first import line and append , re
    m = re.search(r'^import\s+json,\s*os,\s*datetime\s*$', s, re.M)
    if m:
        s = s[:m.end()] + ", re" + s[m.end():]
        open(rp, "w", encoding="utf-8", newline="\n").write(s)
        print("PATCH routes.py: appended ', re' via regex fallback")
    else:
        print("WARN routes.py: import anchor not found — manual fix needed")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.30" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.30", "release_date": "2026-11-19", "status": "released",
        "title": "Экспорт таблицы (.json) работает: исправлен импорт модуля re",
        "notes": "В 0.13.29 кнопка «⬇ Экспорт (.json)» падала с 500 Internal Server Error из-за NameError: модуль re использовался для очистки имени файла, но не был импортирован в начало routes.py. Исправлено добавлением re в существующую строку импортов; рабочий код маршрутов, шаблонов и листа не изменялся."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Экспорт таблицы (.json): исправлен NameError (не хватало import re в routes.py), кнопка скачивания файла работает."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.30")
else:
    print("SKIP history_seed.py: 0.13.30 present")

print("=" * 60)
print("MARKER_END: export re import fixed (0.13.30)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/routes.py")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")