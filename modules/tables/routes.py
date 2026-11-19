from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from core.app import db
from core.auth import perm
from core.models import Role
from modules.tables.models import CustomTable, TableColumn, TableRow, TableAccess, CellLog
from modules.tables.service import (jload, num, compute_value, user_access, role_access,
                                    can_edit_col, calc_counters, TRASH_DAYS)
import json, os, datetime, re

TYPE_LABELS = {
    "text": "Текст",
    "number": "Число",
    "date": "Дата",
    "list": "Список",
    "computed": "Вычисляемая (формула)",
    "ref": "Ссылка на другую таблицу",
}
TYPE_CHOICES = list(TYPE_LABELS.items())

tables_bp = Blueprint("tables", __name__, url_prefix="/tables", template_folder="templates")

def who():
    return current_user.display_name if current_user.is_authenticated else "аноним"

def cols_of(tid):
    return TableColumn.query.filter_by(table_id=tid).order_by(TableColumn.order, TableColumn.id).all()

def visible_tables():
    out = []
    for t in CustomTable.query.order_by(CustomTable.order, CustomTable.id).all():
        if user_access(t.id, current_user)["view"]:
            out.append(t)
    return out

@tables_bp.route("/")
@perm("tables.view")
def index():
    return render_template("tables/index.html", tables=visible_tables())

@tables_bp.route("/new", methods=["POST"])
@perm("tables.manage")
def table_new():
    title = (request.form.get("title") or "").strip()
    key = (request.form.get("key") or "").strip()
    if not title or not key:
        flash("Укажите название и ключ таблицы (ключ — латиницей, без пробелов).")
        return redirect(url_for("tables.index"))
    if CustomTable.query.filter_by(key=key).first():
        flash("Таблица с таким ключом уже есть.")
        return redirect(url_for("tables.index"))
    mx = db.session.query(db.func.max(CustomTable.order)).scalar() or 0
    t = CustomTable(key=key, title=title, order=mx + 1, created_by=who())
    db.session.add(t); db.session.commit()
    flash("Таблица создана. Добавьте колонки и настройте доступ.")
    return redirect(url_for("tables.cols", tid=t.id))

@tables_bp.route("/<int:tid>/delete", methods=["POST"])
@perm("tables.manage")
def table_delete(tid):
    t = CustomTable.query.get_or_404(tid)
    backup = {
        "table": {"key": t.key, "title": t.title, "counters": jload(t.counters, [])},
        "columns": [{"key": c.key, "title": c.title, "col_type": c.col_type, "grp": c.grp,
                     "options": jload(c.options, []), "formula": jload(c.formula, {})} for c in cols_of(tid)],
        "rows": [jload(r.data, {}) for r in TableRow.query.filter_by(table_id=tid).all()],
    }
    bdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "backups")
    os.makedirs(bdir, exist_ok=True)
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bpath = os.path.join(bdir, "table_%s_%s.json" % (t.key, stamp))
    with open(bpath, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=1)
    TableRow.query.filter_by(table_id=tid).delete()
    TableColumn.query.filter_by(table_id=tid).delete()
    TableAccess.query.filter_by(table_id=tid).delete()
    CellLog.query.filter_by(table_id=tid).delete()
    db.session.delete(t); db.session.commit()
    flash("Таблица удалена. Резервная копия: data/backups/" + os.path.basename(bpath))
    return redirect(url_for("tables.index"))

@tables_bp.route("/<int:tid>")
@perm("tables.view")
def view(tid):
    t = CustomTable.query.get_or_404(tid)
    m = user_access(tid, current_user)
    if not m["view"]:
        abort(403)
    mode = request.args.get("mode", "rows")
    cols = cols_of(tid)
    if mode == "trash":
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=TRASH_DAYS)
        for old in TableRow.query.filter(TableRow.table_id == tid,
                                         TableRow.deleted_at.isnot(None),
                                         TableRow.deleted_at < cutoff).all():
            db.session.delete(old)
        db.session.commit()
        rows = TableRow.query.filter(TableRow.table_id == tid,
                                     TableRow.deleted_at.isnot(None)).order_by(TableRow.deleted_at.desc()).all()
    else:
        rows = TableRow.query.filter(TableRow.table_id == tid,
                                     TableRow.deleted_at.is_(None)).order_by(TableRow.id.desc()).all()
    cache = {}
    def remote(rt):
        if rt not in cache:
            cache[rt] = [jload(r.data, {}) for r in TableRow.query.filter_by(table_id=rt, deleted_at=None).all()]
        return cache[rt]
    disp = []
    for r in rows:
        d = jload(r.data, {})
        cells = {}
        for c in cols:
            cells[c.key] = compute_value(c, d, remote) if c.col_type in ("computed", "ref") else d.get(c.key, "")
        disp.append({"row": r, "cells": cells})
    datas = [jload(r.data, {}) for r in rows if r.deleted_at is None] if mode != "trash" else []
    logs = None
    if mode == "history":
        logs = CellLog.query.filter_by(table_id=tid).order_by(CellLog.ts.desc()).limit(300).all()
    trash_count = TableRow.query.filter(TableRow.table_id == tid, TableRow.deleted_at.isnot(None)).count()
    return render_template("tables/view.html", t=t, m=m, cols=cols, disp=disp, mode=mode,
                           counters=calc_counters(t, datas), logs=logs, tabs=visible_tables(),
                           trash_count=trash_count, can_edit_col=can_edit_col, trash_days=TRASH_DAYS)

@tables_bp.route("/<int:tid>/import", methods=["GET", "POST"])
@perm("tables.view")
def import_xlsx(tid):
    """Import .xlsx: sopostavlenie kolonok po zagolovkam, avtosozdanie nedostayushchih."""
    t = CustomTable.query.get_or_404(tid)
    m = user_access(tid, current_user)
    if not (m["create"] or m["edit"] is None):
        flash("Нет права создавать строки в этой таблице — импорт недоступен.")
        return redirect(url_for("tables.view", tid=tid))
    if request.method == "POST":
        f = request.files.get("file")
        if f is None or not f.filename:
            flash("Выберите файл .xlsx")
            return redirect(url_for("tables.import_xlsx", tid=tid))
        try:
            import openpyxl
            wb = openpyxl.load_workbook(f.stream, data_only=True, read_only=True)
        except Exception as e:
            flash("Не удалось прочитать файл: " + str(e)[:200])
            return redirect(url_for("tables.import_xlsx", tid=tid))
        sheet_name = (request.form.get("sheet") or "").strip()
        if sheet_name and sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
        else:
            ws = wb[wb.sheetnames[0]]
        try:
            header_row = max(1, int(request.form.get("header_row") or 1))
        except Exception:
            header_row = 1
        make_cols = bool(request.form.get("make_cols"))
        allrows = list(ws.iter_rows(values_only=True))
        used_sheet = ws.title
        wb.close()
        if len(allrows) < header_row:
            flash("В листе «" + used_sheet + "» нет строк.")
            return redirect(url_for("tables.import_xlsx", tid=tid))
        headers = [str(x).strip() if x is not None else "" for x in allrows[header_row - 1]]
        cols = cols_of(tid)
        by_title = {c.title.strip().lower(): c for c in cols}
        created_cols = 0
        mapping = []
        for i, h in enumerate(headers):
            if not h:
                continue
            c = by_title.get(h.lower())
            if c is None and make_cols:
                keys = {c2.key for c2 in cols}
                key = "col%d" % (i + 1)
                while key in keys:
                    key += "x"
                mx = db.session.query(db.func.max(TableColumn.order)).filter_by(table_id=tid).scalar() or 0
                c = TableColumn(table_id=tid, key=key, title=h, col_type="text", order=mx + 1)
                db.session.add(c); db.session.flush()
                cols.append(c); by_title[h.lower()] = c
                created_cols += 1
            if c is not None:
                mapping.append((i, c.key))
        db.session.commit()
        added = 0
        for r in allrows[header_row:]:
            if all((x is None or str(x).strip() == "") for x in r):
                continue
            data = {}
            for i, key in mapping:
                v = r[i] if i < len(r) else None
                if v is None:
                    data[key] = ""
                elif isinstance(v, (datetime.datetime, datetime.date)):
                    data[key] = v.strftime("%d.%m.%Y")
                else:
                    data[key] = str(v).strip()
            row = TableRow(table_id=tid, data=json.dumps(data, ensure_ascii=False),
                           created_by=who() + " (импорт)")
            db.session.add(row); db.session.flush()
            db.session.add(CellLog(table_id=tid, row_id=row.id, column_key="*",
                                   old_value="", new_value="строка создана импортом Excel",
                                   who=who()))
            added += 1
        db.session.commit()
        flash("Импорт завершён (лист «" + used_sheet + "»): строк добавлено " + str(added) + ", колонок создано " + str(created_cols) + ".")
        return redirect(url_for("tables.view", tid=tid))
    return render_template("tables/import.html", t=t)

@tables_bp.route("/<int:tid>/row/<rid>")
@perm("tables.view")
def row_edit(tid, rid):
    t = CustomTable.query.get_or_404(tid)
    m = user_access(tid, current_user)
    if not m["view"]:
        abort(403)
    row = None if rid == "new" else TableRow.query.get_or_404(int(rid))
    if row is None and not m["create"]:
        flash("Нет права создавать строки в этой таблице.")
        return redirect(url_for("tables.view", tid=tid))
    data = jload(row.data, {}) if row else {}
    cols = cols_of(tid)
    opts = {c.id: jload(c.options, []) for c in cols}
    return render_template("tables/row_edit.html", t=t, row=row, data=data, cols=cols,
                           m=m, opts=opts, can_edit_col=can_edit_col)

@tables_bp.route("/<int:tid>/row/save", methods=["POST"])
@perm("tables.view")
def row_save(tid):
    t = CustomTable.query.get_or_404(tid)
    m = user_access(tid, current_user)
    if not m["view"]:
        abort(403)
    rid = request.form.get("id", type=int)
    row = TableRow.query.get(rid) if rid else None
    if row is None:
        if not m["create"]:
            flash("Нет права создавать строки.")
            return redirect(url_for("tables.view", tid=tid))
        row = TableRow(table_id=tid, data="{}", created_by=who())
        db.session.add(row); db.session.flush()
        data = {}
    else:
        data = jload(row.data, {})
    for c in cols_of(tid):
        if c.col_type in ("computed", "ref"):
            continue
        if not can_edit_col(m, c.key):
            continue
        nv = request.form.get("f_" + c.key, "")
        ov = str(data.get(c.key, "") or "")
        if nv != ov:
            data[c.key] = nv
            db.session.add(CellLog(table_id=tid, row_id=row.id, column_key=c.key,
                                   old_value=ov, new_value=nv, who=who()))
    row.data = json.dumps(data, ensure_ascii=False)
    row.updated_at = datetime.datetime.utcnow()
    db.session.commit()
    flash("Строка сохранена.")
    return redirect(url_for("tables.view", tid=tid))

@tables_bp.route("/<int:tid>/row/<int:rid>/delete", methods=["POST"])
@perm("tables.view")
def row_delete(tid, rid):
    m = user_access(tid, current_user)
    if not (m["delete"] or m["edit"] is None):
        flash("Нет права удалять строки в этой таблице.")
        return redirect(url_for("tables.view", tid=tid))
    row = TableRow.query.get_or_404(rid)
    row.deleted_at = datetime.datetime.utcnow()
    row.deleted_by = who()
    db.session.commit()
    flash("Строка перемещена в корзину (хранится %d дней)." % TRASH_DAYS)
    return redirect(url_for("tables.view", tid=tid))

@tables_bp.route("/<int:tid>/row/<int:rid>/restore", methods=["POST"])
@perm("tables.view")
def row_restore(tid, rid):
    m = user_access(tid, current_user)
    if not (m["create"] or m["edit"] is None):
        flash("Нет права восстанавливать строки.")
        return redirect(url_for("tables.view", tid=tid, mode="trash"))
    row = TableRow.query.get_or_404(rid)
    row.deleted_at = None; row.deleted_by = ""
    db.session.commit()
    flash("Строка восстановлена.")
    return redirect(url_for("tables.view", tid=tid, mode="trash"))

@tables_bp.route("/<int:tid>/row/<int:rid>/purge", methods=["POST"])
@perm("tables.view")
def row_purge(tid, rid):
    m = user_access(tid, current_user)
    if not (m["delete"] or m["edit"] is None):
        flash("Нет права удалять навсегда.")
        return redirect(url_for("tables.view", tid=tid, mode="trash"))
    row = TableRow.query.get_or_404(rid)
    db.session.delete(row); db.session.commit()
    flash("Строка удалена навсегда.")
    return redirect(url_for("tables.view", tid=tid, mode="trash"))

@tables_bp.route("/<int:tid>/cols")
@perm("tables.manage")
def cols(tid):
    t = CustomTable.query.get_or_404(tid)
    col = None
    cid = request.args.get("cid", type=int)
    if cid:
        col = TableColumn.query.get_or_404(cid)
    f = jload(col.formula, {}) if col else {}
    opt_text = ", ".join(jload(col.options, [])) if col else ""
    all_tables = CustomTable.query.order_by(CustomTable.order, CustomTable.id).all()
    lines = []
    for c in jload(t.counters, []):
        lines.append("|".join([c.get("title", ""), c.get("func", "sum"), c.get("col", ""),
                               c.get("wcol", ""), c.get("wval", "")]))
    return render_template("tables/cols.html", t=t, cols=cols_of(tid), col=col, f=f,
                           opt_text=opt_text, all_tables=all_tables,
                           counters_text="\n".join(lines),
                           TYPE_LABELS=TYPE_LABELS, TYPE_CHOICES=TYPE_CHOICES)

@tables_bp.route("/<int:tid>/col/save", methods=["POST"])
@perm("tables.manage")
def col_save(tid):
    t = CustomTable.query.get_or_404(tid)
    cid = request.form.get("id", type=int)
    col = TableColumn.query.get(cid) if cid else None
    title = (request.form.get("title") or "").strip()
    key = (request.form.get("key") or "").strip()
    ctype = request.form.get("col_type") or "text"
    if not title or not key:
        flash("Укажите название и ключ колонки.")
        return redirect(url_for("tables.cols", tid=tid))
    dup = TableColumn.query.filter(TableColumn.table_id == tid, TableColumn.key == key)
    if col:
        dup = dup.filter(TableColumn.id != col.id)
    if dup.first():
        flash("Колонка с таким ключом уже есть в этой таблице.")
        return redirect(url_for("tables.cols", tid=tid))
    formula = {}
    if ctype == "computed":
        kind = request.form.get("kind") or "arith"
        formula = {"kind": kind, "op": request.form.get("op"), "a": request.form.get("a"),
                   "b": request.form.get("b"), "col": request.form.get("if_col"),
                   "if_op": request.form.get("if_op"), "value": request.form.get("if_val"),
                   "then": request.form.get("then_v"), "else": request.form.get("else_v")}
    if ctype == "ref":
        formula = {"kind": "ref", "ref_table": int(request.form.get("ref_table") or 0),
                   "match_local": request.form.get("match_local"),
                   "match_remote": request.form.get("match_remote"),
                   "show": request.form.get("show")}
    if col is None:
        mx = db.session.query(db.func.max(TableColumn.order)).filter_by(table_id=tid).scalar() or 0
        col = TableColumn(table_id=tid, key=key, order=mx + 1)
        db.session.add(col)
    col.title = title; col.col_type = ctype
    col.grp = (request.form.get("grp") or "").strip()
    if ctype == "list":
        parts = [x.strip() for x in (request.form.get("options") or "").split(",") if x.strip()]
        col.options = json.dumps(parts, ensure_ascii=False)
    col.formula = json.dumps(formula, ensure_ascii=False)
    db.session.commit()
    if ctype in ("computed", "ref"):
        first = TableRow.query.filter_by(table_id=tid, deleted_at=None).first()
        if first:
            cache = {}
            def remote(rt):
                if rt not in cache:
                    cache[rt] = [jload(r.data, {}) for r in TableRow.query.filter_by(table_id=rt, deleted_at=None).all()]
                return cache[rt]
            sample = compute_value(col, jload(first.data, {}), remote)
            flash("Колонка сохранена. Пример на первой строке: «%s»" % (sample or "пусто"))
        else:
            flash("Колонка сохранена. Пример появится, когда добавите первую строку.")
    else:
        flash("Колонка сохранена.")
    return redirect(url_for("tables.cols", tid=tid))

@tables_bp.route("/<int:tid>/col/delete", methods=["POST"])
@perm("tables.manage")
def col_delete(tid):
    cid = request.form.get("id", type=int)
    col = TableColumn.query.get_or_404(cid)
    db.session.delete(col); db.session.commit()
    flash("Колонка удалена. Значения в строках остались в данных, но не показываются.")
    return redirect(url_for("tables.cols", tid=tid))

@tables_bp.route("/<int:tid>/counters", methods=["POST"])
@perm("tables.manage")
def counters_save(tid):
    t = CustomTable.query.get_or_404(tid)
    out = []
    for line in (request.form.get("counters") or "").splitlines():
        p = [x.strip() for x in line.split("|")]
        if len(p) >= 3 and p[0] and p[2]:
            out.append({"title": p[0], "func": p[1] or "sum", "col": p[2],
                        "wcol": p[3] if len(p) > 3 else "", "wval": p[4] if len(p) > 4 else ""})
    t.counters = json.dumps(out, ensure_ascii=False)
    db.session.commit()
    flash("Счётчики сохранены: %d шт." % len(out))
    return redirect(url_for("tables.cols", tid=tid))

@tables_bp.route("/<int:tid>/access", methods=["GET", "POST"])
@perm("tables.manage")
def access(tid):
    t = CustomTable.query.get_or_404(tid)
    cols = cols_of(tid)
    roles = Role.query.order_by(Role.name).all()
    if request.method == "POST":
        TableAccess.query.filter_by(table_id=tid).delete()
        for r in roles:
            pre = "r%d_" % r.id
            for mode in ("view", "create", "delete"):
                if request.form.get(pre + mode):
                    db.session.add(TableAccess(table_id=tid, role_id=r.id, column_key="*", mode=mode))
            for c in cols:
                if request.form.get(pre + "e_" + c.key):
                    db.session.add(TableAccess(table_id=tid, role_id=r.id, column_key=c.key, mode="edit"))
        db.session.commit()
        flash("Матрица доступа сохранена.")
        return redirect(url_for("tables.access", tid=tid))
    maps = {r.id: role_access(tid, r.id) for r in roles}
    return render_template("tables/access.html", t=t, cols=cols, roles=roles, maps=maps)

from modules.tables import sheet_routes  # sheet-link


# colmove-v1: perestanovka kolonok vverh/vniz (order uzhe est v modeli).
@tables_bp.route("/<int:tid>/col/move", methods=["POST"])
@perm("tables.manage")
def col_move(tid):
    from flask import jsonify
    j = request.get_json(force=True)
    cid = int(j.get("cid") or 0)
    direction = 1 if str(j.get("dir")) in ("down", "1", "1.0") else -1
    cols = cols_of(tid)
    idx = -1
    for i, c in enumerate(cols):
        if c.id == cid:
            idx = i; break
    if idx < 0:
        return jsonify({"ok": False, "err": "notfound"}), 404
    tgt = idx + direction
    if tgt < 0 or tgt >= len(cols):
        return jsonify({"ok": True, "moved": False})
    a, b = cols[idx], cols[tgt]
    oa = a.order if a.order is not None else 0
    ob = b.order if b.order is not None else 0
    if oa == ob:
        oa, ob = idx, tgt
    a.order, b.order = ob, oa
    db.session.commit()
    return jsonify({"ok": True, "moved": True})


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
