from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.app import db
from datetime import datetime
from modules.versions.models import Release, STATUS_LABELS, STATUS_BADGE

versions_bp = Blueprint("versions", __name__, url_prefix="/versions", template_folder="templates")

@versions_bp.route("/")
def list_releases():
    edit_id = request.args.get("edit", type=int)
    editing = Release.query.get(edit_id) if edit_id else None
    releases = Release.query.order_by(Release.release_date.desc(), Release.id.desc()).all()
    return render_template("list.html", releases=releases, editing=editing,
                           statuses=STATUS_LABELS, badges=STATUS_BADGE)

@versions_bp.route("/save", methods=["POST"])
def save():
    rid = request.form.get("id", type=int)
    version = (request.form.get("version") or "").strip()
    title = (request.form.get("title") or "").strip()
    notes = (request.form.get("notes") or "").strip()
    status = (request.form.get("status") or "released").strip()
    date_str = (request.form.get("release_date") or "").strip()
    who = (request.form.get("who") or "без имени").strip()
    if not version:
        flash("Укажи номер версии")
        return redirect(url_for("versions.list_releases"))
    if status not in STATUS_LABELS:
        status = "released"
    try:
        rdate = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.utcnow().date()
    except ValueError:
        rdate = datetime.utcnow().date()
    if rid:
        rel = Release.query.get_or_404(rid)
        rel.version, rel.title, rel.notes, rel.status, rel.release_date = version, title, notes, status, rdate
    else:
        rel = Release(version=version, title=title, notes=notes, status=status, release_date=rdate)
        db.session.add(rel)
    if status == "released" and request.form.get("make_current"):
        Release.query.update({"is_current": False})
        rel.is_current = True
    db.session.commit()
    flash("Релиз сохранён (автор: " + who + ")")
    return redirect(url_for("versions.list_releases"))

@versions_bp.route("/<int:rid>/make-current", methods=["POST"])
def make_current(rid):
    rel = Release.query.get_or_404(rid)
    Release.query.update({"is_current": False})
    rel.is_current = True
    db.session.commit()
    flash("Текущая версия: " + rel.version)
    return redirect(url_for("versions.list_releases"))

@versions_bp.route("/<int:rid>/delete", methods=["POST"])
def delete(rid):
    rel = Release.query.get_or_404(rid)
    if rel.is_current:
        flash("Нельзя удалить текущую версию")
        return redirect(url_for("versions.list_releases"))
    db.session.delete(rel)
    db.session.commit()
    flash("Релиз удалён")
    return redirect(url_for("versions.list_releases"))

@versions_bp.route("/about")
def about():
    cur = Release.query.filter_by(is_current=True).first()
    releases = Release.query.order_by(Release.release_date.desc(), Release.id.desc()).limit(10).all()
    return render_template("about.html", cur=cur, releases=releases, statuses=STATUS_LABELS, badges=STATUS_BADGE)
