"""Yadro - sozdanie Flask app + chetenie nastroek + dinamicheskie moduli"""
from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy
import os, json, importlib
import config
from core.registry import AVAILABLE_MODULES

db = SQLAlchemy()

def create_app():
    app = Flask(__name__,
                template_folder="../web/templates",
                static_folder="../web/static")
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    os.makedirs(config.DATA_DIR, exist_ok=True)

    # import modeley VSEx moduley DO create_all, chtoby tablicy sozdalis
    from modules.feedback import models as feedback_models  # noqa
    from modules.settings import models as settings_models  # noqa
    from modules.changelog import models as changelog_models  # noqa
    from modules.versions import models as versions_models  # noqa
    from modules.help import models as help_models  # noqa

    with app.app_context():
        db.create_all()
        # zasevka startovyh dannyh (tolko esli tablica pusta)
        from modules.changelog.models import seed as seed_changelog
        from modules.versions.models import seed as seed_versions
        from modules.help.models import seed as seed_help
        seed_changelog()
        seed_versions()
        seed_help()

        from modules.settings.models import get_setting
        raw = get_setting("enabled_modules", "")
        if raw.strip():
            try:
                enabled = set(json.loads(raw))
            except Exception:
                enabled = {m["key"] for m in AVAILABLE_MODULES}
        else:
            enabled = {m["key"] for m in AVAILABLE_MODULES}

    from web.routes import main_bp
    app.register_blueprint(main_bp)

    from modules.settings.routes import settings_bp
    app.register_blueprint(settings_bp)

    registered = {}
    for m in AVAILABLE_MODULES:
        if m["key"] in enabled:
            mod = importlib.import_module(m["import_path"])
            app.register_blueprint(getattr(mod, m["bp_attr"]))
            registered[m["key"]] = m
    app.config["ENABLED_MODULES"] = registered

    @app.context_processor
    def inject_settings():
        from modules.settings.models import get_setting
        from modules.versions.models import Release
        em = app.config.get("ENABLED_MODULES", {})
        menu = [{"name": v["name"], "url": url_for(v["endpoint"])} for v in em.values()]
        cur = Release.query.filter_by(is_current=True).first()
        return {
            "app_title":  get_setting("app_title", "Модульное приложение для производства"),
            "app_footer": get_setting("app_footer", "ядро + модули | Flask + SQLAlchemy"),
            "app_version": cur.version if cur else "dev",
            "theme":      get_setting("theme", "light"),
            "menu":       menu,
        }

    return app
