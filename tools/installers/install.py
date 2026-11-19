# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

mp = os.path.join(BASE, "modules", "manual", "templates", "manual", "index.html")
s = open(mp, encoding="utf-8").read()
pat = re.compile(r'[ \t]*<button class="btn gray" onclick="window\.print\(\)">Печать этой страницы</button>[ \t]*\r?\n')
if pat.search(s):
    s = pat.sub("", s, count=1)
    open(mp, "w", encoding="utf-8", newline="\n").write(s)
    print("PATCH manual/index.html: duplicate print button removed")
elif "Печать этой страницы" in s:
    s = s.replace("Печать этой страницы", "", 1)
    s = re.sub(r'[ \t]*<button class="btn gray" onclick="window\.print\(\)"></button>[ \t]*\r?\n', "", s, count=1)
    open(mp, "w", encoding="utf-8", newline="\n").write(s)
    print("PATCH manual/index.html: duplicate print button removed (fallback regex)")
else:
    print("SKIP manual/index.html: duplicate button already gone")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.21" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.21", "release_date": "2026-11-19", "status": "released",
        "title": "В руководстве осталась одна кнопка печати",
        "notes": "После того как «Версия для печати» стала сама открывать диалог печати, серая кнопка «Печать этой страницы» делала ровно то же самое и только путала. Дубль убран: остаётся одна кнопка «🖨 Версия для печати» (чистая бумага без меню, со штампом версии и даты, диалог открывается сам), а повторно открыть диалог можно кнопкой «Печать сейчас» на жёлтом баннере версии для печати."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "changed",
        "module": "manual", "ticket": "",
        "description": "Убрана дублирующая кнопка «Печать этой страницы» в руководстве: печать осталась одна — «Версия для печати» с авто-диалогом и кнопкой «Печать сейчас» на баннере."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.21")
else:
    print("SKIP history_seed.py: 0.13.21 present")

print("=" * 60)
print("MARKER_END: single print button in manual (0.13.21)")
print("=" * 60)
print("Commit + Push:")
print("  modules/manual/templates/manual/index.html")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")