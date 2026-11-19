# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

# ---------- 1. routes.py: autogen key (backreference indents) ----------
rp_full = os.path.join(BASE, "modules", "tables", "routes.py")
rs = open(rp_full, encoding="utf-8").read()
chg = 0
if "autogen-key-v2" in rs:
    print("SKIP routes.py: autogen-key-v2 present")
else:
    pat_tn = re.compile(
        r'\n([ \t]*)if not title or not key:\n([ \t]+)flash\("Укажите название и ключ таблицы[^"]*"\)\n[ \t]+return redirect\(url_for\("tables\.index"\)\)'
    )
    rep_tn = (
        r'\n\1if not title:\n\2flash("Укажите название таблицы.")\n\2return redirect(url_for("tables.index"))'
        r'\n\1if not key:  # autogen-key-v2'
        r'\n\2taken = {t.key for t in CustomTable.query.all()}'
        r'\n\2key = unique_key(translit_ru_to_latin(title), taken)'
    )
    rs, n_tn = pat_tn.subn(rep_tn, rs, count=1)
    if n_tn:
        chg += 1; print("PATCH routes.py: table_new -> autogen key (backreference indents)")
    else:
        print("WARN routes.py: table_new flash-anchor not matched")

    pat_cs = re.compile(
        r'\n([ \t]*)if not title or not key:\n([ \t]+)flash\("Укажите название и ключ колонки\."\)\n[ \t]+return redirect\(url_for\("tables\.cols", tid=tid\)\)'
    )
    rep_cs = (
        r'\n\1if not title:\n\2flash("Укажите название колонки.")\n\2return redirect(url_for("tables.cols", tid=tid))'
        r'\n\1if not key:  # autogen-key-v2'
        r'\n\2taken = {c.key for c in cols_of(tid)}'
        r'\n\2key = unique_key(translit_ru_to_latin(title), taken)'
    )
    rs, n_cs = pat_cs.subn(rep_cs, rs, count=1)
    if n_cs:
        chg += 1; print("PATCH routes.py: col_save -> autogen key (backreference indents)")
    else:
        print("WARN routes.py: col_save flash-anchor not matched")
    if chg:
        open(rp_full, "w", encoding="utf-8", newline="\n").write(rs)
    else:
        print("NOTE routes.py: nothing changed")

# ---------- 2. colhuman-fix-v1: snyat' required so skrytye klyuchi ne blokiruyut submit ----------
FIXJS = """
<script>
/* colhuman-fix-v1: snymaem required/readonly s skrytyh polej key, chtoby
   display:none + required ne blokirovali submit molcha (prichina "nichego ne proishodit"). */
(function(){
function boot(){
 var ks=document.querySelectorAll('input[name="key"], select[name="key"], textarea[name="key"]');
 for(var i=0;i<ks.length;i++){
  ks[i].removeAttribute("required");
  ks[i].removeAttribute("pattern");
  ks[i].setAttribute("autocomplete","off");
 }
}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",boot);}else{boot();}
})();
</script>
"""
def ins_fix(rel):
    p = os.path.join(BASE, *rel.split("/"))
    s = open(p, encoding="utf-8").read()
    if "colhuman-fix-v1" in s:
        print("SKIP " + rel + ": colhuman-fix-v1 present"); return
    idx = s.rfind("{% endblock %}")
    if idx == -1:
        print("WARN " + rel + ": endblock not found"); return
    open(p, "w", encoding="utf-8", newline="\n").write(s[:idx] + FIXJS.strip("\n") + "\n" + s[idx:])
    print("INSERT " + rel + ": colhuman-fix-v1 before endblock")

ins_fix("modules/tables/templates/tables/cols.html")
ins_fix("modules/tables/templates/tables/index.html")

# ---------- 3. index.html: udalit' dubliruyushchijsya staryj blok .info ----------
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

# ---------- 4. history_seed: reliz 0.13.37 ----------
hp_full = os.path.join(BASE, "modules", "versions", "history_seed.py")
hs = open(hp_full, encoding="utf-8").read()
hm = re.search(r'_B64\s*=\s*"([^"]*)"', hs)
hd = json.loads(base64.b64decode(hm.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.37" for r in hd["releases"]):
    hd["releases"].insert(0, {"version": "0.13.37", "release_date": "2026-11-19", "status": "released",
        "title": "Сохранение колонки починено: скрытый required больше не блокирует отправку + автогенерация ключа",
        "notes": "После 0.13.34 нажатие «Сохранить колонку» не давало никакого запроса на сервер: скрипт colhuman-v1 скрыл техническое поле ключа классом display:none, но оставил на нём атрибут required, из-за чего браузер молча блокировал отправку формы (невидимое обязательное поле невозможно показать пользователю). Добавлен colhuman-fix-v1, который снимает required/pattern со всех скрытых полей ключа на страницах колонок и списка таблиц. Одновременно доделана серверная автогенерация: table_new и col_save теперь, если ключ не указан, подбирают его из русского названия через транслитерацию с проверкой уникальности (замена выполнена по уникальным текстовым якорям сообщений flash, отступы захватываются из фактического файла регулярными группами, поэтому правка не зависит от пробелов/табов и не вызывает IndenationError). Из index.html удалён дублирующий старый блок создания таблицы с обязательным латинским ключом — остался единый блок с русским названием и карточками шаблонов. Лист, ширина, drag колонок, экспорт/импорт .json, визуальный редактор формул и человеческие подписи не изменялись."})
    hd["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Сохранение колонки/таблицы: снят required со скрытых полей ключа (colhuman-fix-v1) — форма больше не блокируется молча; автогенерация ключа из русского названия в table_new и col_save доделана по flash-якорям с захватом реальных отступов."})
    hd["changelog"].insert(1, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "changed",
        "module": "tables", "ticket": "",
        "description": "index.html: удалён дублирующий старый блок создания таблицы с обязательным латинским ключом."})
    nb_hs = base64.b64encode(json.dumps(hd, ensure_ascii=False).encode("utf-8")).decode("ascii")
    hs = hs[:hm.start(1)] + nb_hs + hs[hm.end(1):]
    open(hp_full, "w", encoding="utf-8", newline="\n").write(hs)
    print("PATCH history_seed.py: release 0.13.37")
else:
    print("SKIP history_seed.py: 0.13.37 present")

print("=" * 60)
print("MARKER_END: hidden-required unblocked + autogen key (0.13.37)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/routes.py")
print("  modules/tables/templates/tables/cols.html")
print("  modules/tables/templates/tables/index.html")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")