from flask import Blueprint, render_template
from core.auth import perm

primer_bp = Blueprint("primer", __name__, url_prefix="/primer", template_folder="templates")

@primer_bp.route("/")
@perm("primer.view")
def index():
    from modules.primer.models import PrimerNote
    notes = PrimerNote.query.order_by(PrimerNote.id).all()
    return render_template("primer/index.html", notes=notes)
