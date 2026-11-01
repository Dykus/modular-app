from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from core.app import db
from core.auth import perm
from modules.production.models import ProductionTask, STATUS_LABELS, STATUS_BADGES
from datetime import datetime

production_bp = Blueprint("production", __name__, url_prefix="/production",
                         template_folder="templates")

@production_bp.route("/index")
@perm("production.view")
def index():
    """Alias dlya reestra moduley: menyu stroit ssylku na production.index.
    Prosto perenaapravlyaem na glavnyi ekran modulya (spisok zadach)."""
    return redirect(url_for("production.list_tasks"))

@production_bp.route("/")
@perm("production.view")
def list_tasks():
    """Spisok vseh zadach"""
    status_filter = request.args.get("status", "all")

    query = ProductionTask.query

    if status_filter != "all" and status_filter in STATUS_LABELS:
        query = query.filter(ProductionTask.status == status_filter)

    tasks = query.order_by(ProductionTask.created_at.desc()).all()

    counts = {s: 0 for s in STATUS_LABELS}
    for task in tasks:
        if task.status in counts:
            counts[task.status] += 1

    return render_template("production/list.html",
                         tasks=tasks,
                         counts=counts,
                         total=len(tasks),
                         status_filter=status_filter,
                         labels=STATUS_LABELS,
                         badges=STATUS_BADGES)

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

        if ProductionTask.query.filter_by(number=number).first():
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
    """Udalenie zadachi"""
    task = ProductionTask.query.get_or_404(task_id)
    number = task.number

    db.session.delete(task)
    db.session.commit()

    flash("Задача " + number + " удалена")
    return redirect(url_for("production.list_tasks"))
