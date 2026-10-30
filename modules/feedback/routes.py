from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.app import db
from datetime import datetime
from modules.feedback.models import FeedbackItem, FeedbackLog, STATUS_LABELS, STATUS_BADGE

feedback_bp = Blueprint("feedback", __name__, url_prefix="/feedback", template_folder="templates")

@feedback_bp.route("/")
def list_items():
    status = request.args.get("status", "all")
    q = (request.args.get("q") or "").strip()
    query = FeedbackItem.query
    if status in STATUS_LABELS:
        query = query.filter(FeedbackItem.status == status)
    if q:
        like = "%" + q + "%"
        query = query.filter(db.or_(FeedbackItem.text.ilike(like), FeedbackItem.author.ilike(like)))
    items = query.order_by(FeedbackItem.created_at.desc()).all()
    counts = {s: FeedbackItem.query.filter_by(status=s).count() for s in STATUS_LABELS}
    total = FeedbackItem.query.count()
    return render_template("list.html", items=items, counts=counts, total=total,
                           status=status, q=q, labels=STATUS_LABELS, badges=STATUS_BADGE)

@feedback_bp.route("/add", methods=["POST"])
def add():
    author = (request.form.get("author") or "").strip()
    text = (request.form.get("text") or "").strip()
    if not author or not text:
        flash("Укажите имя и текст хотелки"); return redirect(url_for("feedback.list_items"))
    it = FeedbackItem(author=author, text=text, status="new")
    db.session.add(it); db.session.flush()
    db.session.add(FeedbackLog(item_id=it.id, who=author, action="created", new_status="new"))
    db.session.commit()
    return redirect(url_for("feedback.list_items"))

@feedback_bp.route("/<int:item_id>/status", methods=["POST"])
def set_status(item_id):
    it = FeedbackItem.query.get_or_404(item_id)
    new = (request.form.get("status") or it.status).strip()
    who = (request.form.get("who") or "").strip() or "без имени"
    comment = (request.form.get("comment") or "").strip()
    if new not in STATUS_LABELS:
        flash("Неизвестный статус"); return redirect(url_for("feedback.list_items"))
    old = it.status
    if new != old:
        it.status = new; it.updated_at = datetime.utcnow()
        db.session.add(FeedbackLog(item_id=it.id, who=who, action="status",
                                   old_status=old, new_status=new, comment=comment))
    if comment:
        it.comment = comment
    db.session.commit()
    return redirect(url_for("feedback.list_items"))

@feedback_bp.route("/history")
def history():
    q = (request.args.get("q") or "").strip()
    logs = FeedbackLog.query
    if q:
        like = "%" + q + "%"
        logs = logs.join(FeedbackItem).filter(db.or_(
            FeedbackItem.text.ilike(like), FeedbackItem.author.ilike(like), FeedbackLog.who.ilike(like)))
    logs = logs.order_by(FeedbackLog.timestamp.desc()).limit(500).all()
    return render_template("history.html", logs=logs, q=q, labels=STATUS_LABELS, badges=STATUS_BADGE)
