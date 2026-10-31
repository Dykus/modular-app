from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from core.app import db
import os
from modules.changelog.models import ChangelogEntry, TYPE_LABELS, TYPE_BADGE

changelog_bp = Blueprint("changelog", __name__, url_prefix="/changelog", template_folder="templates")
DEFAULT_MODULES = ["core", "feedback", "production", "changelog", "versions", "help", "settings"]

@changelog_bp.route("/")
def list_entries():
    typ = request.args.get("type", "all")
    mod = request.args.get("module", "all")
    q = (request.args.get("q") or "").strip()
    query = ChangelogEntry.query
    if typ in TYPE_LABELS:
        query = query.filter(ChangelogEntry.change_type == typ)
    if mod != "all":
        query = query.filter(ChangelogEntry.module == mod)
    if q:
        like = "%" + q + "%"
        query = query.filter(db.or_(ChangelogEntry.description.ilike(like), ChangelogEntry.author.ilike(like)))
    entries = query.order_by(ChangelogEntry.date.desc()).all()
    db_mods = [r[0] for r in db.session.query(ChangelogEntry.module).distinct().all()]
    module_opts = sorted(set(DEFAULT_MODULES) | set(db_mods))
    return render_template("changelog/list.html", entries=entries, types=TYPE_LABELS, badges=TYPE_BADGE,
                           typ=typ, mod=mod, q=q, module_opts=module_opts)

@changelog_bp.route("/add", methods=["POST"])
def add():
    author = (request.form.get("author") or "").strip()
    desc = (request.form.get("description") or "").strip()
    typ = (request.form.get("change_type") or "added").strip()
    mod = (request.form.get("module") or "core").strip()
    ticket = (request.form.get("ticket") or "").strip()
    if not author or not desc:
        flash("Укажи имя и описание изменения")
        return redirect(url_for("changelog.list_entries"))
    if typ not in TYPE_LABELS:
        typ = "added"
    db.session.add(ChangelogEntry(author=author, description=desc, change_type=typ, module=mod, ticket=ticket))
    db.session.commit()
    return redirect(url_for("changelog.list_entries"))

@changelog_bp.route("/<int:eid>/delete", methods=["POST"])
def delete(eid):
    e = ChangelogEntry.query.get_or_404(eid)
    db.session.delete(e)
    db.session.commit()
    flash("Запись удалена")
    return redirect(url_for("changelog.list_entries"))

@changelog_bp.route("/export.csv")
def export_csv():
    rows = ["Дата;Тип;Модуль;Описание;Автор;Задача"]
    for e in ChangelogEntry.query.order_by(ChangelogEntry.date.desc()).all():
        rows.append(";".join([
            e.date.strftime("%d.%m.%Y %H:%M"),
            TYPE_LABELS.get(e.change_type, e.change_type),
            e.module,
            e.description.replace(";", ",").replace(os.linesep, " "),
            e.author,
            e.ticket or "",
        ]))
    data = os.linesep.join(rows)
    return Response("﻿" + data, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=changelog.csv"})
