"""Stranicy vhoda, profilya, smeny parolya + zhurnal vkhodov + blokirovka"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from core.app import db
from core.auth import verify_password, hash_password
from core.models import User, LoginLog
from core.settings_helper import get_int
from datetime import datetime, timedelta

auth_bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder="../web/templates")

def _ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "")[:64]

def _log(username, uid, success, reason="", provider="local"):
    db.session.add(LoginLog(username=username, user_id=uid, success=success,
                            ip=_ip(), provider=provider, reason=reason))
    db.session.commit()

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
        _log(username, None, False, "net takogo polzovatelya")
        flash("Nevershnyy login ili parol."); return redirect(url_for("auth.login"))
    if not user.is_active:
        _log(username, user.id, False, "zakryt")
        flash("Polzovatel zakryt. Obratites k administratoru."); return redirect(url_for("auth.login"))
    if user.locked_until and user.locked_until > datetime.utcnow():
        _log(username, user.id, False, "zablokirovan")
        flash("Vkhod vremenno zablokirovan posle neskolkih neudachnyh popytok."); return redirect(url_for("auth.login"))
    if not verify_password(user, password):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        thr = get_int("lock_threshold", 5)
        if user.failed_attempts >= thr:
            mins = get_int("lock_minutes", 15)
            user.locked_until = datetime.utcnow() + timedelta(minutes=mins)
            user.failed_attempts = 0
        db.session.commit()
        _log(username, user.id, False, "nevernyy parol")
        flash("Nevershnyy login ili parol."); return redirect(url_for("auth.login"))
    user.failed_attempts = 0; user.locked_until = None; user.last_login = datetime.utcnow()
    db.session.commit()
    login_user(user, remember=bool(request.form.get("remember")))
    _log(username, user.id, True)
    nxt = request.args.get("next")
    return redirect(nxt if nxt and nxt.startswith("/") else url_for("main.index"))

@auth_bp.route("/logout")
@login_required
def logout():
    _log(current_user.username, current_user.id, True, "vykhod")
    logout_user()
    flash("Vy vyshli iz sistemy.")
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
        flash("Staryy parol neveren."); return redirect(url_for("auth.change_password"))
    if len(new) < 4:
        flash("Novyy parol slishkom korotkiy (min. 4)."); return redirect(url_for("auth.change_password"))
    if new != rep:
        flash("Paroli ne sovpadayut."); return redirect(url_for("auth.change_password"))
    current_user.password_hash = hash_password(new)
    current_user.must_change_password = False
    db.session.commit()
    flash("Parol izmenen.")
    return redirect(url_for("auth.profile"))
