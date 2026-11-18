# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)

NEW_HEADER = '''
<div class="tb-head thead-v2">
  <div class="tb-tabs">
    <a class="tb-tab tswitch" href="{{ url_for('tables.sheet_view', tid=t.id) }}">📊 Лист (Excel-вид)</a>
    {% for x in tabs %}<a class="tb-tab{% if x.id == t.id %} on{% endif %}" href="{{ url_for('tables.view', tid=x.id) }}">{{ x.title }}</a>{% endfor %}
  </div>
  <div class="tb-title">
    <h2>{{ t.title }}</h2>
    <div class="tb-acts">
      <a class="btn" href="{{ url_for('tables.row_edit', tid=t.id, rid='new') }}">＋ Строка</a>
      <a class="btn gray" href="{{ url_for('tables.import_xlsx', tid=t.id) }}">⬇ Импорт Excel</a>
      <a class="btn gray{% if mode == 'rows' %} on{% endif %}" href="{{ url_for('tables.view', tid=t.id) }}">Строки</a>
      <a class="btn gray{% if mode == 'trash' %} on{% endif %}" href="{{ url_for('tables.view', tid=t.id, mode='trash') }}">🗑 Корзина ({{ trash_count }})</a>
      <a class="btn gray{% if mode == 'history' %} on{% endif %}" href="{{ url_for('tables.view', tid=t.id, mode='history') }}">🕓 История клеток</a>
      {% if can('tables.manage') %}
      <a class="btn gray" href="{{ url_for('tables.cols', tid=t.id) }}">⚙ Колонки и формулы</a>
      <a class="btn gray" href="{{ url_for('tables.access', tid=t.id) }}">🛡 Доступ (роли × колонки)</a>
      <form method="post" action="{{ url_for('tables.table_delete', tid=t.id) }}" class="tb-danger"
            onsubmit="return confirm('Удалить таблицу целиком? Будет создана резервная копия в data/backups/.');">
        <button class="btn red" type="submit">🗑 Удалить таблицу</button>
      </form>
      {% endif %}
    </div>
  </div>
</div>
'''

vp = os.path.join(BASE, "modules", "tables", "templates", "tables", "view.html")
s = open(vp, encoding="utf-8").read()
if "thead-v2" in s:
    print("SKIP view.html: header v2 present")
else:
    m = re.search(r"({%\s*block\s+content\s*%})([\s\S]*?)({%\s*if\s+counters\s*%})", s)
    if m:
        s = s[:m.end(1)] + "\n" + NEW_HEADER.strip("\n") + "\n" + s[m.start(3):]
        open(vp, "w", encoding="utf-8", newline="\n").write(s)
        print("PATCH view.html: header rebuilt (tabs strip + title row + grouped actions)")
    else:
        print("WARN view.html: block-content/counters anchors not found")

sp = os.path.join(BASE, "web", "static", "css", "style.css")
c = open(sp, encoding="utf-8").read()
if "tables-head-v2" not in c:
    c = c.rstrip("\n") + '''
/* tables-head-v2: lenta vkladok + zagolovok s deystviyami spava */
.tb-head{margin-bottom:14px}
.tb-tabs{display:flex;gap:6px;flex-wrap:wrap;align-items:center;background:rgba(102,126,234,.08);
 border:1px solid #e1e6ef;border-radius:10px;padding:6px;margin-bottom:12px}
.tb-tab{padding:7px 14px;border-radius:8px;font-size:13px;font-weight:600;color:#5a6b85;
 text-decoration:none;background:transparent;border:1px solid transparent;transition:.15s;white-space:nowrap}
.tb-tab:hover{background:#fff;color:#2c3e50;box-shadow:0 2px 6px rgba(20,30,60,.08)}
.tb-tab.on{background:#667eea;color:#fff;box-shadow:0 3px 10px rgba(102,126,234,.35)}
.tb-tab.tswitch{border:1px dashed #8a93a6;color:#41506b}
.tb-tab.tswitch:hover{border-style:solid;background:#fff}
.tb-title{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px}
.tb-title h2{margin-right:auto}
.tb-acts{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.tb-acts .btn{padding:8px 13px;font-size:13px}
.tb-acts .btn.on{background:#5566d8}
.tb-danger{display:inline-flex;margin-left:6px}
@media (max-width:820px){.tb-tabs{overflow-x:auto;flex-wrap:nowrap}.tb-title{flex-direction:column;align-items:flex-start}}
'''
    open(sp, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH style.css: tables-head-v2 styles")
else:
    print("SKIP style.css: tables-head-v2 present")

dp = os.path.join(BASE, "web", "static", "css", "dark.css")
c = open(dp, encoding="utf-8").read()
if "tables-head-v2-dark" not in c:
    c = c.rstrip("\n") + '''
/* tables-head-v2-dark */
body.dark .tb-tabs{background:rgba(142,162,255,.08);border-color:#3a3f4b}
body.dark .tb-tab{color:#9aa3b2}
body.dark .tb-tab:hover{background:#23262e;color:#e7eaf0}
body.dark .tb-tab.on{background:#8ea2ff;color:#15171c}
body.dark .tb-tab.tswitch{border-color:#4a5060;color:#c4ccd8}
body.dark .tb-tab.tswitch:hover{background:#23262e}
'''
    open(dp, "w", encoding="utf-8", newline="\n").write(c)
    print("PATCH dark.css: tables-head-v2 dark styles")
else:
    print("SKIP dark.css: tables-head-v2-dark present")

hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.8" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.8", "release_date": "2026-11-18", "status": "released",
        "title": "Форма: аккуратная шапка таблицы",
        "notes": "Шапка вида «Форма» пересобрана: переключатель листа и вкладки таблиц стали единой лентой с подсветкой активной вкладки, заголовок таблицы и панель действий выстроены в одну строку (действия справа), режимы Строки/Корзина/История подсвечиваются как активные, опасное «Удалить таблицу» отделено от остальных кнопок и спрашивает подтверждение. Единые отступы и скругления в светлой и тёмной темах; на узких экранах лента вкладок прокручивается горизонтально вместо переносов вразнобой."})
    data["changelog"].insert(0, {"date": "2026-11-18", "author": "синхронизация документации", "change_type": "changed",
        "module": "tables", "ticket": "",
        "description": "Форма: шапка таблицы пересобрана в ленту вкладок + строку заголовка с группированными действиями; активные режимы подсвечены, опасное удаление отделено и с подтверждением; аккуратный вид в обеих темах и на мобильных."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.8")
else:
    print("SKIP history_seed.py: 0.13.8 present")

print("=" * 60)
print("MARKER_END: tables header beautified (0.13.8)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/templates/tables/view.html")
print("  web/static/css/style.css")
print("  web/static/css/dark.css")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")