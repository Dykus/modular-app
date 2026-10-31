"""Stranicy vhoda, profilya, smeny parolya + ekrany Rolei."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from core.app import db
# GLAVNYI FIKS: perm berem iz core.auth, a ne ob'yavlyaem vnizu fayla.
from core.auth import verify_password, role_immutable_list, perm
from core.models import User, Role, RolePermission, LoginLog
from core.permissions import ALL_PERMS, PERM_GROUPS
from core.settings_helper import get_int
from datetime import datetime, timedelta

auth_bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder="../web/templates")

def _ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "")[:64]

def _log(username, uid, success, reason="", provider="local"):
    db.session.add(LoginLog(username=username, user_id=uid, success=success,
                            ip=_ip(), provider=provider, reason=reason))
    db.session.commit()

# --- Vhod / Vyhod / Profil / Smena parolya ---------------------------------

@auth_bp.route("/login", methods=["GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return render_template("auth/login.html")

@auth_bp.route("/login", methods=["POST"])
def do_login():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    user = User.query.filter(db.func.lower(User.username) == username.lower()).first()
    if not user:
        _log(username, None, False, "нет такого пользователя")
        flash("Неверный логин или пароль."); return redirect(url_for("auth.login"))
    if not user.is_active:
        _log(username, user.id, False, "закрыт")
        flash("Пользователь закрыт. Обратитесь к администратору."); return redirect(url_for("auth.login"))
    if user.locked_until and user.locked_until > datetime.utcnow():
        _log(username, user.id, False, "заблокирован")
        flash("Вход временно заблокирован."); return redirect(url_for("auth.login"))
    if not verify_password(user, password):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        thr = get_int("lock_threshold", 5)
        if user.failed_attempts >= thr:
            mins = get_int("lock_minutes", 15)
            user.locked_until = datetime.utcnow() + timedelta(minutes=mins)
            user.failed_attempts = 0
        db.session.commit()
        _log(username, user.id, False, "неверный пароль")
        flash("Неверный логин или пароль."); return redirect(url_for("auth.login"))
    user.failed_attempts = 0; user.locked_until = None; user.last_login = datetime.utcnow()
    db.session.commit()
    login_user(user, remember=bool(request.form.get("remember")))
    _log(username, user.id, True)
    nxt = request.args.get("next")
    return redirect(nxt if nxt and nxt.startswith("/") else url_for("main.index"))

@auth_bp.route("/logout")
@login_required
def logout():
    _log(current_user.username, current_user.id, True, "выход")
    logout_user()
    flash("Вы вышли из системы.")
    return redirect(url_for("auth.login"))

@auth_bp.route("/profile")
@login_required
def profile():
    return render_template("auth/profile.html")

@auth_bp.route("/change-password", methods=["GET"])
def change_password():
    return render_template("auth/change_password.html", forced=current_user.must_change_password)

@auth_bp.route("/change-password", methods=["POST"])
@login_required
def do_change_password():
    old = request.form.get("old") or ""
    new = request.form.get("new") or ""
    rep = request.form.get("repeat") or ""
    if not verify_password(current_user, old):
        flash("Старый пароль неверен."); return redirect(url_for("auth.change_password"))
    if len(new) < 4:
        flash("Новый пароль слишком короткий (мин. 4)."); return redirect(url_for("auth.change_password"))
    if new != rep:
        flash("Пароли не совпадают."); return redirect(url_for("auth.change_password"))
    current_user.password_hash = hash_password_local(new)
    current_user.must_change_password = False
    db.session.commit()
    flash("Пароль изменён.")
    return redirect(url_for("auth.profile"))

def hash_password_local(pw):
    """Malen'kaya obertka, chtoby ne tashchit' lishnii import sverhu."""
    from core.auth import hash_password
    return hash_password(pw)

# --- EKRAN ROLEI -----------------------------------------------------------

@auth_bp.route("/roles")
@perm("auth.manage_roles")
def roles_list():
    """Spisok vseh roley s kolichestvom polzovateley i spiskom prav."""
    roles = Role.query.order_by(Role.is_system.desc(), Role.id).all()
    rows = []
    for r in roles:
        perms_on_role = {rp.perm for rp in r.permissions}
        rows.append({"role": r, "users_count": r.users.count(), "perms": perms_on_role})
    # FIX: peredayom all_perms v shablon, chtoby bейджи imeli podsказki
    return render_template("auth/roles.html", rows=rows, all_perms=ALL_PERMS)

@auth_bp.route("/roles/new")
@perm("auth.manage_roles")
def roles_new():
    return render_template(
        "auth/roles_edit.html", role=None, checked=set(),
        all_perms=ALL_PERMS, perm_groups=PERM_GROUPS, immutable=set(),
    )

@auth_bp.route("/roles/<int:rid>/edit")
@perm("auth.manage_roles")
def roles_edit(rid):
    r = Role.query.get_or_404(rid)
    checked = {rp.perm for rp in r.permissions}
    immutable = set(role_immutable_list(r))
    return render_template(
        "auth/roles_edit.html", role=r, checked=checked,
        all_perms=ALL_PERMS, perm_groups=PERM_GROUPS, immutable=immutable,
    )

@auth_bp.route("/roles/save", methods=["POST"])
@perm("auth.manage_roles")
def roles_save():
    rid = request.form.get("id", type=int)
    name = (request.form.get("name") or "").strip()
    desc = (request.form.get("description") or "").strip()
    chosen = set(request.form.getlist("perms"))

    if not name:
        flash("Укажите имя роли."); return redirect(url_for("auth.roles_list"))

    if rid:
        r = Role.query.get_or_404(rid)
        if current_user.role_id == r.id:
            flash("Нельзя изменить собственную роль — это защита от самоблокировки.")
            return redirect(url_for("auth.roles_list"))
        other = Role.query.filter(Role.name == name, Role.id != r.id).first()
        if other:
            flash("Роль с таким именем уже существует.")
            return redirect(url_for("auth.roles_edit", rid=r.id))
        r.name = name
        r.description = desc
        for imm in role_immutable_list(r):
            chosen.add(imm)
    else:
        if Role.query.filter_by(name=name).first():
            flash("Роль с таким именем уже существует.")
            return redirect(url_for("auth.roles_new"))
        r = Role(name=name, description=desc, is_system=False, immutable_perms="[]")
        db.session.add(r)
        db.session.flush()

    valid_chosen = {c for c in chosen if c in ALL_PERMS}
    existing = {rp.perm: rp for rp in r.permissions}
    for perm_code, rp in list(existing.items()):
        if perm_code not in valid_chosen:
            db.session.delete(rp)
    for perm_code in valid_chosen:
        if perm_code not in existing:
            db.session.add(RolePermission(role_id=r.id, perm=perm_code))

    db.session.commit()
    flash(("Роль обновлена: " if rid else "Роль создана: ") + r.name)
    return redirect(url_for("auth.roles_list"))

@auth_bp.route("/roles/<int:rid>/delete", methods=["POST"])
@perm("auth.manage_roles")
def roles_delete(rid):
    r = Role.query.get_or_404(rid)
    if r.is_system:
        flash("Системную роль удалить нельзя. Можно только отредактировать её права.")
        return redirect(url_for("auth.roles_list"))
    if r.users.count() > 0:
        flash("Нельзя удалить роль: на ней есть пользователи. Сначала переведите их на другую роль.")
        return redirect(url_for("auth.roles_list"))
    if current_user.role_id == r.id:
        flash("Нельзя удалить собственную роль.")
        return redirect(url_for("auth.roles_list"))
    db.session.delete(r)
    db.session.commit()
    flash("Роль удалена: " + r.name)
    return redirect(url_for("auth.roles_list"))
