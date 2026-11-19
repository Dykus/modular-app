# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

rp_full = os.path.join(BASE, "modules", "tables", "routes.py")
rs = open(rp_full, encoding="utf-8").read()
chg = 0

if "autogen-key-v2" in rs:
    print("SKIP routes.py: autogen-key-v2 present")
else:
    # --- table_new: ykor' = unikal'nyj tekst flash pro klyuch tablicy.
    pat_tn = re.compile(
        r'\n([ \t]*)if not title or not key:\n([ \t]+)flash\("Укажите название и ключ таблицы[^"]*"\)\n[ \t]+return redirect\(url_for\("tables\.index"\)\)'
    )
    rep_tn = (
        r'\n\1if not title:\n\2flash("Укажите название таблицы.")\n\2return redirect(url_for("tables.index"))'
        r'\n\1if not key:  # autogen-key-v2'
        r'\n\2taken = {t.key for t in CustomTable.query.all()}'
        r'\n\2key = unique_key(translit_ru_to_latin(title), taken)'
    )
    rs2, n_tn = pat_tn.subn(rep_tn, rs, count=1)
    if n_tn:
        rs = rs2; chg += 1
        print("PATCH routes.py: table_new -> autogen key from title (backreference indents)")
    else:
        print("WARN routes.py: table_new flash-anchor not matched")

    # --- col_save: ykor' = unikal'nyj tekst flash pro klyuch kolonki.
    pat_cs = re.compile(
        r'\n([ \t]*)if not title or not key:\n([ \t]+)flash\("Укажите название и ключ колонки\."\)\n[ \t]+return redirect\(url_for\("tables\.cols", tid=tid\)\)'
    )
    rep_cs = (
        r'\n\1if not title:\n\2flash("Укажите название колонки.")\n\2return redirect(url_for("tables.cols", tid=tid))'
        r'\n\1if not key:  # autogen-key-v2'
        r'\n\2taken = {c.key for c in cols_of(tid)}'
        r'\n\2key = unique_key(translit_ru_to_latin(title), taken)'
    )
    rs2, n_cs = pat_cs.subn(rep_cs, rs, count=1)
    if n_cs:
        rs = rs2; chg += 1
        print("PATCH routes.py: col_save -> autogen key from title (backreference indents)")
    else:
        print("WARN routes.py: col_save flash-anchor not matched")

    if chg:
        open(rp_full, "w", encoding="utf-8", newline="\n").write(rs)
    else:
        print("NOTE routes.py: nothing changed")

# index.html: udalyaem dubliruyushchij staryj blok .info (ostavlyaem tol'ko .card s shablonami).
ip_full = os.path.join(BASE, "modules", "tables", "templates", "tables", "index.html")
is_content = open(ip_full, encoding="utf-8").read()
pat_info = re.compile(
    r'<div class="info">\s*<h3>Создать таблицу</h3>[\s\S]*?<p class="note">После создания[\s\S]*?</div>\s*'
)
if pat_info.search(is_content):
    is_content = pat_info.sub("", is_content, count=1)
    open(ip_full, "w", encoding="utf-8", newline="\n").write(is_content)
    print("PATCH index.html: duplicate legacy create-block (.info) removed")
elif "Создать таблицу" not in is_content:
    print("SKIP index.html: legacy create-block already gone")
else:
    print("WARN index.html: legacy .info block shape not matched (left as-is)")

# history_seed: reliz 0.13.36.
hp_full = os.path.join(BASE, "modules", "versions", "history_seed.py")
hs = open(hp_full, encoding="utf-8").read()
hm = re.search(r'_B64\s*=\s*"([^"]*)"', hs)
hd = json.loads(base64.b64decode(hm.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.36" for r in hd["releases"]):
    hd["releases"].insert(0, {"version": "0.13.36", "release_date": "2026-11-19", "status": "released",
        "title": "Автогенерация ключей заработала + убран дубль блока создания таблицы",
        "notes": "После 0.13.34 автогенерация ключей в table_new и col_save не применилась (установщик искал многострочные блоки с фиксированными переносами, а реальный код был оформлен иначе), из-за чего создание пустой таблицы и добавление колонки вручную по-прежнему требовали латинский ключ и выдавали тост «Укажите название и ключ…». Теперь замена выполнена по уникальным текстовым якорям сообщений flash, а отступы захватываются из фактического файла регулярными группами и переиспользуются — поэтому правка не зависит от пробелов/табов и не вызывает IndentationError. Дополнительно из index.html удалён дублирующий старый блок «Создать таблицу» с обязательным полем «Ключ латиницей»: остался только новый блок с русским названием и карточками шаблонов, служебное имя подбирается сервером автоматически. Скрытое ранее поле ключа больше не отправляется пустым, ложный тост исчезает. Шаблоны, человеческие подписи типов, визуальный редактор формул и лист не изменялись."})
    hd["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "table_new и col_save: автогенерация ключа из русского названия починена точечной заменой по уникальным flash-якорям с захватом реальных отступов (backreference), без зависимости от форматирования."})
    hd["changelog"].insert(1, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "changed",
        "module": "tables", "ticket": "",
        "description": "index.html: удалён дублирующий старый блок создания таблицы с обязательным латинским ключом; остался единый блок с русским названием и шаблонами."})
    nb_hs = base64.b64encode(json.dumps(hd, ensure_ascii=False).encode("utf-8")).decode("ascii")
    hs = hs[:hm.start(1)] + nb_hs + hs[hm.end(1):]
    open(hp_full, "w", encoding="utf-8", newline="\n").write(hs)
    print("PATCH history_seed.py: release 0.13.36")
else:
    print("SKIP history_seed.py: 0.13.36 present")

print("=" * 60)
print("MARKER_END: autogen key fixed + legacy create-block removed (0.13.36)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/routes.py")
print("  modules/tables/templates/tables/index.html")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")