from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
db = SQLAlchemy()
def create_app():
    app = Flask(__name__, template_folder="../web/templates", static_folder="../web/static")
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///../data/database.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"), exist_ok=True)
    with app.app_context():
        db.create_all()
    from web.routes import main_bp
    app.register_blueprint(main_bp)
    return app
