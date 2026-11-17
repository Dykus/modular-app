from flask import Blueprint, render_template
from core.auth import perm

test_update_bp = Blueprint("test_update", __name__, url_prefix="/test-update",
                          template_folder="templates")

@test_update_bp.route("/")
def index():
    """Тестовая страница для проверки обновления."""
    return render_template("test_update/index.html")
