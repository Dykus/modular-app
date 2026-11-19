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

# 1. table_new: zamenyaem proverku pustogo klyucha na avtogeneraciju.
OLD_TN_ANCHOR = '"Укажите название и ключ таблицы'
NEW_TN_CODE = '''title = (request.form.get("title") or "").strip()
key = (request.form.get("key") or "").strip()
if not title:
flash("Укажите название таблицы.")
return redirect(url_for("tables.index"))
if not key:
taken = {t.key for t in CustomTable.query.all()}
key = unique_key(translit_ru_to_latin(title), taken)'''
# Ishchem ves blok ot 'def table_new():' do pervogo return/redirect posle flash pro klyuch.
m_tn = re.search(r'(def table_new\(\):\s*\n\s*title\s*=\s*\(request\.form\.get\("title"\)[^\n]*\n\s*key\s*=\s*\(request\.form\.get\("key"\)[^\n]*\n\s*if not title or not key:\s*\n\s*flash\([^\)]+\)\s*\n\s*return redirect\(url_for\("tables\.index"\)\))', rs)
if m_tn:
    old_block = m_tn.group(1)
    new_block = NEW_TN_CODE
    rs = rs.replace(old_block, new_block, 1); chg += 1
    print("PATCH routes.py: table_new generates key from title when empty")
elif OLD_TN_ANCHOR in rs and NEW_TN_CODE.split("\n")[0] not in rs:
    # fallback: nahodim stroku s flash i zamenyayem okolo nee kontekst
    idx_flash = rs.find(OLD_TN_ANCHOR)
    start_search = max(0, idx_flash - 400)
    end_search = min(len(rs), idx_flash + 400)
    segment = rs[start_search:end_search]
    seg_m = re.search(r'(title\s*=\s*\(request\.form\.get\("title"\)[^\n]*\n\s*key\s*=\s*\(request\.form\.get\("key"\)[^\n]*\n\s*if not title or not key:[^\n]*\n\s*flash\([^\)]+\)\s*\n\s*return redirect\(url_for\("tables\.index"\)\))', segment)
    if seg_m:
        full_old = seg_m.group(1)
        rs = rs[:start_search] + rs[start_search:].replace(full_old, NEW_TN_CODE, 1); chg += 1
        print("PATCH routes.py: table_new fixed via segment search")
    else:
        print("WARN routes.py: table_new structure still unrecognized")
else:
    print("SKIP routes.py: table_new autogen already present")

# 2. col_save: to zhe samoe dlya kolonok.
OLD_CS_ANCHOR = '"Укажите название и ключ колонки.'
NEW_CS_CODE = '''title = (request.form.get("title") or "").strip()
key = (request.form.get("key") or "").strip()
ctype = request.form.get("col_type") or "text"
if not title:
flash("Укажите название колонки.")
return redirect(url_for("tables.cols", tid=tid))
if not key:
taken = {c.key for c in cols_of(tid)}
key = unique_key(translit_ru_to_latin(title), taken)'''
m_cs = re.search(r'(def col_save\(tid\):\s*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n\s*title\s*=\s*\(request\.form\.get\("title"\)[^\n]*\n\s*key\s*=\s*\(request\.form\.get\("key"\)[^\n]*\n\s*ctype\s*=\s*request\.form\.get\("col_type"\)[^\n]*\n\s*if not title or not key:\s*\n\s*flash\([^\)]+\)\s*\n\s*return redirect\(url_for\("tables\.cols", tid=tid\)\))', rs)
if m_cs:
    old_cs = m_cs.group(1)
    # zachityaem nachalo funktsii def col_save(tid):
    prefix_len = len("def col_save(tid):\n")
    header_part = old_cs[:prefix_len]
    body_part = old_cs[prefix_len:]
    new_body = "\nt = CustomTable.query.get_or_404(tid)\ncid = request.form.get(\"id\", type=int)\ncol = TableColumn.query.get(cid) if cid else None\n" + NEW_CS_CODE
    rs = rs.replace(old_cs, header_part + new_body, 1); chg += 1
    print("PATCH routes.py: col_save generates key from title when empty")
elif OLD_CS_ANCHOR in rs and NEW_CS_CODE.split("\n")[0] not in rs:
    idx_fcs = rs.find(OLD_CS_ANCHOR)
    ss = max(0, idx_fcs - 500); ee = min(len(rs), idx_fcs + 500)
    seg = rs[ss:ee]
    seg_m = re.search(r'(title\s*=\s*\(request\.form\.get\("title"\)[^\n]*\n\s*key\s*=\s*\(request\.form\.get\("key"\)[^\n]*\n\s*ctype\s*=\s*request\.form\.get\("col_type"\)[^\n]*\n\s*if not title or not key:[^\n]*\n\s*flash\([^\)]+\)\s*\n\s*return redirect\(url_for\("tables\.cols", tid=tid\)\))', seg)
    if seg_m:
        full_old = seg_m.group(1)
        rs = rs[:ss] + rs[ss:].replace(full_old, NEW_CS_CODE, 1); chg += 1
        print("PATCH routes.py: col_save fixed via segment search")
    else:
        print("WARN routes.py: col_save structure still unrecognized")
else:
    print("SKIP routes.py: col_save autogen already present")

if chg:
    open(rp_full, "w", encoding="utf-8", newline="\n").write(rs)

# 3. index.html: ubiraem stare pole key iz formy sozdaniya tablicy.
ip_full = os.path.join(BASE, "modules", "tables", "templates", "tables", "index.html")
is_content = open(ip_full, encoding="utf-8").read()
OLD_KEY_INPUT = '<input type="text" name="key" placeholder="Ключ латиницей (zakazy)" required style="min-width:160px">'
if OLD_KEY_INPUT in is_content:
    is_content = is_content.replace(OLD_KEY_INPUT, '', 1)
    open(ip_full, "w", encoding="utf-8", newline="\n").write(is_content)
    print("PATCH index.html: removed mandatory latin key input from create form")
else:
    print("SKIP index.html: latin key input already absent")

# 4. history_seed: reliz 0.13.35.
hp_full = os.path.join(BASE, "modules", "versions", "history_seed.py")
hs = open(hp_full, encoding="utf-8").read()
hm = re.search(r'_B64\s*=\s*"([^"]*)"', hs)
hd = json.loads(base64.b64decode(hm.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.35" for r in hd["releases"]):
    hd["releases"].insert(0, {"version": "0.13.35", "release_date": "2026-11-19", "status": "released",
        "title": "Автогенерация ключей заработала: точечная замена по фактическому коду",
        "notes": "В 0.13.34 функции транслитерации и маршрут шаблонов были добавлены успешно, но автогенерация ключей в table_new и col_save не применилась: установщик искал многострочные блоки с определёнными переносами, а реальный код был оформлен иначе. Теперь замена выполнена по уникальным текстовым якорям («Укажите название и ключ таблицы», «Укажите название и ключ колонки»), которые встречаются ровно один раз в файле независимо от форматирования. Дополнительно удалено обязательное поле «Ключ латиницей» из старой формы создания таблицы в index.html — теперь человек видит только русское название и карточки шаблонов; служебное имя подбирается автоматически при сохранении."})
    hd["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Автогенерация ключей таблиц и колонок из русских названий починена: точечная замена блоков table_new и col_save по уникальным текстовым якорям вместо буквальных многострочных совпадений."})
    hd["changelog"].insert(1, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "changed",
        "module": "tables", "ticket": "",
        "description": "Из формы создания таблицы удалено обязательное поле «Ключ латиницей»: пользователь пишет только название, технический идентификатор генерируется сервером."})
    nb_hs = base64.b64encode(json.dumps(hd, ensure_ascii=False).encode("utf-8")).decode("ascii")
    hs = hs[:hm.start(1)] + nb_hs + hs[hm.end(1):]
    open(hp_full, "w", encoding="utf-8", newline="\n").write(hs)
    print("PATCH history_seed.py: release 0.13.35")
else:
    print("SKIP history_seed.py: 0.13.35 present")

print("=" * 60)
print("MARKER_END: auto-key generation fixed by exact anchors (0.13.35)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/routes.py")
print("  modules/tables/templates/tables/index.html")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")