from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from core.app import db
from core.auth import perm
from core.models import Role
from modules.tables.models import CustomTable, TableColumn, TableRow, TableAccess, CellLog
from modules.tables.service import (jload, num, compute_value, user_access, role_access,
                                    can_edit_col, calc_counters, TRASH_DAYS)
import json, os, datetime

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
    all_tables = CustomTable.query.order_by(CustomTable.order, CustomTable.id).all()
    lines = []
    for c in jload(t.counters, []):
        lines.append("|".join([c.get("title", ""), c.get("func", "sum"), c.get("col", ""),
                               c.get("wcol", ""), c.get("wval", "")]))
    return render_template("tables/cols.html", t=t, cols=cols_of(tid), col=col,
                           all_tables=all_tables, counters_text="\n".join(lines))

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
