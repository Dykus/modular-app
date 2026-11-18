# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

jp = os.path.join(BASE, "web", "static", "js", "sheet.js")
s = open(jp, encoding="utf-8").read()
ANCHOR = 'var td=e.target.closest("td[data-key]");if(!td)return;'
GUARD = 'if(e.target.closest("td.editing"))return; /* edit-click-guard */\n var td=e.target.closest("td[data-key]");if(!td)return;'
if "edit-click-guard" in s:
    print("SKIP sheet.js: edit-click guard present")
elif ANCHOR in s:
    s = s.replace(ANCHOR, GUARD, 1)
    open(jp, "w", encoding="utf-8", newline="\n").write(s)
    print("PATCH sheet.js: clicks inside open editor no longer recreate it")
else:
    print("WARN sheet.js: click handler anchor not found")

vp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(vp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.7" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.7", "release_date": "2026-11-18", "status": "released",
        "title": "Лист: выпадающий список в клетке больше не захлопывается",
        "notes": "Клик по уже открытому редактору клетки (стрелке списка или внутри текстового поля) повторно вызывал открытие редактора: старый редактор вместе с раскрытым списком и набранным текстом уничтожался и создавался новый закрытый — список «исчезал», не дав выбрать. Добавлена стража: клики внутри редактируемой клетки не пересоздают редактор. Выбор значения, позиционирование курсора и раскрытие списка теперь работают как в Excel."})
    data["changelog"].insert(0, {"date": "2026-11-18", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Лист: клики внутри открытого редактора клетки больше не пересоздают его — выпадающий список не захлопывается при раскрытии, набранный текст не теряется при клике для позиционирования курсора."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(vp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.7")
else:
    print("SKIP history_seed.py: 0.13.7 present")

print("=" * 60)
print("MARKER_END: editor click guard (0.13.7)")
print("=" * 60)
print("Commit + Push:")
print("  web/static/js/sheet.js")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")