"""Маршруты модуля производства"""
from flask import Blueprint

production_bp = Blueprint("production", __name__, url_prefix="/production",
                          template_folder="templates", static_folder="static")

@production_bp.route("/")
def index():
    return "<h1>Модуль производства</h1><p>Этот модуль работает!</p>"
