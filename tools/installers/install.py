# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

# rows-thead -> dvustrochnaya shema kak v liste (fbands + fcols).
# Svobodnyi regex: matcit LYBUYO rows-thead-tr (sots 0.13.23 ili original),
# no NE trasaitsya na history/trash (tam net {% for c in cols %} v pervoi stroke)
# i ne na tele (tam {% for line in disp %}, ne {% for c in cols %}).
THEAD_PAT = re.compile(
    r'<tr>\s*\{%\s*for\s+c\s+in\s+cols\s*%\}[\s\S]*?<th>\s*Действия\s*</th>\s*</tr>\s*(?:<!--\s*form-th-v1\s*-->)?',
    re.S)
FBANDS = ('<tr class="fbands">{% for c in cols %}'
          '{% set gi = (groups.index(c.grp) % 6) if c.grp else -1 %}'
          '<th class="fb{% if gi >= 0 %} fg{{ gi }}{% endif %}">'
          '{% if loop.first or (cols[loop.index0-1].grp or \'\') != (c.grp or \'\') %}{{ c.grp or \'\' }}{% endif %}'
          '</th>{% endfor %}<th class="fb"></th></tr>')
FCOLS = ('<tr class="fcols">{% for c in cols %}'
         '{% set gi = (groups.index(c.grp) % 6) if c.grp else -1 %}'
         '<th class="thc ty-{{ c.col_type }}"{% if gi >= 0 %} style="--gc:var(--shg{{ gi }}c)"{% endif %}>'
         '{{ c.title }}{% if c.col_type in (\'computed\',\'ref\') %} ⚙'
         '{% elif can_edit_col(m, c.key) %} ✎{% else %} 🔒{% endif %}</th>{% endfor %}'
         '<th class="thc th-act">Действия</th></tr>')
NEWHEAD = FBANDS + "\n" + FCOLS + " <!-- form-fbands-v1 -->"

vp = os.path.join(BASE, "modules", "tables", "templates", "tables", "view.html")
s = open(vp, encoding="utf-8").read()
if "form-fbands-v1" in s:
    print("SKIP view.html: two-row header (fbands+fcols) already present")
else:
    s2, n = THEAD_PAT.subn(lambda m: NEWHEAD, s, count=1)
    if n:
        open(vp, "w", encoding="utf-8", newline="\n").write(s2)
        print("PATCH view.html: rows header -> fbands + fcols (aligned like sheet)")
    else:
        print("WARN view.html: rows-thead anchor not found (template shape changed?)")

# CSS: dvustrochnaya shapka, sticky, max-height prokrutki, kompaktnoi tnel.
st = os.path.join(BASE, "web", "static", "css", "style.css")
c = open(st, encoding="utf-8").read()
if "form-fbands-css" not in c:
    c = c.rstrip("\n") + '''
/* form-fbands-css: dvustrochnaya shapka formy + sticky + prokrutka v okne */
.tscroll{max-height:72vh;overflow:auto;position:relative;border-radius:8px}
.tscroll thead th{position:sticky;background:#f7f8fb;z-index:3}
.tscroll thead tr.fbands th{top:0;height:22px;line-height:16px;padding:3px 6px;font-size:10px;
 font-weight:800;text-transform:uppercase;letter-spacing:.4px;text-align:center;
 border-bottom:1px solid #e1e6ef;background:#eef1f6;color:#8a93a6}
.tscroll thead tr.fbands th.fg0{background:var(--shg0b);color:var(--shg0c);border-top:2px solid var(--shg0c)}
.tscroll thead tr.fbands th.fg1{background:var(--shg1b);color:var(--shg1c);border-top:2px solid var(--shg1c)}
.tscroll thead tr.fbands th.fg2{background:var(--shg2b);color:var(--shg2c);border-top:2px solid var(--shg2c)}
.tscroll thead tr.fbands th.fg3{background:var(--shg3b);color:var(--shg3c);border-top:2px solid var(--shg3c)}
.tscroll thead tr.fbands th.fg4{background:var(--shg4b);color:var(--shg4c);border-top:2px solid var(--shg4c)}
.tscroll thead tr.fbands th.fg5{background:var(--shg5b);color:var(--shg5c);border-top:2px solid var(--shg5c)}
.tscroll thead tr.fcols th{top:22px;padding:6px 8px;font-size:11px;text-transform:uppercase;
 letter-spacing:.3px;color:#41506b;border-bottom:2px solid #d8dfea;text-align:left;
 vertical-align:top;background:#f7f8fb;white-space:normal;word-break:normal}
.tscroll thead tr.fcols th.ty-number,.tscroll thead tr.fcols th.ty-date{white-space:nowrap}
.tscroll thead tr.fcols th.th-act{min-width:118px}
.tscroll tbody td{vertical-align:middle;padding:7px 8px;word-break:normal}
.tscroll tbody td.ty-number,.tscroll tbody td.ty-date{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tscroll tbody td.ty-text,.tscroll tbody td.ty-list{max-width:240px;word-break:break-word}
.tscroll tbody tr td:last-child{white-space:nowrap;vertical-align:middle}
.tscroll tbody tr td:last-child .btn{padding:3px 9px;font-size:11px;margin:0 2px}
.tscroll table{min-width:100%}
'''
    open(st, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH style.css: fbands/fcols header + sticky + windowed scroll")
else:
    print("SKIP style.css: form-fbands-css present")

dk = os.path.join(BASE, "web", "static", "css", "dark.css")
c = open(dk, encoding="utf-8").read()
if "form-fbands-dark" not in c:
    c = c.rstrip("\n") + '''
/* form-fbands-dark */
body.dark .tscroll thead th{background:#1b2430}
body.dark .tscroll thead tr.fbands th{background:#232e3c;color:#8b99b0;border-bottom-color:#2b3646}
body.dark .tscroll thead tr.fbands th.fg0{background:var(--shg0b);color:var(--shg0c);border-top-color:var(--shg0c)}
body.dark .tscroll thead tr.fbands th.fg1{background:var(--shg1b);color:var(--shg1c);border-top-color:var(--shg1c)}
body.dark .tscroll thead tr.fbands th.fg2{background:var(--shg2b);color:var(--shg2c);border-top-color:var(--shg2c)}
body.dark .tscroll thead tr.fbands th.fg3{background:var(--shg3b);color:var(--shg3c);border-top-color:var(--shg3c)}
body.dark .tscroll thead tr.fbands th.fg4{background:var(--shg4b);color:var(--shg4c);border-top-color:var(--shg4c)}
body.dark .tscroll thead tr.fbands th.fg5{background:var(--shg5b);color:var(--shg5c);border-top-color:var(--shg5c)}
body.dark .tscroll thead tr.fcols th{color:#b9c4d6;border-bottom-color:#2b3646;background:#1b2430}
'''
    open(dk, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH dark.css: fbands/fcols dark")
else:
    print("SKIP dark.css: form-fbands-dark present")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.24" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.24", "release_date": "2026-11-19", "status": "released",
        "title": "Форма: ровная двухстрочная шапка как в листе, прокрутка в окне, кнопки в ряд",
        "notes": "Предыдущая правка формы положила подпись группы под каждый заголовок в одну ячейку, но не зафиксировала высоту заголовка — из-за разной длины названий группы всё равно «плясали», а шапка и строки тела стали выше (добавился перенос кнопок «Изменить/Удалить» в столбик из-за сжатия колонки «Действия»). Теперь шапка формы построена по той же схеме, что и лист: верхняя строка — сплошная цветная полоса групп, нижняя — заголовки; внутри одной строки таблицы все ячейки автоматически одной высоты, поэтому базовые линии ровные без фиксации высоты и без обрезки длинных названий. Контейнер таблицы получил max-height и залипающую шапку: горизонтальная прокрутка теперь всегда видна внизу окна таблицы, а не в конце длинного списка, и шапка не уезжает при прокрутке вниз. Колонка «Действия» получила минимальную ширину, кнопки стоят в ряд и выровнены по центру, строки тела компактнее. Лист и зелёная подсветка чужих правок не менялись."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Форма: шапка переведена на двухстрочную схему листа (полоса групп + заголовки) — выравнивание базовых линий без обрезки; max-height + sticky шапки — горизонтальная прокрутка доступна в окне таблицы; колонка «Действия» с min-width и кнопками в ряд — строки тела компактнее."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.24")
else:
    print("SKIP history_seed.py: 0.13.24 present")

print("=" * 60)
print("MARKER_END: form two-row header + windowed scroll + action row (0.13.24)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/templates/tables/view.html")
print("  web/static/css/style.css")
print("  web/static/css/dark.css")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")