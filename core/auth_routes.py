"""Stranicy vhoda, profilya, smeny parolya, Rolei i Polzovateley."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from core.app import db
from core.auth import verify_password, hash_password, role_immutable_list, perm
from core.models import User, Role, RolePermission, LoginLog, AuditLog
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

def _audit(action, detail):
    """Zapis v audit: kto iz rukovoditeley chto sdelal s lyud'mi."""
    db.session.add(AuditLog(user_id=current_user.id, action=action,
                            table_name="user", record_id=None, changes=detail))
    db.session.commit()

def _admin_role():
    return Role.query.filter_by(name="admin").first()

def _is_last_active_admin(u):
    """True, esli u - poslednii aktivnyi polzovatel s rolyu admin."""
    ar = _admin_role()
    if not ar or u.role_id != ar.id or not u.is_active:
        return False
    cnt = User.query.filter_by(role_id=ar.id, is_active=True).count()
    return cnt <= 1

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
    current_user.password_hash = hash_password(new)
    current_user.must_change_password = False
    db.session.commit()
    flash("Пароль изменён.")
    return redirect(url_for("auth.profile"))

# --- EKRAN ROLEI (iz podshaga 2b-1, bez izmeneniy) --------------------------

@auth_bp.route("/roles")
@perm("auth.manage_roles")
def roles_list():
    roles = Role.query.order_by(Role.is_system.desc(), Role.id).all()
    rows = []
    for r in roles:
        perms_on_role = {rp.perm for rp in r.permissions}
        rows.append({"role": r, "users_count": r.users.count(), "perms": perms_on_role})
    return render_template("auth/roles.html", rows=rows, all_perms=ALL_PERMS)

@auth_bp.route("/roles/new")
@perm("auth.manage_roles")
def roles_new():
    return render_template("auth/roles_edit.html", role=None, checked=set(),
                           all_perms=ALL_PERMS, perm_groups=PERM_GROUPS, immutable=set())

@auth_bp.route("/roles/<int:rid>/edit")
@perm("auth.manage_roles")
def roles_edit(rid):
    r = Role.query.get_or_404(rid)
    checked = {rp.perm for rp in r.permissions}
    immutable = set(role_immutable_list(r))
    return render_template("auth/roles_edit.html", role=r, checked=checked,
                           all_perms=ALL_PERMS, perm_groups=PERM_GROUPS, immutable=immutable)

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
        r.name = name; r.description = desc
        for imm in role_immutable_list(r):
            chosen.add(imm)
    else:
        if Role.query.filter_by(name=name).first():
            flash("Роль с таким именем уже существует.")
            return redirect(url_for("auth.roles_new"))
        r = Role(name=name, description=desc, is_system=False, immutable_perms="[]")
        db.session.add(r); db.session.flush()
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
    db.session.delete(r); db.session.commit()
    flash("Роль удалена: " + r.name)
    return redirect(url_for("auth.roles_list"))

# --- EKRAN POLZOVATELEY (novoe v 2b-2) --------------------------------------

@auth_bp.route("/users")
@perm("auth.manage_users")
def users_list():
    """Spisok lyudey. Status schitaetsya zdes', chtoby shablon byl prostym."""
    now = datetime.utcnow()
    rows = []
    for u in User.query.order_by(User.username).all():
        if not u.is_active:
            st, cls = "закрыт", "b-red"
        elif u.locked_until and u.locked_until > now:
            st, cls = "заблокирован до " + u.locked_until.strftime("%d.%m %H:%M"), "b-yellow"
        else:
            st, cls = "активен", "b-green"
        rows.append({"u": u, "status": st, "cls": cls})
    audits = AuditLog.query.filter_by(table_name="user").order_by(AuditLog.timestamp.desc()).limit(15).all()
    return render_template("auth/users.html", rows=rows, audits=audits, now=now)

@auth_bp.route("/users/new")
@perm("auth.manage_users")
def users_new():
    roles = Role.query.order_by(Role.name).all()
    return render_template("auth/users_edit.html", user=None, roles=roles, is_self=False)

@auth_bp.route("/users/<int:uid>/edit")
@perm("auth.manage_users")
def users_edit(uid):
    u = User.query.get_or_404(uid)
    roles = Role.query.order_by(Role.name).all()
    return render_template("auth/users_edit.html", user=u, roles=roles,
                           is_self=(u.id == current_user.id))

@auth_bp.route("/users/save", methods=["POST"])
@perm("auth.manage_users")
def users_save():
    uid = request.form.get("id", type=int)
    username = (request.form.get("username") or "").strip()
    full_name = (request.form.get("full_name") or "").strip()
    email = (request.form.get("email") or "").strip()
    role_id = request.form.get("role_id", type=int)
    is_active = bool(request.form.get("is_active"))
    must_change = bool(request.form.get("must_change"))

    if not username:
        flash("Укажите логин."); return redirect(url_for("auth.users_list"))
    role = Role.query.get(role_id) if role_id else None
    if not role:
        flash("Выберите роль."); return redirect(url_for("auth.users_list"))

    if uid:
        u = User.query.get_or_404(uid)
        if u.id == current_user.id:
            # sebe mozhno menyat' tolko imya i pochtu - zashchita ot samoblokirovki
            u.full_name = full_name; u.email = email
            db.session.commit()
            _audit("edit_self", "изменил свои имя/почту")
            flash("Свои роль и статус изменить нельзя (защита от самоблокировки). Имя и почта обновлены.")
            return redirect(url_for("auth.users_list"))
        dup = User.query.filter(db.func.lower(User.username) == username.lower(), User.id != u.id).first()
        if dup:
            flash("Логин уже занят."); return redirect(url_for("auth.users_edit", uid=u.id))
        # zashchita poslednego admina: nelzya razzhalovat' ili zakryt' ego
        if _is_last_active_admin(u) and (role.name != "admin" or not is_active):
            flash("Нельзя разжаловать или закрыть последнего активного администратора.")
            return redirect(url_for("auth.users_edit", uid=u.id))
        u.username = username; u.full_name = full_name; u.email = email
        u.role_id = role.id; u.is_active = is_active; u.must_change_password = must_change
        db.session.commit()
        _audit("edit", "изменил пользователя " + username + " (роль: " + role.name + ")")
        flash("Пользователь обновлён: " + username)
    else:
        pw = request.form.get("password") or ""
        if len(pw) < 4:
            flash("Пароль слишком короткий (мин. 4)."); return redirect(url_for("auth.users_new"))
        dup = User.query.filter(db.func.lower(User.username) == username.lower()).first()
        if dup:
            flash("Логин уже занят."); return redirect(url_for("auth.users_new"))
        u = User(username=username, full_name=full_name, email=email,
                 password_hash=hash_password(pw), role_id=role.id,
                 auth_source="local", is_active=is_active,
                 must_change_password=must_change if must_change else True)
        db.session.add(u); db.session.commit()
        _audit("create", "создал пользователя " + username + " (роль: " + role.name + ")")
        flash("Пользователь создан: " + username)
    return redirect(url_for("auth.users_list"))

@auth_bp.route("/users/<int:uid>/toggle", methods=["POST"])
@perm("auth.manage_users")
def users_toggle(uid):
    u = User.query.get_or_404(uid)
    if u.id == current_user.id:
        flash("Нельзя закрыть или открыть доступ самому себе.")
        return redirect(url_for("auth.users_list"))
    if _is_last_active_admin(u):
        flash("Нельзя закрыть последнего активного администратора.")
        return redirect(url_for("auth.users_list"))
    u.is_active = not u.is_active
    db.session.commit()
    _audit("toggle", ("открыл доступ" if u.is_active else "закрыл доступ") + " пользователю " + u.username)
    flash(("Доступ открыт: " if u.is_active else "Доступ закрыт: ") + u.username)
    return redirect(url_for("auth.users_list"))

@auth_bp.route("/users/<int:uid>/reset-password", methods=["POST"])
@perm("auth.manage_users")
def users_reset(uid):
    u = User.query.get_or_404(uid)
    pw = request.form.get("password") or ""
    if len(pw) < 4:
        flash("Пароль слишком короткий (мин. 4).")
        return redirect(url_for("auth.users_edit", uid=u.id))
    u.password_hash = hash_password(pw)
    u.must_change_password = True
    u.failed_attempts = 0; u.locked_until = None   # sbros snimaet i vremennuyu blokirovku
    db.session.commit()
    _audit("reset_password", "сбросил пароль пользователю " + u.username)
    flash("Пароль сброшен для " + u.username + ". При входе потребуется смена.")
    return redirect(url_for("auth.users_edit", uid=u.id))

@auth_bp.route("/users/<int:uid>/delete", methods=["POST"])
@perm("auth.manage_users")
def users_delete(uid):
    u = User.query.get_or_404(uid)
    if u.id == current_user.id:
        flash("Нельзя удалить собственную учётную запись.")
        return redirect(url_for("auth.users_list"))
    if _is_last_active_admin(u):
        flash("Нельзя удалить последнего активного администратора.")
        return redirect(url_for("auth.users_list"))
    name = u.username
    db.session.delete(u); db.session.commit()
    _audit("delete", "удалил пользователя " + name)
    flash("Пользователь удалён: " + name)
    return redirect(url_for("auth.users_list"))

@auth_bp.route("/login-log")
@perm("auth.manage_users")
def login_log():
    """Zhurnal vkhodov: kogda, kto, uspeshno li, s kakogo IP."""
    q = (request.args.get("q") or "").strip()
    query = LoginLog.query
    if q:
        query = query.filter(LoginLog.username.ilike("%" + q + "%"))
    logs = query.order_by(LoginLog.timestamp.desc()).limit(300).all()
    return render_template("auth/login_log.html", logs=logs, q=q)
