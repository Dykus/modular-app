from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from core.app import db
from core.auth import perm
from datetime import datetime
from core.models import User
from modules.feedback.models import FeedbackItem, FeedbackLog, STATUS_LABELS, STATUS_BADGE
from modules.settings.models import get_bool

feedback_bp = Blueprint("feedback", __name__, url_prefix="/feedback", template_folder="templates")

def _match_user(name):
    """Ishchet polzovatelya po imeni ili polnomu imeni (dlya privyazki id)."""
    if not name:
        return None
    ln = name.strip().lower()
    u = User.query.filter(db.func.lower(User.username) == ln).first()
    if u:
        return u
    return User.query.filter(db.func.lower(User.full_name) == ln).first()

def _names_of(user):
    return {user.username.lower(), (user.full_name or "").lower()}

def _can_see(it, user):
    """Privatnuyu zapis vidyat: avtor, adresat, superuser. Otkrytuyu - vse s pravom view."""
    if not it.is_private:
        return True
    if user is None or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if it.author_id == user.id or it.addressee_id == user.id:
        return True
    nm = _names_of(user)
    return it.author.strip().lower() in nm or (it.addressee or "").strip().lower() in nm

def _can_toggle(it, user):
    """Menyat vidimost mogut: avtor, adresat, superuser."""
    if user is None or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if it.author_id == user.id or it.addressee_id == user.id:
        return True
    nm = _names_of(user)
    return it.author.strip().lower() in nm or (it.addressee or "").strip().lower() in nm

@feedback_bp.route("/")
@perm("feedback.view")
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

    user = current_user if current_user.is_authenticated else None
    rows = []
    for it in items:
        if not _can_see(it, user):
            continue
        rows.append({"it": it, "can_toggle": _can_toggle(it, user)})

    counts = {s: 0 for s in STATUS_LABELS}
    for r in rows:
        counts[r["it"].status] = counts.get(r["it"].status, 0) + 1
    total = len(rows)

    people = User.query.filter_by(is_active=True).order_by(User.username).all()
    me = current_user.display_name if current_user.is_authenticated else ""
    return render_template("feedback/list.html", rows=rows, counts=counts, total=total,
                           status=status, q=q, labels=STATUS_LABELS, badges=STATUS_BADGE,
                           people=people, me=me)

@feedback_bp.route("/add", methods=["POST"])
@perm("feedback.create")
def add():
    author = (request.form.get("author") or "").strip() or (current_user.display_name if current_user.is_authenticated else "")
    addressee = (request.form.get("addressee") or "").strip()
    text = (request.form.get("text") or "").strip()
    is_private = bool(request.form.get("is_private"))
    if not author or not text:
        flash("Укажи имя и текст задачи")
        return redirect(url_for("feedback.list_items"))
    au = _match_user(author)
    ad = _match_user(addressee)
    it = FeedbackItem(author=author, author_id=current_user.id if current_user.is_authenticated else None,
                      addressee=addressee, addressee_id=ad.id if ad else None,
                      text=text, status="new", is_private=is_private)
    db.session.add(it); db.session.flush()
    db.session.add(FeedbackLog(item_id=it.id, who=author, action="created", new_status="new"))
    db.session.commit()
    flash("Задача создана" + (" (приватная)" if is_private else ""))
    return redirect(url_for("feedback.list_items"))

@feedback_bp.route("/<int:item_id>/status", methods=["POST"])
@perm("feedback.set_status")
def set_status(item_id):
    it = FeedbackItem.query.get_or_404(item_id)
    new = (request.form.get("status") or it.status).strip()
    who = (request.form.get("who") or "").strip() or "без имени"
    comment = (request.form.get("comment") or "").strip()
    if new not in STATUS_LABELS:
        flash("Неизвестный статус")
        return redirect(url_for("feedback.list_items"))
    if new == "reject" and not comment and get_bool("feedback_require_comment_on_reject", False):
        flash("Для статуса «Не нужно» укажи комментарий — почему отказ.")
        return redirect(url_for("feedback.list_items"))
    old = it.status
    if new != old:
        it.status = new; it.updated_at = datetime.utcnow()
        db.session.add(FeedbackLog(item_id=it.id, who=who, action="status",
                                   old_status=old, new_status=new, comment=comment))
    if comment:
        it.comment = comment
    db.session.commit()
    return redirect(url_for("feedback.list_items"))

@feedback_bp.route("/<int:item_id>/privacy", methods=["POST"])
@login_required
def toggle_privacy(item_id):
    it = FeedbackItem.query.get_or_404(item_id)
    if not _can_toggle(it, current_user):
        flash("Нельзя менять видимость чужой записи.")
        return redirect(url_for("feedback.list_items"))
    it.is_private = not it.is_private
    db.session.commit()
    flash("Запись теперь приватная: видна только автору, адресату и администратору." if it.is_private
          else "Запись теперь открыта всем, у кого есть доступ к разделу.")
    return redirect(url_for("feedback.list_items"))

@feedback_bp.route("/history")
@perm("feedback.view")
def history():
    q = (request.args.get("q") or "").strip()
    user = current_user if current_user.is_authenticated else None
    visible_ids = [it.id for it in FeedbackItem.query.all() if _can_see(it, user)]
    logs = FeedbackLog.query
    logs = logs.filter(FeedbackLog.item_id.in_(visible_ids if visible_ids else [-1]))
    if q:
        like = "%" + q + "%"
        logs = logs.join(FeedbackItem).filter(db.or_(
            FeedbackItem.text.ilike(like), FeedbackItem.author.ilike(like), FeedbackLog.who.ilike(like)))
    logs = logs.order_by(FeedbackLog.timestamp.desc()).limit(500).all()
    return render_template("feedback/history.html", logs=logs, q=q, labels=STATUS_LABELS, badges=STATUS_BADGE)
