from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.app import db
from core.auth import perm
import json
from core.registry import AVAILABLE_MODULES
from core import ad_provider
from core.models import Role
from modules.settings.models import Setting, SettingLog, get_setting, get_bool, set_setting

settings_bp = Blueprint("settings", __name__, url_prefix="/settings", template_folder="templates")

def _current_enabled():
    raw = get_setting("enabled_modules", "")
    if raw.strip():
        try: return set(json.loads(raw))
        except Exception: pass
    return {m["key"] for m in AVAILABLE_MODULES}

@settings_bp.route("/")
@perm("settings.view")
def index():
    logs = SettingLog.query.order_by(SettingLog.timestamp.desc()).limit(100).all()
    roles = Role.query.order_by(Role.name).all()
    return render_template("settings/settings.html",
        modules=AVAILABLE_MODULES, enabled=_current_enabled(),
        app_title=get_setting("app_title", "Модульное приложение для производства"),
        app_footer=get_setting("app_footer", ""),
        theme=get_setting("theme", "light"),
        require_comment=get_bool("feedback_require_comment_on_reject", False),
        auth_enabled=get_bool("auth_enabled", False),
        lock_threshold=get_setting("lock_threshold", "5"),
        lock_minutes=get_setting("lock_minutes", "15"),
        ad_enabled=get_bool("ad_enabled", False),
        ad_host=get_setting("ad_host", ""),
        ad_port=get_setting("ad_port", "389"),
        ad_security=get_setting("ad_security", "none"),
        ad_base_dn=get_setting("ad_base_dn", ""),
        ad_bind_template=get_setting("ad_bind_template", ""),
        ad_search_filter=get_setting("ad_search_filter", "(sAMAccountName=%s)"),
        ad_default_role=get_setting("ad_default_role", "staff"),
        ad_allow_fallback=get_bool("ad_allow_fallback_local", True),
        ad_lib_ok=ad_provider.ldap3_available(),
        roles=roles,
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

    # AD-nastroyki (trebuyut prava auth.security)
    # Esli u tekushchego polzovatelya net auth.security - AD-ne-nastroyki ignorim
    from core.auth import user_has_perm
    from flask_login import current_user
    can_ad = user_has_perm(current_user, "auth.security")
    if can_ad:
        set_setting("ad_enabled", "1" if request.form.get("ad_enabled") else "0", who)
        set_setting("ad_host", (request.form.get("ad_host") or "").strip(), who)
        set_setting("ad_port", (request.form.get("ad_port") or "389").strip(), who)
        sec = (request.form.get("ad_security") or "none").strip()
        if sec not in ("none", "starttls", "ldaps"): sec = "none"
        set_setting("ad_security", sec, who)
        set_setting("ad_base_dn", (request.form.get("ad_base_dn") or "").strip(), who)
        set_setting("ad_bind_template", (request.form.get("ad_bind_template") or "").strip(), who)
        set_setting("ad_search_filter", (request.form.get("ad_search_filter") or "(sAMAccountName=%s)").strip(), who)
        def_role = (request.form.get("ad_default_role") or "staff").strip()
        set_setting("ad_default_role", def_role, who)
        set_setting("ad_allow_fallback_local", "1" if request.form.get("ad_allow_fallback") else "0", who)

    flash("Настройки сохранены." + ("" if can_ad else " Раздел AD не сохранён: нет права auth.security."))
    return redirect(url_for("settings.index"))
