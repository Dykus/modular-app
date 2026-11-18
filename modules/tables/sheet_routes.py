# Excel-vid ("List") poverh konstructora: te zhe prava, istoriya, dannye.
import json, datetime
from flask import request, jsonify, render_template, redirect, url_for, flash, abort
from flask_login import current_user
from sqlalchemy import text
from core.app import db
from core.auth import perm
from modules.tables.routes import tables_bp, cols_of, who
from modules.tables.models import CustomTable, TableRow, TableAccess, CellLog
from modules.tables.service import (jload, compute_value, user_access, can_edit_col,
                                    calc_counters, TRASH_DAYS)

class SheetView(db.Model):
    __tablename__ = "sheet_view"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    table_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    payload = db.Column(db.Text, default="{}")

_ensured = False
def ensure():
    global _ensured
    if _ensured: return
    db.create_all()
    cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(table_row)"))]
    if "sort_order" not in cols:
        db.session.execute(text("ALTER TABLE table_row ADD COLUMN sort_order INTEGER DEFAULT 0"))
        db.session.commit()
    _ensured = True

def meta(tid):
    t = CustomTable.query.get_or_404(tid)
    m = user_access(tid, current_user)
    if not m["view"]: abort(403)
    cols = cols_of(tid)
    cm = []
    for c in cols:
        cm.append({"key": c.key, "title": c.title, "type": c.col_type,
                   "options": jload(c.options, []), "grp": (c.grp or "").strip(),
                   "computed": c.col_type in ("computed", "ref"),
                   "editable": can_edit_col(m, c.key) and c.col_type not in ("computed", "ref")})
    return t, m, cols, cm

def row_payload(tid, cols, rows):
    cache = {}
    def remote(rt):
        if rt not in cache:
            cache[rt] = [jload(r.data, {}) for r in TableRow.query.filter_by(table_id=rt, deleted_at=None).all()]
        return cache[rt]
    so = {r[0]: r[1] for r in db.session.execute(text("SELECT id, sort_order FROM table_row WHERE table_id=:t"), {"t": tid})}
    rows = sorted(rows, key=lambda r: (so.get(r.id, 0), r.id))
    out = []
    for r in rows:
        d = jload(r.data, {})
        cells = {c.key: (compute_value(c, d, remote) if c.col_type in ("computed", "ref") else d.get(c.key, "")) for c in cols}
        out.append({"id": r.id, "cells": cells, "updated": r.updated_at.isoformat() if r.updated_at else "",
                    "deleted": r.deleted_at is not None})
    return out

def stamp(): return datetime.datetime.utcnow()

@tables_bp.route("/sheet")
@perm("tables.view")
def sheet_index():
    ensure()
    ts = [t for t in CustomTable.query.order_by(CustomTable.order, CustomTable.id).all()
          if user_access(t.id, current_user)["view"]]
    return render_template("tables/sheet_index.html", tables=ts)

@tables_bp.route("/<int:tid>/sheet")
@perm("tables.view")
def sheet_view(tid):
    ensure()
    t, m, cols, cm = meta(tid)
    rows = TableRow.query.filter_by(table_id=tid, deleted_at=None).all()
    payload = {"tid": tid, "cols": cm, "rows": row_payload(tid, cols, rows),
               "counters": calc_counters(t, [jload(r.data, {}) for r in rows]),
               "m": {"create": m["create"], "delete": m["delete"] or m["edit"] is None},
               "trash": TableRow.query.filter(TableRow.table_id == tid, TableRow.deleted_at.isnot(None)).count(),
               "server_ts": stamp().isoformat(),
               "urls": {"data": url_for("tables.sheet_data", tid=tid),
                        "cell": url_for("tables.sheet_cell", tid=tid),
                        "row": url_for("tables.sheet_row", tid=tid),
                        "bulk": url_for("tables.sheet_bulk", tid=tid),
                        "reorder": url_for("tables.sheet_reorder", tid=tid),
                        "history": url_for("tables.sheet_history", tid=tid),
                        "revert": url_for("tables.sheet_revert", tid=tid),
                        "views": url_for("tables.sheet_views", tid=tid),
                        "form": url_for("tables.view", tid=tid),
                        "trash": url_for("tables.view", tid=tid, mode="trash")}}
    return render_template("tables/sheet.html", t=t, payload=payload)

@tables_bp.route("/<int:tid>/sheet/data")
@perm("tables.view")
def sheet_data(tid):
    ensure()
    t, m, cols, cm = meta(tid)
    since = request.args.get("since", "")
    rows = TableRow.query.filter_by(table_id=tid, deleted_at=None).all()
    changes = []
    if since:
        try:
            ts = datetime.datetime.fromisoformat(since)
            changes = [{"row": l.row_id, "key": l.column_key, "who": l.who, "old": l.old_value,
                        "new": l.new_value, "ts": l.ts.isoformat()}
                       for l in CellLog.query.filter(CellLog.table_id == tid, CellLog.ts > ts).order_by(CellLog.ts).all()]
        except Exception:
            pass
    return jsonify({"rows": row_payload(tid, cols, rows),
                    "counters": calc_counters(t, [jload(r.data, {}) for r in rows]),
                    "changes": changes, "server_ts": stamp().isoformat(),
                    "trash": TableRow.query.filter(TableRow.table_id == tid, TableRow.deleted_at.isnot(None)).count()})

@tables_bp.route("/<int:tid>/sheet/cell", methods=["POST"])
@perm("tables.view")
def sheet_cell(tid):
    ensure()
    t, m, cols, cm = meta(tid)
    j = request.get_json(force=True)
    rid, key, nv = j.get("id"), j.get("key"), str(j.get("value", ""))
    col = next((c for c in cols if c.key == key), None)
    if col is None or col.col_type in ("computed", "ref"):
        return jsonify({"ok": False, "err": "computed"}), 400
    if not can_edit_col(m, key):
        return jsonify({"ok": False, "err": "locked", "grp": col.grp}), 403
    row = TableRow.query.get(rid)
    if row is None or row.table_id != tid or row.deleted_at:
        return jsonify({"ok": False, "err": "gone"}), 404
    data = jload(row.data, {})
    ov = str(data.get(key, "") or "")
    if ov != nv:
        data[key] = nv
        row.data = json.dumps(data, ensure_ascii=False)
        row.updated_at = stamp()
        db.session.add(CellLog(table_id=tid, row_id=row.id, column_key=key, old_value=ov, new_value=nv, who=who()))
        db.session.commit()
    cache = {}
    def remote(rt):
        if rt not in cache:
            cache[rt] = [jload(r.data, {}) for r in TableRow.query.filter_by(table_id=rt, deleted_at=None).all()]
        return cache[rt]
    cells = {c.key: (compute_value(c, data, remote) if c.col_type in ("computed", "ref") else data.get(c.key, "")) for c in cols}
    allrows = [jload(r.data, {}) for r in TableRow.query.filter_by(table_id=tid, deleted_at=None).all()]
    return jsonify({"ok": True, "id": rid, "cells": cells, "counters": calc_counters(t, allrows),
                    "updated": row.updated_at.isoformat(), "server_ts": stamp().isoformat()})

@tables_bp.route("/<int:tid>/sheet/row", methods=["POST"])
@perm("tables.view")
def sheet_row(tid):
    ensure()
    t, m, cols, cm = meta(tid)
    if not m["create"]:
        return jsonify({"ok": False, "err": "nocreate"}), 403
    row = TableRow(table_id=tid, data="{}", created_by=who())
    db.session.add(row); db.session.flush()
    mx = db.session.execute(text("SELECT COALESCE(MAX(sort_order),0) FROM table_row WHERE table_id=:t"), {"t": tid}).scalar()
    db.session.execute(text("UPDATE table_row SET sort_order=:o WHERE id=:i"), {"o": mx + 1, "i": row.id})
    db.session.add(CellLog(table_id=tid, row_id=row.id, column_key="*", old_value="", new_value="строка создана в листе", who=who()))
    db.session.commit()
    return jsonify({"ok": True, "row": row_payload(tid, cols, [row])[0], "server_ts": stamp().isoformat()})

def _row_action(tid, rid, action):
    t, m, cols, cm = meta(tid)
    row = TableRow.query.get_or_404(rid)
    if action == "delete":
        if not (m["delete"] or m["edit"] is None): return jsonify({"ok": False, "err": "nodelete"}), 403
        row.deleted_at = stamp(); row.deleted_by = who()
    elif action == "restore":
        if not (m["create"] or m["edit"] is None): return jsonify({"ok": False, "err": "nocreate"}), 403
        row.deleted_at = None; row.deleted_by = ""
    elif action == "purge":
        if not (m["delete"] or m["edit"] is None): return jsonify({"ok": False, "err": "nodelete"}), 403
        db.session.delete(row)
    db.session.commit()
    return jsonify({"ok": True, "server_ts": stamp().isoformat()})

@tables_bp.route("/<int:tid>/sheet/row/<int:rid>/<action>", methods=["POST"])
@perm("tables.view")
def sheet_row_action(tid, rid, action):
    ensure()
    if action not in ("delete", "restore", "purge"): abort(404)
    return _row_action(tid, rid, action)

@tables_bp.route("/<int:tid>/sheet/bulk", methods=["POST"])
@perm("tables.view")
def sheet_bulk(tid):
    ensure()
    t, m, cols, cm = meta(tid)
    j = request.get_json(force=True)
    ids = j.get("ids", [])
    if j.get("action") == "delete":
        if not (m["delete"] or m["edit"] is None): return jsonify({"ok": False, "err": "nodelete"}), 403
        for row in TableRow.query.filter(TableRow.table_id == tid, TableRow.id.in_(ids)).all():
            row.deleted_at = stamp(); row.deleted_by = who()
        db.session.commit()
        return jsonify({"ok": True, "n": len(ids), "server_ts": stamp().isoformat()})
    key, nv = j.get("key"), str(j.get("value", ""))
    col = next((c for c in cols if c.key == key), None)
    if col is None or not can_edit_col(m, key): return jsonify({"ok": False, "err": "locked"}), 403
    n = 0
    for row in TableRow.query.filter(TableRow.table_id == tid, TableRow.id.in_(ids), TableRow.deleted_at.is_(None)).all():
        data = jload(row.data, {})
        ov = str(data.get(key, "") or "")
        if ov != nv:
            data[key] = nv; row.data = json.dumps(data, ensure_ascii=False); row.updated_at = stamp()
            db.session.add(CellLog(table_id=tid, row_id=row.id, column_key=key, old_value=ov, new_value=nv, who=who()))
            n += 1
    db.session.commit()
    return jsonify({"ok": True, "n": n, "server_ts": stamp().isoformat()})

@tables_bp.route("/<int:tid>/sheet/reorder", methods=["POST"])
@perm("tables.view")
def sheet_reorder(tid):
    ensure()
    t, m, cols, cm = meta(tid)
    ids = request.get_json(force=True).get("ids", [])
    for i, rid in enumerate(ids):
        db.session.execute(text("UPDATE table_row SET sort_order=:o WHERE id=:i AND table_id=:t"), {"o": i + 1, "i": rid, "t": tid})
    db.session.commit()
    return jsonify({"ok": True, "server_ts": stamp().isoformat()})

@tables_bp.route("/<int:tid>/sheet/history")
@perm("tables.view")
def sheet_history(tid):
    ensure()
    t, m, cols, cm = meta(tid)
    rid = request.args.get("rid", type=int)
    q = CellLog.query.filter_by(table_id=tid)
    if rid: q = q.filter_by(row_id=rid)
    logs = q.order_by(CellLog.ts.desc()).limit(120).all()
    return jsonify({"logs": [{"id": l.id, "row": l.row_id, "key": l.column_key, "old": l.old_value,
                              "new": l.new_value, "who": l.who, "ts": l.ts.isoformat()} for l in logs]})

@tables_bp.route("/<int:tid>/sheet/revert", methods=["POST"])
@perm("tables.view")
def sheet_revert(tid):
    ensure()
    t, m, cols, cm = meta(tid)
    lid = request.get_json(force=True).get("log_id")
    l = CellLog.query.get_or_404(lid)
    col = next((c for c in cols if c.key == l.column_key), None)
    if col is None or not can_edit_col(m, l.column_key): return jsonify({"ok": False, "err": "locked"}), 403
    row = TableRow.query.get(l.row_id)
    if row is None: return jsonify({"ok": False, "err": "gone"}), 404
    data = jload(row.data, {})
    ov = str(data.get(l.column_key, "") or "")
    data[l.column_key] = l.old_value or ""
    row.data = json.dumps(data, ensure_ascii=False); row.updated_at = stamp()
    db.session.add(CellLog(table_id=tid, row_id=row.id, column_key=l.column_key, old_value=ov,
                           new_value=l.old_value or "", who=who() + " (возврат старого)"))
    db.session.commit()
    return jsonify({"ok": True, "server_ts": stamp().isoformat()})

@tables_bp.route("/<int:tid>/sheet/views", methods=["GET", "POST", "DELETE"])
@perm("tables.view")
def sheet_views(tid):
    ensure()
    t, m, cols, cm = meta(tid)
    uid = current_user.id if current_user.is_authenticated else 0
    if request.method == "GET":
        vs = SheetView.query.filter_by(user_id=uid, table_id=tid).all()
        return jsonify({"views": [{"id": v.id, "name": v.name, "payload": jload(v.payload, {})} for v in vs]})
    if request.method == "POST":
        j = request.get_json(force=True)
        v = SheetView(user_id=uid, table_id=tid, name=(j.get("name") or "Вид")[:80],
                      payload=json.dumps(j.get("payload", {}), ensure_ascii=False))
        db.session.add(v); db.session.commit()
        return jsonify({"ok": True, "id": v.id})
    vid = request.args.get("id", type=int)
    v = SheetView.query.filter_by(id=vid, user_id=uid).first()
    if v: db.session.delete(v); db.session.commit()
    return jsonify({"ok": True})
