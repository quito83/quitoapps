"""Rutas públicas (con prefijo de idioma /es/ o /en/)."""
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
from flask_babel import gettext as _
from sqlalchemy import or_

from .. import db, ratelimit
from ..models import STATUS_LABELS, STATUSES, App, AppTranslation, Category, Message, Page, Tag
from .forms import ContactForm

bp = Blueprint("public", __name__, url_prefix="/<any(es,en):lang_code>")


def visible_apps():
    return App.query.filter(App.visible.is_(True))


@bp.route("/")
def index():
    featured = visible_apps().filter(App.featured.is_(True)).order_by(App.sort_order, App.created_at.desc()).all()
    latest = visible_apps().order_by(App.created_at.desc()).limit(6).all()
    total = visible_apps().count()
    return render_template("public/index.html", featured=featured, latest=latest, total=total)


@bp.route("/apps/")
def catalog():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", "")
    tag = request.args.get("tag", "")
    status = request.args.get("status", "")

    query = visible_apps()
    if q:
        like = f"%{q}%"
        query = query.filter(
            App.translations.any(
                or_(AppTranslation.name.ilike(like), AppTranslation.short_desc.ilike(like))
            )
            | App.tags.any(or_(Tag.name_es.ilike(like), Tag.name_en.ilike(like)))
        )
    if cat:
        query = query.filter(App.category.has(Category.slug == cat))
    if tag:
        query = query.filter(App.tags.any(Tag.slug == tag))
    if status in STATUSES:
        query = query.filter(App.status == status)

    apps = query.order_by(App.featured.desc(), App.sort_order, App.created_at.desc()).all()
    categories = Category.query.order_by(Category.sort_order, Category.slug).all()
    tags = Tag.query.order_by(Tag.slug).all()
    return render_template(
        "public/catalog.html",
        apps=apps,
        categories=categories,
        tags=tags,
        statuses=STATUS_LABELS,
        filters={"q": q, "category": cat, "tag": tag, "status": status},
    )


@bp.route("/apps/<slug>/")
def detail(slug):
    app_ = visible_apps().filter_by(slug=slug).first()
    if app_ is None:
        abort(404)
    related = []
    if app_.category_id:
        related = (
            visible_apps()
            .filter(App.category_id == app_.category_id, App.id != app_.id)
            .order_by(App.sort_order)
            .limit(3)
            .all()
        )
    return render_template("public/detail.html", app_item=app_, related=related)


@bp.route("/about/")
def about():
    page = Page.query.filter_by(key="about").first()
    return render_template("public/about.html", page=page)


@bp.route("/contact/", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        if form.website.data:  # honeypot: un bot rellenó el campo oculto
            flash(_("Thanks! Your message has been sent."), "success")
            return redirect(url_for(".contact"))
        ip = ratelimit.client_ip()
        cfg = current_app.config
        if ratelimit.is_limited("contact", ip, cfg["CONTACT_MAX_MESSAGES"], cfg["CONTACT_WINDOW_MINUTES"]):
            flash(_("Too many messages. Please try again in a few minutes."), "error")
            return render_template("public/contact.html", form=form), 429
        db.session.add(
            Message(
                name=form.name.data.strip(),
                email=form.email.data.strip(),
                body=form.message.data.strip(),
                ip=ip,
                lang=g.lang_code,
            )
        )
        db.session.commit()
        ratelimit.record("contact", ip)
        flash(_("Thanks! Your message has been sent."), "success")
        return redirect(url_for(".contact"))
    return render_template("public/contact.html", form=form)
