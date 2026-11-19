# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

# 1. routes.py: dobavit' uuid k importam (fixes NameError on _texp_cleanup_old).
rp = os.path.join(BASE, "modules", "tables", "routes.py")
s = open(rp, encoding="utf-8").read()
OLD_IMP = "import json, os, datetime, re"
NEW_IMP = "import json, os, datetime, re, uuid"
if NEW_IMP in s:
    print("SKIP routes.py: uuid already imported")
elif OLD_IMP in s:
    s = s.replace(OLD_IMP, NEW_IMP, 1)
    open(rp, "w", encoding="utf-8", newline="\n").write(s)
    print("PATCH routes.py: added 'uuid' to imports (fixes NameError on import page)")
else:
    m = re.search(r'^import\s+json,\s*os,\s*datetime,\s*re\s*$', s, re.M)
    if m:
        s = s[:m.end()] + ", uuid" + s[m.end():]
        open(rp, "w", encoding="utf-8", newline="\n").write(s)
        print("PATCH routes.py: appended ', uuid' via regex fallback")
    else:
        print("WARN routes.py: import anchor not found — manual fix needed")

# 2. index.html: peredelat' knopku importa v tihuju ssylku vnizu, tol'ko dlya manage.
ip = os.path.join(BASE, "modules", "tables", "templates", "tables", "index.html")
s = open(ip, encoding="utf-8").read()
BIG_BTN = '<a class="btn gray" href="{{ url_for(\'tables.import_json\') }}">📤 Импорт таблицы (.json)</a> <!-- texp-index-v1 -->'
SMALL_LINK = ('{% if can(\'tables.manage\') %}\n'
              '<p style="margin-top:18px;font-size:12px;color:#8a93a6">'
              '<a href="{{ url_for(\'tables.import_json\') }}" style="color:#667eea;text-decoration:underline dotted">'
              '📤 Импорт готовой таблицы из файла (.json)</a>'
              ' · <a href="#" onclick="alert(\'Экспорт делается кнопкой ⬇ Экспорт (.json) в шапке формы или листа нужной таблицы.\');return false" '
              'style="color:#8a93a6">как экспортировать?</a></p>{% endif %}')
if BIG_BTN in s:
    s = s.replace(BIG_BTN, SMALL_LINK, 1)
    open(ip, "w", encoding="utf-8", newline="\n").write(s)
    print("PATCH index.html: import button demoted to quiet link (manage only)")
elif "texp-index-v1" in s or "Импорт готовой таблицы" in s:
    print("SKIP index.html: import link already quiet")
else:
    # fallback: insert before endblock if nothing found
    idx = s.rfind("{% endblock %}")
    if idx != -1:
        s = s[:idx] + "\n" + SMALL_LINK.strip("\n") + "\n" + s[idx:]
        open(ip, "w", encoding="utf-8", newline="\n").write(s)
        print("INSERT index.html: quiet import link added before endblock")
    else:
        print("WARN index.html: no anchor for import link")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.32" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.32", "release_date": "2026-11-19", "status": "released",
        "title": "Импорт таблицы (.json): исправлен импорт uuid, кнопка стала тихой ссылкой",
        "notes": "Страница «/tables/import-json» падала с 500 Internal Server Error из-за NameError: модуль uuid использовался для генерации имени временного файла при предпросмотре импорта, но не был импортирован в начало routes.py (та же причина, что и с re в 0.13.30). Исправлено добавлением uuid в существующую строку импортов. Кроме того, крупная серая кнопка «📤 Импорт таблицы (.json)» в списке таблиц убрана: импорт нужен редко и только админу, поэтому вместо неё появилась тихая пунктирная ссылка внизу страницы, видимая исключительно роли tables.manage, со справочной подсказкой о том, где делать экспорт."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Импорт таблицы (.json): исправлен NameError (не хватало import uuid в routes.py), страница предпросмотра больше не падает с 500."})
    data["changelog"].insert(1, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "changed",
        "module": "tables", "ticket": "",
        "description": "Список таблиц: крупная кнопка импорта заменена тихой ссылкой внизу, видимой только роли tables.manage; добавлена подсказка о месте экспорта."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.32")
else:
    print("SKIP history_seed.py: 0.13.32 present")

print("=" * 60)
print("MARKER_END: import uuid fix + quiet link (0.13.32)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/routes.py")
print("  modules/tables/templates/tables/index.html")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")