"""Yadro - sozdanie Flask app + avtorizaciya + dinamicheskie moduli."""
from flask import Flask, url_for, redirect, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user
import os, json, importlib
import config
from core.registry import AVAILABLE_MODULES, SYSTEM_MODULE_KEYS
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

    # VAZHNO (fiks chistogo starta): modeli SISTEMNYH moduley (settings)
    # tozhe importiruyutsya DO create_all. Inache na pustoy baze net
    # tablic setting/setting_log, i seed.py padaet s "no such table: setting".
    model_keys = [m["key"] for m in AVAILABLE_MODULES] + list(SYSTEM_MODULE_KEYS)
    for key in model_keys:
        try:
            importlib.import_module("modules.%s.models" % key)
        except ModuleNotFoundError:
            pass
        except Exception as e:
            print("PREDUPREZHDENIE: models modulya %s ne zagruzilis: %s" % (key, e))
    from core import models as core_models  # noqa
    # dvoynaya strahovka: settings vsegda do create_all, dazhe esli reestr izmenitsya
    from modules.settings import models as settings_models  # noqa

    with app.app_context():
        db.create_all()
        from core.seed import run_seed
        run_seed()
        try:
            from modules.versions import docs_seed as _ds
            _h, _m = _ds.apply()
            print("  ДОКУМЕНТАЦИЯ: статей справки %d, разделов руководства %d" % (_h, _m), flush=True)
        except Exception as _e:
            print("PREDUPREZHDENIE: документация не применена: %s" % _e, flush=True)
        try:
            from modules.versions import history_seed as _hs
            _r, _c = _hs.apply()
            if _r or _c:
                print("  ISTORIYA: dobavleno relizov %d, zapisey zhurnala %d" % (_r, _c), flush=True)
        except Exception as _e:
            print("PREDUPREZHDENIE: istoriya relizov ne primenena: %s" % _e, flush=True)
        for m in AVAILABLE_MODULES:
            try:
                mod = importlib.import_module("modules.%s.models" % m["key"])
                if hasattr(mod, "seed"):
                    mod.seed()
            except Exception:
                pass
        from modules.settings.models import get_setting, get_bool
        raw = get_setting("enabled_modules", "")
        if raw.strip():
            try:
                enabled = set(json.loads(raw))
            except Exception:
                enabled = {m["key"] for m in AVAILABLE_MODULES}
        else:
            enabled = set()
            for m in AVAILABLE_MODULES:
                pas = m.get("passport")
                if pas is None:
                    enabled.add(m["key"])
                elif pas.get("default_enabled", False):
                    enabled.add(m["key"])
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
            try:
                mod = importlib.import_module(m["import_path"])
                app.register_blueprint(getattr(mod, m["bp_attr"]))
                registered[m["key"]] = m
            except Exception as e:
                print("PREDUPREZHDENIE: modul %s NE zaregistrirovan (bitoy kod?): %s" % (m["key"], e))
                print("  Programma prodolzhaet rabotat bez nego. Isprav modul i perezapusti.")
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

        # ustoychivoe menyu: esli endpoint ne stroitsya - punkt propuskaetsya
        # s preduprezhdeniem, a ne valit vse stranicy sayta (BuildError).
        def _safe_url(name, endpoint):
            try:
                return url_for(endpoint)
            except Exception as e:
                print("MENU: propusk punkta '%s' (endpoint '%s' ne stroitsya: %s)" % (name, endpoint, e))
                return None

        menu = []
        if auth_on and not current_user.is_authenticated:
            menu = []
        else:
            codes = None
            if auth_on and current_user.is_authenticated:
                codes = user_perm_codes(current_user)
            for v in em.values():
                if auth_on:
                    need = MODULE_PERMS.get(v["key"], [])
                    if not (codes is None or (need and (set(need) & codes))):
                        continue
                u = _safe_url(v["name"], v["endpoint"])
                if u:
                    menu.append({"name": v["name"], "url": u})

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
