"""Marshuty modulya "Rukovodstvo": chtenie, pechat, pravka razdelov."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.app import db
from core.auth import perm
from datetime import datetime
from modules.manual.models import ManualSection

manual_bp = Blueprint("manual", __name__, url_prefix="/manual", template_folder="templates")

def _sections():
    return ManualSection.query.order_by(ManualSection.order, ManualSection.id).all()

@manual_bp.route("/")
@perm("manual.view")
def index():
    return render_template("manual/index.html", sections=_sections(),
                           print_mode=False,
                           now_str=datetime.now().strftime("%d.%m.%Y %H:%M"))

@manual_bp.route("/print")
@perm("manual.view")
def print_view():
    return render_template("manual/index.html", sections=_sections(),
                           print_mode=True,
                           now_str=datetime.now().strftime("%d.%m.%Y %H:%M"))

@manual_bp.route("/<int:sid>/edit")
@perm("manual.manage")
def edit(sid):
    s = ManualSection.query.get_or_404(sid)
    return render_template("manual/edit.html", section=s)

@manual_bp.route("/save", methods=["POST"])
@perm("manual.manage")
def save():
    sid = request.form.get("id", type=int)
    title = (request.form.get("title") or "").strip()
    body = (request.form.get("body") or "").strip()
    order = request.form.get("order", type=int) or 0
    who = (request.form.get("who") or "без имени").strip()
    if not title:
        flash("Укажите заголовок раздела.")
        return redirect(url_for("manual.index"))
    s = ManualSection.query.get_or_404(sid)
    s.title = title; s.body = body; s.order = order; s.updated_by = who
    db.session.commit()
    flash("Раздел обновлён: " + title)
    return redirect(url_for("manual.index"))
