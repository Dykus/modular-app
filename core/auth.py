"""Yadro avtorizacii: proverka parolya, glava prav, dekorator zamykaniya."""
from functools import wraps
from flask import current_app, redirect, url_for, request, abort
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
    """Spisok prav roli, kotorye NELZYA snyat (zashchita ot samoblokirovki).
    Lezhit v pole immutable_perms kak JSON-stroka."""
    if not role or not role.immutable_perms:
        return []
    try:
        return json.loads(role.immutable_perms)
    except Exception:
        return []

def user_has_perm(user, code):
    """GLAVNAYA FUNKCIYA: umet li dannyi chelovek pravo `code`?

    Logika prostaya:
      - net cheloveka (ne vooshel) -> Net.
      - superuser (rol' admin) -> Vsegda Da, emu mozhno vse.
      - inache smotrim v tablicu role_permission: est' li zapisi
        (rol' cheloveka, eto pravo). Est' -> Da, net -> Net.
    """
    if user is None:
        return False
    if user.is_superuser:
        return True
    if user.role_id is None:
        return False
    from core.models import RolePermission
    return RolePermission.query.filter_by(role_id=user.role_id, perm=code).first() is not None

def user_perm_codes(user):
    """Vozvraschaet MNOZHESTVO kodov prav roli cheloveka (dlya filtra menu).
    Dlya superusera vozvraschaet None = 'u nego voobshche vse prava'."""
    if user is None:
        return set()
    if user.is_superuser:
        return None
    if user.role_id is None:
        return set()
    from core.models import RolePermission
    return {rp.perm for rp in RolePermission.query.filter_by(role_id=user.role_id).all()}

def perm(code):
    """DEKORATOR: stavi syuda nad funciy-stranicey, i ona zamykaetsya na pravo.

    Primenenie:  @perm("feedback.create")  nad  def add(): ...

    Kak on rabotaet, shag za shagom (etovo vazhno ponyat'):
      1) Esli avtorizaciya VYKLYUCHENA (safety-switch off) i pravo NE sistemnoe
         (ne nachinaetsya s "auth.") -> propuskaem kogo ugodno. Eto i est'
         rezhim 'kak ранше, vse otкрыто po seti'. No sistemnye prava (auth.*)
         proveryaemsya VSEGDA - upravlyat' lyud'mi bez parolya nelzya nikogda.
      2) Esli chelovek ne vooshel -> otpravlyaem na stranicu vhoda.
      3) Esli vooshel, no prava net -> stranka 403 'Dostup zapreshchen'.
      4) Inache -> vypolnyaem stranicu kak obychno.
    """
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            content_right = not code.startswith("auth.")
            if content_right and not current_app.config.get("AUTH_ENABLED"):
                return f(*args, **kwargs)          # shag 1: otkrytyi rezhim
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.path))  # shag 2
            if not user_has_perm(current_user, code):
                abort(403)                          # shag 3
            return f(*args, **kwargs)               # shag 4
        return wrapper
    return deco
