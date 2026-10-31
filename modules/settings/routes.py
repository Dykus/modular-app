from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.app import db
from core.auth import perm
import json
from core.registry import AVAILABLE_MODULES
from modules.settings.models import Setting, SettingLog, get_setting, get_bool, set_setting

settings_bp = Blueprint("settings", __name__, url_prefix="/settings", template_folder="templates")

def _current_enabled():
    raw = get_setting("enabled_modules", "")
    if raw.strip():
        try:
            return set(json.loads(raw))
        except Exception:
            pass
    return {m["key"] for m in AVAILABLE_MODULES}

@settings_bp.route("/")
@perm("settings.view")
def index():
    logs = SettingLog.query.order_by(SettingLog.timestamp.desc()).limit(100).all()
    return render_template("settings/settings.html",
                           modules=AVAILABLE_MODULES,
                           enabled=_current_enabled(),
                           app_title=get_setting("app_title", "Модульное приложение для производства"),
                           app_footer=get_setting("app_footer", ""),
                           theme=get_setting("theme", "light"),
                           require_comment=get_bool("feedback_require_comment_on_reject", False),
                           auth_enabled=get_bool("auth_enabled", False),
                           lock_threshold=get_setting("lock_threshold", "5"),
                           lock_minutes=get_setting("lock_minutes", "15"),
                           logs=logs)

@settings_bp.route("/save", methods=["POST"])
@perm("settings.manage")
def save():
    who = (request.form.get("who") or "без имени").strip()
    set_setting("app_title",  (request.form.get("app_title") or "").strip() or "Модульное приложение", who)
    set_setting("app_footer", (request.form.get("app_footer") or "").strip(), who)
    set_setting("theme",      request.form.get("theme") or "light", who)
    mods = request.form.getlist("modules")
    set_setting("enabled_modules", json.dumps(mods, ensure_ascii=False), who)
    set_setting("feedback_require_comment_on_reject", "1" if request.form.get("require_comment") else "0", who)
    set_setting("auth_enabled", "1" if request.form.get("auth_enabled") else "0", who)
    lt = (request.form.get("lock_threshold") or "5").strip()
    lm = (request.form.get("lock_minutes") or "15").strip()
    set_setting("lock_threshold", lt.lstrip("-") or "5", who)
    set_setting("lock_minutes", lm.lstrip("-") or "15", who)
    flash("Настройки сохранены. Название, тема, требования и авторизация применяются сразу. Включение/выключение модулей — после перезапуска run.py.")
    return redirect(url_for("settings.index"))
