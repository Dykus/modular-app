# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

PREPASS = ('{% set groups = [] %}{% for c in cols %}'
           '{% if c.grp and c.grp not in groups %}{% if groups.append(c.grp) %}{% endif %}{% endif %}{% endfor %}')
NEWTR = ('<tr>\n{% for c in cols %}{% set gi = (groups.index(c.grp) % 6) if c.grp else -1 %}'
         '<th class="thc ty-{{ c.col_type }}{% if gi >= 0 %} hasgrp{% endif %}"'
         '{% if gi >= 0 %} style="--gc:var(--shg{{ gi }}c);--gb:var(--shg{{ gi }}b)"{% endif %}>'
         '<span class="tht">{{ c.title }}{% if c.col_type in (\'computed\',\'ref\') %} ⚙'
         '{% elif can_edit_col(m, c.key) %} ✎{% else %} 🔒{% endif %}</span>'
         '{% if c.grp %}<span class="thg">{{ c.grp }}</span>{% else %}<span class="thg">&nbsp;</span>{% endif %}'
         '</th>{% endfor %}<th>Действия</th></tr>')
HDR_PAT = re.compile(r'<tr>\s*\{%\s*for\s+c\s+in\s+cols\s*%\}.*?<th>\s*Действия\s*</th>\s*</tr>', re.S)
OLD_TD = '{% for c in cols %}<td>{{ line.cells[c.key] }}</td>{% endfor %}'
NEW_TD = '{% for c in cols %}<td class="ty-{{ c.col_type }}">{{ line.cells[c.key] }}</td>{% endfor %}'

vp = os.path.join(BASE, "modules", "tables", "templates", "tables", "view.html")
s = open(vp, encoding="utf-8").read()
chg = 0
if "form-th-v1" not in s:
    s2, n = HDR_PAT.subn(lambda m: PREPASS + "\n" + NEWTR + " <!-- form-th-v1 -->", s, count=1)
    if n:
        s = s2; chg += 1
        print("PATCH view.html: header row -> flex column + colored group label")
    else:
        print("WARN view.html: header <tr> anchor not found")
if OLD_TD in s:
    s = s.replace(OLD_TD, NEW_TD, 1); chg += 1
    print("PATCH view.html: body cells get type classes (align/wrap)")
elif 'class="ty-' in s:
    print("SKIP view.html: body cells already classed")
else:
    print("WARN view.html: body td loop anchor not found")
if chg:
    open(vp, "w", encoding="utf-8", newline="\n").write(s)

st = os.path.join(BASE, "web", "static", "css", "style.css")
c = open(st, encoding="utf-8").read()
if "form-th-css" not in c:
    c = c.rstrip("\n") + '''
/* form-th-css: palette + aligned colored group labels + stable widths (Form) */
:root{--shg0c:#0b6bcb;--shg0b:#e3f0fd;--shg1c:#c96a10;--shg1b:#fdf0e0;--shg2c:#2b8a3e;--shg2b:#e6f6e9;--shg3c:#6741d9;--shg3b:#efeafc;--shg4c:#0c8599;--shg4b:#e0f5f8;--shg5c:#a61e4d;--shg5b:#fde8ef}
body.dark{--shg0c:#4dabf7;--shg0b:#12283d;--shg1c:#ffa94d;--shg1b:#33230f;--shg2c:#69db7c;--shg2b:#122b18;--shg3c:#b197fc;--shg3b:#241b3a;--shg4c:#66d9e8;--shg4b:#0f2e33;--shg5c:#faa2c1;--shg5b:#3a1220}
.tscroll table thead th.thc{vertical-align:top;padding:6px 8px;text-align:left}
.tscroll table thead th.thc .tht{display:block;font-weight:700;text-transform:uppercase;letter-spacing:.3px;font-size:11px;line-height:1.25;word-break:break-word}
.tscroll table thead th.thc .thg{display:block;margin-top:5px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-top:2px solid var(--gc,transparent);padding-top:3px;color:#8a93a6}
.tscroll table thead th.thc.hasgrp .thg{color:var(--gc);background:var(--gb);border-radius:0 0 5px 5px;padding:2px 5px}
.tscroll table thead th.ty-number .tht,.tscroll table thead th.ty-date .tht{white-space:nowrap}
.tscroll table thead th.ty-number,.tscroll table thead th.ty-date{min-width:86px}
.tscroll table thead th.ty-text,.tscroll table thead th.ty-list{min-width:100px;max-width:220px}
.tscroll table tbody td{vertical-align:top;word-break:break-word}
.tscroll table tbody td.ty-number,.tscroll table tbody td.ty-date{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
@media print{.tscroll table thead th.thc .thg{border-top-color:#999}}
'''
    open(st, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH style.css: form header palette + widths")
else:
    print("SKIP style.css: form-th-css present")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.23" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.23", "release_date": "2026-11-19", "status": "released",
        "title": "Форма: ровная цветная шапка и стабильные ширины колонок",
        "notes": "В шапке вида «Форма» заголовок и подпись группы лежали в одном потоке: у колонок с длинным названием группа уезжала вниз, подписи «плясали» по высоте, цвет отдела отсутствовал, а ширины колонок тянулись по содержимому и длинный заголовок обрезался. Теперь каждая ячейка шапки — flex-колонка с одинаковой высотой слота группы (пустая группа резервирует строку), подпись группы окрашена в цвет отдела той же палитрой, что и лист (индекс по порядку первого появления), числа и даты не переносятся и выровнены вправо табличными цифрами, текст и списки переносят слова с разумными min/max. Палитра объявлена на :root/body.dark в style.css, поэтому форма видит её вне #shroot; лист продолжает использовать свои значения без конфликта. Лист и зелёная подсветка чужих правок не менялись."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "fixed",
        "module": "tables", "ticket": "",
        "description": "Форма: шапка выровнена по базовой линии (flex-колонка, слот группы одинаковой высоты), группы окрашены палитрой листа, ширины колонок стабилизированы по типу (число/дата nowrap+вправо, текст/список перенос), обрезка длинных заголовков устранена."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.23")
else:
    print("SKIP history_seed.py: 0.13.23 present")

print("=" * 60)
print("MARKER_END: form header aligned + colored + widths (0.13.23)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/templates/tables/view.html")
print("  web/static/css/style.css")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")