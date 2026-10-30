"""Yadro - sozdanie Flask app"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__,
                template_folder="../web/templates",
                static_folder="../web/static")
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # Garantiruem, chto papka data SUSHCHESTVUET do podklyucheniya
    os.makedirs(config.DATA_DIR, exist_ok=True)

    # Import modeley modulya DO create_all, chtoby tablicy sozdalis
    from modules.feedback import models as feedback_models  # noqa
    with app.app_context():
        db.create_all()

    from web.routes import main_bp
    app.register_blueprint(main_bp)
    from modules.feedback.routes import feedback_bp
    app.register_blueprint(feedback_bp)
    return app
