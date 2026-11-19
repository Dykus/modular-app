# -*- coding: utf-8 -*-
import os, re, json, base64
d = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(d, "run.py")):
    p = os.path.dirname(d)
    if p == d: break
    d = p
BASE = d
print("ROOT: " + BASE)
def put(rel, content):
    p = os.path.join(BASE, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="\n").write(content)
    print("WRITE " + rel)
def append(rel, marker, block):
    p = os.path.join(BASE, *rel.split("/"))
    s = open(p, encoding="utf-8").read()
    if marker in s:
        print("SKIP " + rel + ": " + marker); return False
    open(p, "a", encoding="utf-8", newline="\n").write("\n\n" + block.strip("\n") + "\n")
    print("APPEND " + rel + ": " + marker); return True
def ins_before_endblock(rel, marker, block):
    p = os.path.join(BASE, *rel.split("/"))
    s = open(p, encoding="utf-8").read()
    if marker in s:
        print("SKIP " + rel + ": " + marker); return False
    idx = s.rfind("{% endblock %}")
    if idx == -1:
        print("WARN " + rel + ": {% endblock %} anchor not found"); return False
    open(p, "w", encoding="utf-8", newline="\n").write(s[:idx] + block.strip("\n") + "\n" + s[idx:])
    print("INSERT " + rel + ": " + marker + " before endblock"); return True

EXPORT_FMT = "modular-table-export/1"

# 1. routes.py: export + import_json GET/POST (append, suščestvuyušchie stroki netronuty).
append("modules/tables/routes.py", "texpimp-v1", r'''
# texpimp-v1: jeksport/v Import tablicy kak fajla (.json) meždu mašinami.
TABLE_EXPORT_FORMAT = "modular-table-export/1"

@tables_bp.route("/<int:tid>/export")
@perm("tables.view")
def table_export(tid):
    from flask import Response
    t = CustomTable.query.get_or_404(tid)
    m = user_access(tid, current_user)
    if not m["view"]:
        abort(403)
    cols = cols_of(tid)
    widths = {}
    try:
        from modules.tables.sheet_routes import ColWidth
        for w in ColWidth.query.filter_by(table_id=tid).all():
            if w.width_px and w.width_px > 0:
                widths[w.column_key] = int(w.width_px)
    except Exception:
        pass
    acc = []
    for r in Role.query.order_by(Role.name).all():
        ra = role_access(tid, r.id)
        if not (ra["view"] or ra["create"] or ra["delete"] or ra["edit"]):
            continue
        modes = [mo for mo in ("view", "create", "delete") if ra[mo]]
        acc.append({"role_name": r.name, "modes": modes, "edits": sorted(ra["edit"])})
    rows = []
    for r in TableRow.query.filter_by(table_id=tid).order_by(TableRow.id).all():
        rows.append({"id": r.id, "data": jload(r.data, {}), "created_by": r.created_by or "",
                     "deleted_at": r.deleted_at.isoformat() if r.deleted_at else None,
                     "deleted_by": r.deleted_by or ""})
    doc = {"format": TABLE_EXPORT_FORMAT,
           "table": {"key": t.key, "title": t.title, "counters": jload(t.counters, [])},
           "columns": [{"key": c.key, "title": c.title, "col_type": c.col_type, "grp": c.grp or "",
                        "options": jload(c.options, []), "formula": jload(c.formula, {}),
                        "order": c.order if c.order is not None else 0} for c in cols],
           "widths": widths, "access": acc, "rows": rows}
    body = json.dumps(doc, ensure_ascii=False, indent=1)
    fname = "%s_%s.json" % (re.sub(r"[^A-Za-z0-9_.-]", "_", t.key),
                            datetime.datetime.utcnow().strftime("%Y%m%d"))
    return Response(body, mimetype="application/json",
                    headers={"Content-Disposition": 'attachment; filename="%s"' % fname})

@tables_bp.route("/import-json", methods=["GET", "POST"])
@perm("tables.manage")
def import_json():
    """Ekran importa .json tablicy: svodka -> režim -> primenenie v odnoj tranzakcii."""
    def summarize(doc):
        fmt = str(doc.get("format") or "")
        tb = doc.get("table") or {}
        cols = doc.get("columns") or []
        rows = doc.get("rows") or []
        live = [r for r in rows if not r.get("deleted_at")]
        dead = [r for r in rows if r.get("deleted_at")]
        have, missing = [], []
        names = {r.name for r in Role.query.all()}
        for a in (doc.get("access") or []):
            rn = str(a.get("role_name") or "")
            if rn in names:
                have.append(rn)
            elif rn:
                missing.append(rn)
        conflict = None
        key = str(tb.get("key") or "").strip()
        if key and CustomTable.query.filter_by(key=key).first():
            conflict = key
        return {"fmt": fmt, "ok_fmt": fmt.startswith("modular-table-export/"),
                "key": key, "title": str(tb.get("title") or ""),
                "ncols": len(cols), "nlive": len(live), "ndead": len(dead),
                "nacc": len(doc.get("access") or []), "have_roles": have,
                "missing_roles": missing, "conflict": conflict}

    if request.method != "POST":
        return render_template("tables/import_table.html", step="pick", summ=None, done=None)

    # Shag 1: zagruzka fajla -> svodka.
    act = request.form.get("act") or "preview"
    if act == "preview":
        f = request.files.get("file")
        if f is None or not f.filename:
            flash("Выберите файл .json таблицы.")
            return redirect(url_for("tables.import_json"))
        try:
            doc = json.loads(f.stream.read().decode("utf-8"))
        except Exception as e:
            flash("Не удалось прочитать JSON: " + str(e)[:200])
            return redirect(url_for("tables.import_json"))
        summ = summarize(doc)
        if not summ["ok_fmt"]:
            flash("Файл не похож на экспорт таблицы (нет format modular-table-export/…).")
            return redirect(url_for("tables.import_json"))
        sess = dict(request.session) if hasattr(request, "session") else None
        try:
            request.session["texp_doc"] = json.dumps(doc, ensure_ascii=False)
        except Exception:
            flash("Файл слишком велик для предпросмотра в сессии — попробуйте таблицу меньшего размера.")
            return redirect(url_for("tables.import_json"))
        return render_template("tables/import_table.html", step="confirm", summ=summ, done=None)

    # Shag 2: primenenie.
    mode = request.form.get("mode") or "new"
    raw = None
    try:
        raw = request.session.pop("texp_doc", None)
    except Exception:
        raw = None
    if not raw:
        flash("Сессия истекла — загрузите файл заново.")
        return redirect(url_for("tables.import_json"))
    try:
        doc = json.loads(raw)
    except Exception as e:
        flash("Ошибка разбора сохранённого документа: " + str(e)[:200])
        return redirect(url_for("tables.import_json"))
    summ = summarize(doc)
    newkey = (request.form.get("newkey") or "").strip()
    target_key = newkey or summ["key"]
    if not target_key:
        flash("У таблицы нет ключа в файле — импорт невозможен.")
        return redirect(url_for("tables.import_json"))
    existing = CustomTable.query.filter_by(key=target_key).first()
    if mode == "new" and existing:
        flash("Ключ «%s» занят. Выберите «Обновить существующую», «Только структура» или задайте другой ключ." % target_key)
        try:
            request.session["texp_doc"] = raw
        except Exception:
            pass
        return render_template("tables/import_table.html", step="confirm", summ=summ, done=None)

    report = {"mode": mode, "cols_added": 0, "cols_updated": 0, "cols_removed": 0,
              "rows_created": 0, "rows_updated": 0, "trash_restored": 0,
              "roles_skipped": [], "backup": "", "errors": []}
    try:
        cols_doc = doc.get("columns") or []
        rows_doc = doc.get("rows") or []
        acc_doc = doc.get("access") or []
        wid_doc = doc.get("widths") or {}
        ctr_doc = (doc.get("table") or {}).get("counters") or []
        role_by_name = {r.name: r for r in Role.query.all()}

        if mode == "new":
            mx = db.session.query(db.func.max(CustomTable.order)).scalar() or 0
            t = CustomTable(key=target_key, title=str((doc.get("table") or {}).get("title") or target_key),
                            order=mx + 1, created_by=who() + " (импорт)")
            db.session.add(t); db.session.flush()
            report["backup"] = "(новая таблица — резервная копия не требуется)"
        else:
            t = existing
            bdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(file)))),
                                "data", "backups")
            os.makedirs(bdir, exist_ok=True)
            stamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            bpath = os.path.join(bdir, "pre_import_%s_%s.json" % (target_key, stamp))
            with open(bpath, "w", encoding="utf-8") as bf:
                cur_cols = [{"key": c.key, "title": c.title, "col_type": c.col_type, "grp": c.grp or "",
                             "options": jload(c.options, []), "formula": jload(c.formula, {}),
                             "order": c.order if c.order is not None else 0} for c in cols_of(t.id)]
                cur_rows = [{"id": r.id, "data": jload(r.data, {}), "created_by": r.created_by or "",
                             "deleted_at": r.deleted_at.isoformat() if r.deleted_at else None,
                             "deleted_by": r.deleted_by or ""}
                            for r in TableRow.query.filter_by(table_id=t.id).all()]
                json.dump({"reason": "pre-import", "table": {"key": t.key, "title": t.title,
                         "counters": jload(t.counters, [])}, "columns": cur_cols, "rows": cur_rows},
                          bf, ensure_ascii=False, indent=1)
            report["backup"] = "data/backups/" + os.path.basename(bpath)

        # Kolonki.
        if mode == "new":
            for cd in cols_doc:
                db.session.add(TableColumn(table_id=t.id, key=str(cd.get("key")), title=str(cd.get("title") or cd.get("key")),
                                           col_type=str(cd.get("col_type") or "text"), grp=str(cd.get("grp") or ""),
                                           options=json.dumps(cd.get("options") or [], ensure_ascii=False),
                                           formula=json.dumps(cd.get("formula") or {}, ensure_ascii=False),
                                           order=int(cd.get("order") or 0)))
                report["cols_added"] += 1
            db.session.flush()
        else:
            cur = {c.key: c for c in cols_of(t.id)}
            wanted = {str(cd.get("key")): cd for cd in cols_doc}
            for k, cd in wanted.items():
                c = cur.get(k)
                if c is None:
                    db.session.add(TableColumn(table_id=t.id, key=k, title=str(cd.get("title") or k),
                                               col_type=str(cd.get("col_type") or "text"), grp=str(cd.get("grp") or ""),
                                               options=json.dumps(cd.get("options") or [], ensure_ascii=False),
                                               formula=json.dumps(cd.get("formula") or {}, ensure_ascii=False),
                                               order=int(cd.get("order") or 0)))
                    report["cols_added"] += 1
                else:
                    c.title = str(cd.get("title") or c.title); c.col_type = str(cd.get("col_type") or c.col_type)
                    c.grp = str(cd.get("grp") or ""); c.options = json.dumps(cd.get("options") or [], ensure_ascii=False)
                    c.formula = json.dumps(cd.get("formula") or {}, ensure_ascii=False)
                    c.order = int(cd.get("order") or c.order or 0)
                    report["cols_updated"] += 1
            for k, c in cur.items():
                if k not in wanted:
                    db.session.delete(c); report["cols_removed"] += 1
            db.session.flush()

        # Stroki (ne pri "structure only").
        if mode != "structure":
            cur_ids = {r.id for r in TableRow.query.filter_by(table_id=t.id).all()}
            for rd in rows_doc:
                rid = rd.get("id")
                dat = json.dumps(rd.get("data") or {}, ensure_ascii=False)
                cb = str(rd.get("created_by") or "")
                da = rd.get("deleted_at")
                dbt = datetime.datetime.fromisoformat(da) if da else None
                if rid in cur_ids:
                    row = TableRow.query.get(rid)
                    if row is not None and row.table_id == t.id:
                        row.data = dat
                        row.updated_at = datetime.datetime.utcnow()
                        if dbt is not None:
                            row.deleted_at = dbt; row.deleted_by = str(rd.get("deleted_by") or "")
                            report["trash_restored"] += 1
                        report["rows_updated"] += 1
                else:
                    nr = TableRow(table_id=t.id, data=dat, created_by=cb,
                                  updated_at=datetime.datetime.utcnow(),
                                  deleted_at=dbt, deleted_by=str(rd.get("deleted_by") or ""))
                    db.session.add(nr); db.session.flush()
                    if dbt is not None:
                        report["trash_restored"] += 1
                    report["rows_created"] += 1

        # Širina.
        try:
            from modules.tables.sheet_routes import ColWidth
            for k, px in (wid_doc or {}).items():
                try:
                    pv = int(px)
                except Exception:
                    pv = 0
                if pv <= 0:
                    continue
                cw = ColWidth.query.filter_by(table_id=t.id, column_key=str(k)).first()
                if cw is None:
                    db.session.add(ColWidth(table_id=t.id, column_key=str(k), width_pv=pv))
                else:
                    cw.width_px = pv
        except Exception as e:
            report["errors"].append("ширина: " + str(e)[:120])

        # Dostup po imeni roli.
        TableAccess.query.filter_by(table_id=t.id).delete()
        for a in acc_doc:
            rn = str(a.get("role_name") or "")
            r = role_by_name.get(rn)
            if r is None:
                if rn:
                    report["roles_skipped"].append(rn)
                continue
            for mo in (a.get("modes") or []):
                if mo in ("view", "create", "delete"):
                    db.session.add(TableAccess(table_id=t.id, role_id=r.id, column_key="", mode=mo))
            for ek in (a.get("edits") or []):
                db.session.add(TableAccess(table_id=t.id, role_id=r.id, column_key=str(ek), mode="edit"))

        t.counters = json.dumps(ctr_doc, ensure_ascii=False)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        report["errors"].append(str(e)[:300])
        flash("Импорт отменён (rollback), база не изменена: " + str(e)[:200])
        return redirect(url_for("tables.import_json"))

    return render_template("tables/import_table.html", step="done", summ=summ, done=report)
''')

# 2. sheet_routes.py: nichego novogo ne nuzhno (ColWidth uzhe est iz 0.13.27).
#     No esli 0.13.27 ne došel — export vse ravno rabotaet (try/except okolo ColWidth).

# 3. import_table.html: ekran tri šaga (vybrat' -> svodka/režim -> itog).
put("modules/tables/templates/tables/import_table.html", r'''{% extends "base.html" %}
{% block title %}Импорт таблицы (.json){% endblock %}
{% block content %}
<h2>📤 Импорт таблицы (.json)</h2>
<p class="note">Перенос готовой таблицы между машинами одним файлом: колонки с типами, группами и формулами, права (по имени роли), счётчики, ширина и строки, включая корзину.</p>

{% if step == "pick" %}
<form method="post" enctype="multipart/form-data" action="{{ url_for('tables.import_json') }}">
  <input type="hidden" name="act" value="preview">
  <div class="form-row"><label>Файл экспорта (.json)</label><input type="file" name="file" accept=".json,application/json" required></div>
  <button class="btn" type="submit">Показать сводку</button>
</form>
<p class="note">Экспорт делается кнопкой «⬇ Экспорт (.json)» в шапке формы или листа нужной таблицы.</p>

{% elif step == "confirm" %}
<div class="card" style="margin-bottom:12px">
  <h3>{{ summ.title }} <code>{{ summ.key }}</code></h3>
  <p>Колонок: <b>{{ summ.ncols }}</b> · строк живых: <b>{{ summ.nlive }}</b> · в корзине: <b>{{ summ.ndead }}</b> · правил доступа: <b>{{ summ.nacc }}</b></p>
  <p>Роли на этой машине: {{ summ.have_roles|join(', ') or '—' }}
     {% if summ.missing_roles %}<span style="color:#c0392b"> · отсутствуют: {{ summ.missing_roles|join(', ') }} (их права будут пропущены)</span>{% endif %}</p>
  {% if summ.conflict %}<p style="color:#e8930c;font-weight:700">Ключ «{{ summ.conflict }}» уже занят на этой машине.</p>{% endif %}
</div>
<form method="post" action="{{ url_for('tables.import_json') }}">
  <input type="hidden" name="act" value="apply">
  <div class="form-row">
    <label><input type="radio" name="mode" value="new" {% if not summ.conflict %}checked{% endif %}> Создать новую копию</label>
    <label><input type="radio" name="mode" value="update" {% if summ.conflict %}checked{% endif %}> Обновить существующую (колонки догоняются, строки по id, доступ и счётчики перезаписываются)</label>
    <label><input type="radio" name="mode" value="structure"> Только структура (колонки/права/счётчики/ширина — да, строки — нет)</label>
  </div>
  <div class="form-row"><label>Новый ключ (если «Создать новую» и ключ занят; латиницей, без пробелов)</label>
    <input type="text" name="newkey" placeholder="{{ summ.key }}-copy"></div>
  <p class="note">Перед «Обновить» и «Только структура» автоматически пишется резервная копия в <code>data/backups/</code>. Импорт выполняется одной транзакцией: ошибка на середине — откат, база не меняется.</p>
  <button class="btn" type="submit" onclick="return confirm('Импортировать эту таблицу?');">Применить импорт</button>
  <a class="btn gray" href="{{ url_for('tables.import_json') }}">Отмена</a>
</form>

{% elif step == "done" %}
<div class="card" style="border-left:4px solid #2f9e44">
  <h3>Импорт завершён (режим: {{ done.mode }})</h3>
  <p>Колонок добавлено: <b>{{ done.cols_added }}</b> · обновлено: <b>{{ done.cols_updated }}</b> · удалено: <b>{{ done.cols_removed }}</b></p>
  <p>Строк создано: <b>{{ done.rows_created }}</b> · обновлено: <b>{{ done.rows_updated }}</b> · восстановлено в корзину: <b>{{ done.trash_restored }}</b></p>
  {% if done.roles_skipped %}<p style="color:#e8930c">Пропущены роли (нет на этой машине): {{ done.roles_skipped|join(', ') }}</p>{% endif %}
  <p>Резервная копия: <code>{{ done.backup }}</code></p>
  {% if done.errors %}<p style="color:#c0392b;font-weight:700">Замечания: {{ done.errors|join('; ') }}</p>{% endif %}
  <a class="btn" href="{{ url_for('tables.index') }}">К списку таблиц</a>
  <a class="btn gray" href="{{ url_for('tables.import_json') }}">Импортировать ещё</a>
</div>
{% endif %}
{% endblock %}''')

# 4. Knopka eksporta v forme (tb-acts, pered form udalenija) i v liste (shacts).
ins_before_endblock("modules/tables/templates/tables/view.html", "texp-btn-v1", '')
vp = os.path.join(BASE, "modules", "tables", "templates", "tables", "view.html")
s = open(vp, encoding="utf-8").read()
if "texp-btn-v1" not in s:
    EXP_FORM = ('<a class="btn gray" href="{{ url_for(\'tables.table_export\', tid=t.id) }}" '
                'onclick="this.setAttribute(\'data-texp\',\'1\')">⬇ Экспорт (.json)</a> <!-- texp-btn-v1 -->')
    anchor_form = '<form method="post" action="{{ url_for(\'tables.table_delete\', tid=t.id) }}" class="tb-danger"'
    if anchor_form in s:
        s = s.replace(anchor_form, EXP_FORM + "\n" + anchor_form, 1)
        open(vp, "w", encoding="utf-8", newline="\n").write(s)
        print("PATCH view.html: export button inserted before delete form")
    else:
        print("WARN view.html: delete-form anchor not found (export button skipped)")
else:
    print("SKIP view.html: export button present")

sp = os.path.join(BASE, "modules", "tables", "templates", "tables", "sheet.html")
s = open(sp, encoding="utf-8").read()
if "texp-btn-sheet-v1" not in s:
    EXP_SHEET = ('<a class="btn gray" href="{{ url_for(\'tables.table_export\', tid=payload.tid) }}">⬇ Экспорт (.json)</a> <!-- texp-btn-sheet-v1 -->')
    m = re.search(r'(<button class="btn gray" id="shcsv">)', s)
    if m:
        s = s[:m.start(1)] + EXP_SHEET + "\n      " + s[m.start(1):]
        open(sp, "w", encoding="utf-8", newline="\n").write(s)
        print("PATCH sheet.html: export button inserted near CSV")
    else:
        print("WARN sheet.html: shcsv anchor not found (export button skipped)")
else:
    print("SKIP sheet.html: export button present")

# 5. Knopka «Import tablicy» v obshem spiske tablic (index.html).
ip = os.path.join(BASE, "modules", "tables", "templates", "tables", "index.html")
s = open(ip, encoding="utf-8").read()
if "texp-index-v1" not in s:
    IDXBTN = ('<a class="btn gray" href="{{ url_for(\'tables.import_json\') }}">📤 Импорт таблицы (.json)</a> <!-- texp-index-v1 -->')
    m = re.search(r'(<h2>|<div class="stats">)', s)
    if m:
        s = s[:m.start(1)] + IDXBTN + "\n" + s[m.start(1):]
        open(ip, "w", encoding="utf-8", newline="\n").write(s)
        print("PATCH index.html: import-table button added")
    else:
        print("WARN index.html: h2/stats anchor not found")
else:
    print("SKIP index.html: import button present")

# 6. history_seed: reliz 0.13.29.
hp = os.path.join(BASE, "modules", "versions", "history_seed.py")
v = open(hp, encoding="utf-8").read()
m = re.search(r'_B64\s*=\s*"([^"]*)"', v)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
if not any(r.get("version") == "0.13.29" for r in data["releases"]):
    data["releases"].insert(0, {"version": "0.13.29", "release_date": "2026-11-19", "status": "released",
        "title": "Экспорт и импорт таблицы как файла (.json) между машинами",
        "notes": "Готовую таблицу теперь можно перенести между разными экземплярами программы (Windows/Linux) одним файлом: кнопка «⬇ Экспорт (.json)» в шапке формы и листа отдаёт полный снимок — колонки с типами, группами, вариантами списков и формулами, ширину колонок, матрицу доступа (по имени роли), счётчики и все строки, включая находящиеся в корзине. Новая страница «📤 Импорт таблицы (.json)» в списке таблиц показывает сводку файла (сколько колонок/строк, какие роли есть на этой машине и каких нет, конфликт ключа) и три режима: создать новую копию, обновить существующую (колонки догоняются по ключу, строки совпадают по id, доступ и счётчики перезаписываются) или только структура (без строк). Перед обновлением автоматически пишется резервная копия pre_import_… в data/backups/, импорт выполняется одной транзакцией с откатом при ошибке, отсутствующие роли честно помечаются в отчёте. Импорт доступен роли tables.manage, экспорт — любой, кто видит таблицу. Существующие маршруты не изменялись: код добавлен дописыванием в конец файлов и вставкой перед endblock в шаблонах."})
    data["changelog"].insert(0, {"date": "2026-11-19", "author": "синхронизация документации", "change_type": "added",
        "module": "tables", "ticket": "",
        "description": "Экспорт/импорт таблицы как .json-файла: полный снимок структуры, ширины, доступа, счётчиков и строк (включая корзину); экран импорта со сводкой и тремя режимами (новая/обновить/только структура), авто-backup перед обновлением, транзакционный импорт с откатом, маппинг ролей по имени."})
    nb = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    v = v[:m.start(1)] + nb + v[m.end(1):]
    open(hp, "w", encoding="utf-8", newline="\n").write(v)
    print("PATCH history_seed.py: release 0.13.29")
else:
    print("SKIP history_seed.py: 0.13.29 present")

print("=" * 60)
print("MARKER_END: table export/import as .json file (0.13.29)")
print("=" * 60)
print("Commit + Push:")
print("  modules/tables/routes.py                  (append texpimp-v1)")
print("  modules/tables/templates/tables/import_table.html  (novyj fil)")
print("  modules/tables/templates/tables/view.html          (knopka eksporta)")
print("  modules/tables/templates/tables/sheet.html         (knopka eksporta)")
print("  modules/tables/templates/tables/index.html         (knopka importa)")
print("  modules/versions/history_seed.py")
print("  tools/installers/install.py")