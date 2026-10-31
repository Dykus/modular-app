"""Yadro avtorizacii: proverka parolya, glava prav, dekorator zamykaniya."""
from functools import wraps
from flask import current_app, redirect, url_for, request, render_template
from flask_login import current_user
from flask_login import LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
import json

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Войдите в систему, чтобы продолжить."
login_manager.session_protection = "strong"

@login_manager.user_loader
def load_user(uid):
    """Flask-Login zvonyt syuda pri kazhdom zaprose, chtoby ponjat',
    kto seychas vooshel po cookie-sessii. Vozvraschaem User po id."""
    from core.models import User
    try:
        return User.query.get(int(uid))
    except (TypeError, ValueError):
        return None

def hash_password(pw):
    """Prevraschaet parol v neprouchit'yemyy otpechatok (hesh).
    My NIKOGDA ne hranim paroli v otkrytom vide - tolko hesh."""
    return generate_password_hash(pw)

def verify_password(user, pw):
    """Sveryaet vvedennyi parol s heshom polzovatelya. True/False."""
    return check_password_hash(user.password_hash, pw)

def role_immutable_list(role):
    """Spisok prav roli, kotorye NELZYA snyat (zashchita ot samoblokirovki)."""
    if not role or not role.immutable_perms:
        return []
    try:
        return json.loads(role.immutable_perms)
    except Exception:
        return []

def user_has_perm(user, code):
    """GLAVNAYA FUNKCIYA: umet li dannyi chelovek pravo `code`?
      - net cheloveka -> Net.  - superuser (admin) -> Vsegda Da.
      - inache smotrim v tablicu role_permission: est' li zapisi (rol', pravo)."""
    if user is None:
        return False
    if user.is_superuser:
        return True
    if user.role_id is None:
        return False
    from core.models import RolePermission
    return RolePermission.query.filter_by(role_id=user.role_id, perm=code).first() is not None

def user_perm_codes(user):
    """MNOZHESTVO kodov prav roli (dlya filtra menu). None = superuser = vse."""
    if user is None:
        return set()
    if user.is_superuser:
        return None
    if user.role_id is None:
        return set()
    from core.models import RolePermission
    return {rp.perm for rp in RolePermission.query.filter_by(role_id=user.role_id).all()}

def perm(code):
    """DEKORATOR: zamykaet stranicu na pravo. Primer: @perm("feedback.create")

    Kak rabotaet, po shagam:
      1) Avtorizaciya VYKL and pravo NE sistemnoe (ne "auth.") -> propuskaem
         kogo ugodno (rezhim "kak ранше, vse otкрыто po seti"). Sistemnye
         prava auth.* proveryaemsya VSEGDA - bez parolya lyud'mi ne upravlyayut.
      2) Ne vooshel -> na stranicu vhoda.
      3) Vooshel, no prava net -> RISUEM STRANICU-OTKAZ S OPISANIEM prava,
         kotornogo ne xvataet (etovo i est' "ponyatno ne prodvinutom").
      4) Inache -> vypolnyaem stranicu.
    """
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            content_right = not code.startswith("auth.")
            if content_right and not current_app.config.get("AUTH_ENABLED"):
                return f(*args, **kwargs)
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.path))
            if not user_has_perm(current_user, code):
                # Berem chelovecheskoe opisanie prava iz reestra (sobran v collect()).
                from core.permissions import ALL_PERMS
                group, desc = ALL_PERMS.get(code, ("Без категории", code))
                return render_template(
                    "403.html",
                    perm_code=code, perm_group=group, perm_desc=desc,
                ), 403
            return f(*args, **kwargs)
        return wrapper
    return deco
