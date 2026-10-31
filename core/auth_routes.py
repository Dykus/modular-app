"""Stranicy vhoda, profilya, smeny parolya, Rolei, Polzovateley + AD-logika."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from core.app import db
from core.auth import verify_password, hash_password, role_immutable_list, perm
from core.models import User, Role, RolePermission, LoginLog, AuditLog
from core.permissions import ALL_PERMS, PERM_GROUPS
from core.settings_helper import get_int
from core import ad_provider
from modules.settings.models import get_setting, get_bool
from datetime import datetime, timedelta

auth_bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder="../web/templates")

def _ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "")[:64]

def _log(username, uid, success, reason="", provider="local"):
    db.session.add(LoginLog(username=username, user_id=uid, success=success,
                            ip=_ip(), provider=provider, reason=reason))
    db.session.commit()

def _audit(action, detail):
    db.session.add(AuditLog(user_id=current_user.id, action=action,
                            table_name="user", record_id=None, changes=detail))
    db.session.commit()

def _admin_role():
    return Role.query.filter_by(name="admin").first()

def _is_last_active_admin(u):
    ar = _admin_role()
    if not ar or u.role_id != ar.id or not u.is_active:
        return False
    return User.query.filter_by(role_id=ar.id, is_active=True).count() <= 1

# --- Vhod s AD-logikoy ------------------------------------------------------

@auth_bp.route("/login", methods=["GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    ad_on = get_bool("ad_enabled", False) and ad_provider.ldap3_available()
    return render_template("auth/login.html", ad_on=ad_on)

@auth_bp.route("/login", methods=["POST"])
def do_login():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    user = User.query.filter(db.func.lower(User.username) == username.lower()).first()

    ad_on = get_bool("ad_enabled", False)
    fallback_ok = get_bool("ad_allow_fallback_local", True)

    def _lock(user):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        thr = get_int("lock_threshold", 5)
        if user.failed_attempts >= thr:
            mins = get_int("lock_minutes", 15)
            user.locked_until = datetime.utcnow() + timedelta(minutes=mins)
            user.failed_attempts = 0
        db.session.commit()

    # --- SLUCHAI A: polzovatel NAYDEN v BD ---
    if user:
        if not user.is_active:
            _log(username, user.id, False, "закрыт", provider=user.auth_source or "local")
            flash("Пользователь закрыт. Обратитесь к администратору.")
            return redirect(url_for("auth.login"))
        if user.locked_until and user.locked_until > datetime.utcnow():
            _log(username, user.id, False, "заблокирован", provider=user.auth_source or "local")
            flash("Вход временно заблокирован.")
            return redirect(url_for("auth.login"))

        # A.1: auth_source == "ad" -> tolko AD
        if user.auth_source == "ad":
            if not ad_on:
                _log(username, user.id, False, "AD выключен, а учётка доменная", provider="ad")
                flash("Учётка доменная, но AD сейчас выключен. Обратитесь к администратору.")
                return redirect(url_for("auth.login"))
            ok, info = ad_provider.verify_ad_password(username, password)
            if ok is None:
                _log(username, user.id, False, "AD недоступен: " + str(info), provider="ad")
                flash("Не удалось связаться с AD. Попробуйте позже или обратитесь к администратору.")
                return redirect(url_for("auth.login"))
            if not ok:
                _lock(user)
                _log(username, user.id, False, "неверный пароль AD", provider="ad")
                flash("Неверный логин или пароль.")
                return redirect(url_for("auth.login"))
            # uspeh
            user.failed_attempts = 0; user.locked_until = None; user.last_login = datetime.utcnow()
            # obnovim imya/email iz AD, esli priшли
            if isinstance(info, dict):
                if info.get("fullname"): user.full_name = info["fullname"]
                if info.get("email"):    user.email    = info["email"]
            db.session.commit()
            login_user(user, remember=bool(request.form.get("remember")))
            _log(username, user.id, True, provider="ad")
            return redirect(request.args.get("next") or url_for("main.index"))

        # A.2: auth_source == "local" -> lokalno
        if not verify_password(user, password):
            # dopolnitelno: esli AD vklyuchen, proveryaem tam - vdruk smenilsya
            if ad_on:
                ok, info = ad_provider.verify_ad_password(username, password)
                if ok is True:
                    # pereveli na AD? avtomatom: istocnik=ad, parol lokalnyi bolshe ne nuzhen
                    user.auth_source = "ad"
                    user.failed_attempts = 0; user.locked_until = None
                    user.last_login = datetime.utcnow()
                    if isinstance(info, dict):
                        if info.get("fullname"): user.full_name = info["fullname"]
                        if info.get("email"):    user.email    = info["email"]
                    db.session.commit()
                    login_user(user, remember=bool(request.form.get("remember")))
                    _log(username, user.id, True, "автоматический перевод на AD", provider="ad")
                    flash("Ваша учётка теперь доменная: вход через AD.")
                    return redirect(request.args.get("next") or url_for("main.index"))
            _lock(user)
            _log(username, user.id, False, "неверный пароль", provider="local")
            flash("Неверный логин или пароль.")
            return redirect(url_for("auth.login"))
        # lokalnyi uspeh
        user.failed_attempts = 0; user.locked_until = None; user.last_login = datetime.utcnow()
        db.session.commit()
        login_user(user, remember=bool(request.form.get("remember")))
        _log(username, user.id, True, provider="local")
        return redirect(request.args.get("next") or url_for("main.index"))

    # --- SLUCHAI B: polzovatelya NET v BD ---
    if not ad_on:
        _log(username, None, False, "нет такого пользователя")
        flash("Неверный логин или пароль.")
        return redirect(url_for("auth.login"))

    ok, info = ad_provider.verify_ad_password(username, password)
    if ok is None:
        _log(username, None, False, "AD недоступен при первом входе: " + str(info), provider="ad")
        flash("Не удалось связаться с AD. Попробуйте позже.")
        return redirect(url_for("auth.login"))
    if not ok:
        _log(username, None, False, "нет такого пользователя / неверный пароль AD", provider="ad")
        flash("Неверный логин или пароль.")
        return redirect(url_for("auth.login"))

    # PROVISIONING: sozdaem novogo polzovatelya iz AD
    def_role_name = get_setting("ad_default_role", "staff")
    role = Role.query.filter_by(name=def_role_name).first() or Role.query.filter_by(name="staff").first()
    if not role:
        _log(username, None, False, "не найдена роль по умолчанию для AD-пользователей")
        flash("Ошибка конфигурации: не найдена роль по умолчанию для AD. Обратитесь к администратору.")
        return redirect(url_for("auth.login"))

    new_user = User(
        username=username,
        full_name=(info.get("fullname") or "") if isinstance(info, dict) else "",
        email=(info.get("email") or "") if isinstance(info, dict) else "",
        password_hash="",                 # u AD-polzovatelya net lokalnogo parolya
        role_id=role.id,
        auth_source="ad",
        is_active=True,
        must_change_password=False,
    )
    db.session.add(new_user); db.session.commit()
    new_user.last_login = datetime.utcnow()
    db.session.commit()
    login_user(new_user, remember=bool(request.form.get("remember")))
    _log(username, new_user.id, True, "автосоздан из AD (роль: " + role.name + ")", provider="ad")
    # audit
    admin = User.query.filter_by(username="admin").first()
    db.session.add(AuditLog(user_id=admin.id if admin else None, action="provision_ad",
                            table_name="user", record_id=new_user.id,
                            changes="автосоздан из AD с ролью " + role.name))
    db.session.commit()
    flash("Учётка создана из AD (роль: " + role.name + "). При необходимости администратор изменит роль.")
    return redirect(url_for("main.index"))

# --- Vyhod / Profil / Smena parolya ----------------------------------------

@auth_bp.route("/logout")
@login_required
def logout():
    _log(current_user.username, current_user.id, True, "выход",
         provider=current_user.auth_source or "local")
    logout_user()
    flash("Вы вышли из системы.")
    return redirect(url_for("auth.login"))

@auth_bp.route("/profile")
@login_required
def profile():
    return render_template("auth/profile.html")

@auth_bp.route("/change-password", methods=["GET"])
def change_password():
    # U AD-polzovateley smena parolya - v samom AD, ne u nas
    if current_user.auth_source == "ad":
        flash("Ваш пароль управляется в Active Directory. Меняйте его там (Ctrl+Alt+Del → Сменить пароль).")
        return redirect(url_for("auth.profile"))
    return render_template("auth/change_password.html", forced=current_user.must_change_password)

@auth_bp.route("/change-password", methods=["POST"])
@login_required
def do_change_password():
    if current_user.auth_source == "ad":
        flash("Пароль доменных пользователей меняется в AD, а не здесь.")
        return redirect(url_for("auth.profile"))
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

# --- Rolei (iz 2b-1, bez izmeneniy) ----------------------------------------

@auth_bp.route("/roles")
@perm("auth.manage_roles")
def roles_list():
    roles = Role.query.order_by(Role.is_system.desc(), Role.id).all()
    rows = [{"role": r, "users_count": r.users.count(),
             "perms": {rp.perm for rp in r.permissions}} for r in roles]
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
    return render_template("auth/roles_edit.html", role=r,
                           checked={rp.perm for rp in r.permissions},
                           all_perms=ALL_PERMS, perm_groups=PERM_GROUPS,
                           immutable=set(role_immutable_list(r)))

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
            flash("Нельзя изменить собственную роль.")
            return redirect(url_for("auth.roles_list"))
        if Role.query.filter(Role.name == name, Role.id != r.id).first():
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
    valid = {c for c in chosen if c in ALL_PERMS}
    existing = {rp.perm: rp for rp in r.permissions}
    for code, rp in list(existing.items()):
        if code not in valid: db.session.delete(rp)
    for code in valid:
        if code not in existing:
            db.session.add(RolePermission(role_id=r.id, perm=code))
    db.session.commit()
    flash(("Роль обновлена: " if rid else "Роль создана: ") + r.name)
    return redirect(url_for("auth.roles_list"))

@auth_bp.route("/roles/<int:rid>/delete", methods=["POST"])
@perm("auth.manage_roles")
def roles_delete(rid):
    r = Role.query.get_or_404(rid)
    if r.is_system: flash("Системную роль удалить нельзя."); return redirect(url_for("auth.roles_list"))
    if r.users.count() > 0: flash("Нельзя удалить роль: на ней есть пользователи."); return redirect(url_for("auth.roles_list"))
    if current_user.role_id == r.id: flash("Нельзя удалить собственную роль."); return redirect(url_for("auth.roles_list"))
    db.session.delete(r); db.session.commit()
    flash("Роль удалена: " + r.name); return redirect(url_for("auth.roles_list"))

# --- Polzovateli (iz 2b-2, dobavleno: priznak auth_source v edit) ----------

@auth_bp.route("/users")
@perm("auth.manage_users")
def users_list():
    now = datetime.utcnow()
    rows = []
    for u in User.query.order_by(User.username).all():
        if not u.is_active: st, cls = "закрыт", "b-red"
        elif u.locked_until and u.locked_until > now:
            st, cls = "заблокирован до " + u.locked_until.strftime("%d.%m %H:%M"), "b-yellow"
        else: st, cls = "активен", "b-green"
        rows.append({"u": u, "status": st, "cls": cls})
    audits = AuditLog.query.filter_by(table_name="user").order_by(AuditLog.timestamp.desc()).limit(15).all()
    return render_template("auth/users.html", rows=rows, audits=audits, now=now)

@auth_bp.route("/users/new")
@perm("auth.manage_users")
def users_new():
    return render_template("auth/users_edit.html", user=None,
                           roles=Role.query.order_by(Role.name).all(),
                           is_self=False, ad_on=get_bool("ad_enabled", False))

@auth_bp.route("/users/<int:uid>/edit")
@perm("auth.manage_users")
def users_edit(uid):
    u = User.query.get_or_404(uid)
    return render_template("auth/users_edit.html", user=u,
                           roles=Role.query.order_by(Role.name).all(),
                           is_self=(u.id == current_user.id),
                           ad_on=get_bool("ad_enabled", False))

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
    auth_source = (request.form.get("auth_source") or "local").strip()
    if auth_source not in ("local", "ad"):
        auth_source = "local"

    if not username: flash("Укажите логин."); return redirect(url_for("auth.users_list"))
    role = Role.query.get(role_id) if role_id else None
    if not role: flash("Выберите роль."); return redirect(url_for("auth.users_list"))

    if uid:
        u = User.query.get_or_404(uid)
        if u.id == current_user.id:
            u.full_name = full_name; u.email = email
            db.session.commit()
            _audit("edit_self", "изменил свои имя/почту")
            flash("Свою роль и статус изменить нельзя. Имя и почта обновлены.")
            return redirect(url_for("auth.users_list"))
        if User.query.filter(db.func.lower(User.username) == username.lower(), User.id != u.id).first():
            flash("Логин уже занят."); return redirect(url_for("auth.users_edit", uid=u.id))
        if _is_last_active_admin(u) and (role.name != "admin" or not is_active):
            flash("Нельзя разжаловать/закрыть последнего активного администратора.")
            return redirect(url_for("auth.users_edit", uid=u.id))
        u.username = username; u.full_name = full_name; u.email = email
        u.role_id = role.id; u.is_active = is_active; u.must_change_password = must_change
        u.auth_source = auth_source
        if auth_source == "ad":
            u.password_hash = ""
        db.session.commit()
        _audit("edit", "изменил " + username + " (роль: " + role.name + ", источник: " + auth_source + ")")
        flash("Пользователь обновлён: " + username)
    else:
        if User.query.filter(db.func.lower(User.username) == username.lower()).first():
            flash("Логин уже занят."); return redirect(url_for("auth.users_new"))
        if auth_source == "ad":
            u = User(username=username, full_name=full_name, email=email,
                     password_hash="", role_id=role.id, auth_source="ad",
                     is_active=is_active, must_change_password=False)
        else:
            pw = request.form.get("password") or ""
            if len(pw) < 4:
                flash("Пароль слишком короткий (мин. 4)."); return redirect(url_for("auth.users_new"))
            u = User(username=username, full_name=full_name, email=email,
                     password_hash=hash_password(pw), role_id=role.id, auth_source="local",
                     is_active=is_active, must_change_password=must_change if must_change else True)
        db.session.add(u); db.session.commit()
        _audit("create", "создал " + username + " (роль: " + role.name + ", источник: " + auth_source + ")")
        flash("Пользователь создан: " + username)
    return redirect(url_for("auth.users_list"))

@auth_bp.route("/users/<int:uid>/toggle", methods=["POST"])
@perm("auth.manage_users")
def users_toggle(uid):
    u = User.query.get_or_404(uid)
    if u.id == current_user.id: flash("Нельзя закрыть/открыть доступ себе."); return redirect(url_for("auth.users_list"))
    if _is_last_active_admin(u): flash("Нельзя закрыть последнего активного администратора."); return redirect(url_for("auth.users_list"))
    u.is_active = not u.is_active; db.session.commit()
    _audit("toggle", ("открыл" if u.is_active else "закрыл") + " доступ " + u.username)
    flash(("Доступ открыт: " if u.is_active else "Доступ закрыт: ") + u.username)
    return redirect(url_for("auth.users_list"))

@auth_bp.route("/users/<int:uid>/reset-password", methods=["POST"])
@perm("auth.manage_users")
def users_reset(uid):
    u = User.query.get_or_404(uid)
    if u.auth_source == "ad":
        flash("У доменных пользователей пароль меняется в AD, не здесь.")
        return redirect(url_for("auth.users_edit", uid=u.id))
    pw = request.form.get("password") or ""
    if len(pw) < 4:
        flash("Пароль слишком короткий (мин. 4)."); return redirect(url_for("auth.users_edit", uid=u.id))
    u.password_hash = hash_password(pw); u.must_change_password = True
    u.failed_attempts = 0; u.locked_until = None
    db.session.commit()
    _audit("reset_password", "сбросил пароль " + u.username)
    flash("Пароль сброшен для " + u.username + ". При входе потребуется смена.")
    return redirect(url_for("auth.users_edit", uid=u.id))

@auth_bp.route("/users/<int:uid>/delete", methods=["POST"])
@perm("auth.manage_users")
def users_delete(uid):
    u = User.query.get_or_404(uid)
    if u.id == current_user.id: flash("Нельзя удалить себя."); return redirect(url_for("auth.users_list"))
    if _is_last_active_admin(u): flash("Нельзя удалить последнего активного администратора."); return redirect(url_for("auth.users_list"))
    name = u.username
    db.session.delete(u); db.session.commit()
    _audit("delete", "удалил " + name)
    flash("Пользователь удалён: " + name)
    return redirect(url_for("auth.users_list"))

@auth_bp.route("/login-log")
@perm("auth.manage_users")
def login_log():
    q = (request.args.get("q") or "").strip()
    query = LoginLog.query
    if q: query = query.filter(LoginLog.username.ilike("%" + q + "%"))
    logs = query.order_by(LoginLog.timestamp.desc()).limit(300).all()
    return render_template("auth/login_log.html", logs=logs, q=q)
