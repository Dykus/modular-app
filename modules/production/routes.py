from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from core.app import db
from core.auth import perm
from modules.production.models import ProductionTask, STATUS_LABELS, STATUS_BADGES
from datetime import datetime, timedelta

TRASH_DAYS = 30

production_bp = Blueprint("production", __name__, url_prefix="/production",
                         template_folder="templates")

@production_bp.route("/index")
@perm("production.view")
def index():
    """Alias dlya reestra moduley: menyu stroit ssylku na production.index."""
    return redirect(url_for("production.list_tasks"))

@production_bp.route("/")
@perm("production.view")
def list_tasks():
    """Spisok aktivnyh zadach (korzina ne pokazyvaetsya)"""
    status_filter = request.args.get("status", "all")

    query = ProductionTask.query.filter(ProductionTask.deleted_at.is_(None))

    if status_filter != "all" and status_filter in STATUS_LABELS:
        query = query.filter(ProductionTask.status == status_filter)

    tasks = query.order_by(ProductionTask.created_at.desc()).all()

    counts = {s: 0 for s in STATUS_LABELS}
    for task in tasks:
        if task.status in counts:
            counts[task.status] += 1

    trash_count = ProductionTask.query.filter(ProductionTask.deleted_at.isnot(None)).count()

    return render_template("production/list.html",
                         tasks=tasks,
                         counts=counts,
                         total=len(tasks),
                         status_filter=status_filter,
                         labels=STATUS_LABELS,
                         badges=STATUS_BADGES,
                         trash_count=trash_count)

@production_bp.route("/trash")
@perm("production.edit")
def trash_list():
    """Korzina: udalennye zadachi + autoochistka starshe TRASH_DAYS."""
    cutoff = datetime.utcnow() - timedelta(days=TRASH_DAYS)
    old = ProductionTask.query.filter(
        ProductionTask.deleted_at.isnot(None),
        ProductionTask.deleted_at < cutoff).all()
    purged = len(old)
    for t in old:
        db.session.delete(t)
    if purged:
        db.session.commit()

    tasks = ProductionTask.query.filter(
        ProductionTask.deleted_at.isnot(None)
    ).order_by(ProductionTask.deleted_at.desc()).all()

    return render_template("production/trash.html",
                         tasks=tasks,
                         purged=purged,
                         trash_days=TRASH_DAYS,
                         labels=STATUS_LABELS,
                         now=datetime.utcnow())

@production_bp.route("/add", methods=["GET", "POST"])
@perm("production.create")
def add_task():
    """Dobavlenie novoi zadachi"""
    if request.method == "POST":
        number = request.form.get("number", "").strip()
        description = request.form.get("description", "").strip()
        assignee = request.form.get("assignee", "").strip()
        priority = request.form.get("priority", "normal")

        if not number or not description:
            flash("Укажите номер и описание задачи")
            return redirect(url_for("production.add_task"))

        existing = ProductionTask.query.filter_by(number=number).first()
        if existing:
            if existing.deleted_at is not None:
                flash("Номер " + number + " занят задачей в корзине: восстановите её или удалите навсегда, чтобы освободить номер.")
            else:
                flash("Задача с номером " + number + " уже существует")
            return redirect(url_for("production.add_task"))

        task = ProductionTask(
            number=number,
            description=description,
            assignee=assignee,
            priority=priority,
            created_by=current_user.username if current_user.is_authenticated else "аноним"
        )

        db.session.add(task)
        db.session.commit()

        flash("Задача " + number + " создана")
        return redirect(url_for("production.list_tasks"))

    return render_template("production/add.html")

@production_bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@perm("production.edit")
def edit_task(task_id):
    """Redaktirovanie zadachi"""
    task = ProductionTask.query.get_or_404(task_id)

    if request.method == "POST":
        description = request.form.get("description", "").strip()
        status = request.form.get("status", task.status)
        assignee = request.form.get("assignee", "").strip()
        priority = request.form.get("priority", task.priority)
        comment = request.form.get("comment", "").strip()

        if not description:
            flash("Описание не может быть пустым")
            return redirect(url_for("production.edit_task", task_id=task_id))

        task.description = description
        task.status = status
        task.assignee = assignee
        task.priority = priority
        task.comment = comment

        db.session.commit()

        flash("Задача " + task.number + " обновлена")
        return redirect(url_for("production.list_tasks"))

    return render_template("production/edit.html", task=task, labels=STATUS_LABELS)

@production_bp.route("/<int:task_id>/delete", methods=["POST"])
@perm("production.delete")
def delete_task(task_id):
    """Udalenie = peremeshchenie v korzinu (ne unichtozhenie)."""
    task = ProductionTask.query.get_or_404(task_id)
    task.deleted_at = datetime.utcnow()
    task.deleted_by = current_user.username if current_user.is_authenticated else "аноним"
    db.session.commit()

    flash("Задача " + task.number + " перемещена в корзину. Хранится " + str(TRASH_DAYS) + " дней, можно восстановить.")
    return redirect(url_for("production.list_tasks"))

@production_bp.route("/<int:task_id>/restore", methods=["POST"])
@perm("production.edit")
def restore_task(task_id):
    """Vosstanovlenie iz korziny."""
    task = ProductionTask.query.get_or_404(task_id)
    if task.deleted_at is None:
        flash("Задача не находится в корзине.")
        return redirect(url_for("production.trash_list"))

    clash = ProductionTask.query.filter(
        ProductionTask.number == task.number,
        ProductionTask.deleted_at.is_(None),
        ProductionTask.id != task.id).first()
    if clash:
        flash("Восстановление невозможно: номер " + task.number + " уже занят активной задачей. Переименуйте её или удалите навсегда.")
        return redirect(url_for("production.trash_list"))

    task.deleted_at = None
    task.deleted_by = ""
    db.session.commit()

    flash("Задача " + task.number + " восстановлена.")
    return redirect(url_for("production.trash_list"))

@production_bp.route("/<int:task_id>/purge", methods=["POST"])
@perm("production.delete")
def purge_task(task_id):
    """Udalenie navsegda, bez vozvrata."""
    task = ProductionTask.query.get_or_404(task_id)
    number = task.number

    db.session.delete(task)
    db.session.commit()

    flash("Задача " + number + " удалена навсегда.")
    return redirect(url_for("production.trash_list"))
