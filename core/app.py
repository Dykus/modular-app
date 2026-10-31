"""Yadro - sozdanie Flask app + avtorizaciya + dinamicheskie moduli"""
from flask import Flask, url_for, redirect, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user
import os, json, importlib
import config
from core.registry import AVAILABLE_MODULES
from core.auth import login_manager, user_has_perm, user_perm_codes
from core.permissions import collect, MODULE_PERMS

db = SQLAlchemy()

AUTH_WHITELIST = {"auth.login", "auth.do_login", "auth.logout",
                  "auth.change_password", "auth.do_change_password", "static"}

def create_app():
    app = Flask(__name__,
                template_folder="../web/templates",
                static_folder="../web/static")
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    login_manager.init_app(app)
    os.makedirs(config.DATA_DIR, exist_ok=True)

    collect()

    from modules.feedback import models as feedback_models  # noqa
    from modules.settings import models as settings_models  # noqa
    from modules.changelog import models as changelog_models  # noqa
    from modules.versions import models as versions_models  # noqa
    from modules.help import models as help_models  # noqa
    from modules.manual import models as manual_models  # noqa
    from core import models as core_models  # noqa

    with app.app_context():
        db.create_all()
        from core.seed import run_seed
        run_seed()
        from modules.changelog.models import seed as seed_changelog
        from modules.versions.models import seed as seed_versions
        from modules.help.models import seed as seed_help
        from modules.manual.models import seed as seed_manual
        seed_changelog(); seed_versions(); seed_help(); seed_manual()
        from modules.settings.models import get_setting, get_bool
        raw = get_setting("enabled_modules", "")
        if raw.strip():
            try:
                enabled = set(json.loads(raw))
            except Exception:
                enabled = {m["key"] for m in AVAILABLE_MODULES}
        else:
            enabled = {m["key"] for m in AVAILABLE_MODULES}
        app.config["AUTH_ENABLED"] = get_bool("auth_enabled", False)

    from web.routes import main_bp
    app.register_blueprint(main_bp)
    from core.auth_routes import auth_bp
    app.register_blueprint(auth_bp)
    from modules.settings.routes import settings_bp
    app.register_blueprint(settings_bp)

    registered = {}
    for m in AVAILABLE_MODULES:
        if m["key"] in enabled:
            mod = importlib.import_module(m["import_path"])
            app.register_blueprint(getattr(mod, m["bp_attr"]))
            registered[m["key"]] = m
    app.config["ENABLED_MODULES"] = registered

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.before_request
    def guard():
        if not app.config.get("AUTH_ENABLED"):
            return None
        ep = request.endpoint
        if ep in AUTH_WHITELIST:
            return None
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.must_change_password and ep not in (
                "auth.change_password", "auth.do_change_password", "auth.logout"):
            return redirect(url_for("auth.change_password"))
        return None

    @app.context_processor
    def inject_settings():
        from modules.settings.models import get_setting
        from modules.versions.models import Release
        em = app.config.get("ENABLED_MODULES", {})
        auth_on = app.config.get("AUTH_ENABLED", False)
        if not auth_on:
            menu = [{"name": v["name"], "url": url_for(v["endpoint"])} for v in em.values()]
        elif not current_user.is_authenticated:
            menu = []
        else:
            codes = user_perm_codes(current_user)
            menu = []
            for v in em.values():
                need = MODULE_PERMS.get(v["key"], [])
                if codes is None or (need and (set(need) & codes)):
                    menu.append({"name": v["name"], "url": url_for(v["endpoint"])})
        cur = Release.query.filter_by(is_current=True).first()
        def can(code):
            return user_has_perm(current_user._get_current_object() if current_user.is_authenticated else None, code)
        return {
            "app_title":  get_setting("app_title", "Модульное приложение для производства"),
            "app_footer": get_setting("app_footer", "ядро + модули | Flask + SQLAlchemy"),
            "app_version": cur.version if cur else "dev",
            "theme":      get_setting("theme", "light"),
            "menu":       menu,
            "auth_enabled": auth_on,
            "can":        can,
        }

    return app
