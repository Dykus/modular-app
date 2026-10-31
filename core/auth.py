"""Yadro avtorizacii: login_manager, proverka parolya, glava prav (zaglushka do Shaga 2)"""
from flask_login import LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
import json

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Voydite v sistemu, chtoby prodlomit."
login_manager.session_protection = "strong"

@login_manager.user_loader
def load_user(uid):
    from core.models import User
    try:
        return User.query.get(int(uid))
    except (TypeError, ValueError):
        return None

def hash_password(pw):
    return generate_password_hash(pw)

def verify_password(user, pw):
    return check_password_hash(user.password_hash, pw)

def role_immutable_list(role):
    if not role or not role.immutable_perms:
        return []
    try:
        return json.loads(role.immutable_perms)
    except Exception:
        return []

def user_has_perm(user, perm):
    """Shag 1: prava eschyo ne razlichayutsya. Superuser vsegda prokhodit.
    Kogda v Shage 2 poyavitsya role_permission - zdes' budet realnaya proverka."""
    if user is None:
        return False
    if user.is_superuser:
        return True
    return True  # do Shaga 2: vsetki vshedshie vidyat vsyo
