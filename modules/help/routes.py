from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.app import db
from modules.help.models import HelpArticle, CATEGORIES

help_bp = Blueprint("help", __name__, url_prefix="/help", template_folder="templates")

@help_bp.route("/")
def index_articles():
    q = (request.args.get("q") or "").strip()
    query = HelpArticle.query
    if q:
        like = "%" + q + "%"
        query = query.filter(db.or_(HelpArticle.title.ilike(like), HelpArticle.body.ilike(like)))
    arts = query.order_by(HelpArticle.category, HelpArticle.order, HelpArticle.id).all()
    grouped = {}
    for a in arts:
        grouped.setdefault(a.category, []).append(a)
    return render_template("index.html", grouped=grouped, q=q, categories=CATEGORIES, total=len(arts))

@help_bp.route("/<int:aid>")
def view(aid):
    a = HelpArticle.query.get_or_404(aid)
    return render_template("article.html", article=a, editing=False, categories=CATEGORIES)

@help_bp.route("/new")
def new():
    cat = request.args.get("category", CATEGORIES[0])
    return render_template("article.html", article=None, editing=None, categories=CATEGORIES, default_cat=cat)

@help_bp.route("/<int:aid>/edit")
def edit(aid):
    a = HelpArticle.query.get_or_404(aid)
    return render_template("article.html", article=a, editing=a, categories=CATEGORIES)

@help_bp.route("/save", methods=["POST"])
def save():
    aid = request.form.get("id", type=int)
    title = (request.form.get("title") or "").strip()
    category = (request.form.get("category") or CATEGORIES[0]).strip()
    body = (request.form.get("body") or "").strip()
    order = request.form.get("order", type=int) or 0
    who = (request.form.get("who") or "без имени").strip()
    if not title:
        flash("Укажи заголовок статьи")
        return redirect(url_for("help.index_articles"))
    if category not in CATEGORIES:
        category = CATEGORIES[0]
    if aid:
        a = HelpArticle.query.get_or_404(aid)
        a.title, a.category, a.body, a.order, a.edited_by = title, category, body, order, who
    else:
        a = HelpArticle(title=title, category=category, body=body, order=order, edited_by=who)
        db.session.add(a)
    db.session.commit()
    flash("Статья сохранена")
    return redirect(url_for("help.view", aid=a.id))
