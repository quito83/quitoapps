"""Rutas del panel de administración (/admin)."""
from functools import wraps

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from .. import db, ratelimit
from ..models import LINK_KINDS, App, Category, Message, Page, Screenshot, Tag, User
from ..storage import ICON_MAX, SCREENSHOT_MAX, ImageError, get_storage, save_image
from .forms import LINK_FIELD_LABELS, AppForm, EmptyForm, LoginForm, PageForm, TaxonomyForm

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
def admin_locale():
    g.lang_code = "es"  # el panel está en español


@bp.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@bp.context_processor
def inject_admin():
    unread = 0
    if current_user.is_authenticated:
        unread = Message.query.filter_by(read=False).count()
    return {"unread_count": unread, "empty_form": EmptyForm()}


def _safe_next(target):
    return target if target and target.startswith("/") and not target.startswith("//") else None


# --------------------------------------------------------------------------- auth
@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(".dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        ip = ratelimit.client_ip()
        cfg = current_app.config
        if ratelimit.is_limited("login", ip, cfg["LOGIN_MAX_ATTEMPTS"], cfg["LOGIN_WINDOW_MINUTES"]):
            flash(f"Demasiados intentos. Espera {cfg['LOGIN_WINDOW_MINUTES']} minutos.", "error")
            return render_template("admin/login.html", form=form), 429
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            ratelimit.clear("login", ip)
            return redirect(_safe_next(request.args.get("next")) or url_for(".dashboard"))
        ratelimit.record("login", ip)
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("admin/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    if EmptyForm().validate_on_submit():
        logout_user()
    return redirect(url_for(".login"))


# ---------------------------------------------------------------------- dashboard
@bp.route("/")
@login_required
def dashboard():
    stats = {
        "apps": App.query.count(),
        "visible": App.query.filter_by(visible=True).count(),
        "featured": App.query.filter_by(featured=True).count(),
        "categories": Category.query.count(),
        "tags": Tag.query.count(),
        "messages": Message.query.count(),
    }
    recent_messages = Message.query.order_by(Message.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats, recent_messages=recent_messages)


# --------------------------------------------------------------------------- apps
@bp.route("/apps")
@login_required
def apps():
    items = App.query.order_by(App.sort_order, App.created_at.desc()).all()
    return render_template("admin/apps.html", items=items)


def _fill_choices(form):
    form.category_id.choices = [(0, "— Sin categoría —")] + [
        (c.id, c.name_es) for c in Category.query.order_by(Category.sort_order, Category.name_es)
    ]
    form.tag_ids.choices = [(t.id, t.name_es) for t in Tag.query.order_by(Tag.name_es)]


def _save_app(form, item):
    """Copia los datos del formulario al modelo y procesa imágenes."""
    storage = get_storage()
    item.slug = form.slug.data.strip()
    item.status = form.status.data
    item.category_id = form.category_id.data or None
    item.tags = Tag.query.filter(Tag.id.in_(form.tag_ids.data or [])).all() if form.tag_ids.data else []
    item.featured = form.featured.data
    item.visible = form.visible.data
    item.sort_order = form.sort_order.data or 0
    item.set_translation("es", form.name_es.data.strip(), form.short_es.data.strip(), form.long_es.data)
    item.set_translation("en", form.name_en.data.strip(), form.short_en.data.strip(), form.long_en.data)
    for kind in LINK_KINDS:
        item.set_link(kind, getattr(form, f"link_{kind}").data)

    if form.remove_icon.data and item.icon_url:
        storage.delete(item.icon_url)
        item.icon_url = None
    icon = form.icon.data
    if icon and getattr(icon, "filename", ""):
        new_url = save_image(icon, f"{item.slug}-icon", ICON_MAX)
        if item.icon_url:
            storage.delete(item.icon_url)
        item.icon_url = new_url

    next_order = max((s.sort_order for s in item.screenshots), default=-1) + 1
    for f in form.screenshots.data or []:
        if f and getattr(f, "filename", ""):
            url = save_image(f, f"{item.slug}-shot", SCREENSHOT_MAX)
            item.screenshots.append(Screenshot(image_url=url, sort_order=next_order))
            next_order += 1


def _app_form_view(item):
    is_new = item.id is None
    form = AppForm(obj=None if request.method == "POST" else item)
    _fill_choices(form)
    if request.method == "GET" and not is_new:
        form.category_id.data = item.category_id or 0
        form.tag_ids.data = [t.id for t in item.tags]
        es, en = item.tr("es"), item.tr("en")
        form.name_es.data, form.short_es.data, form.long_es.data = es.name, es.short_desc, es.long_desc
        en_t = next((t for t in item.translations if t.lang == "en"), None)
        if en_t:
            form.name_en.data, form.short_en.data, form.long_en.data = en_t.name, en_t.short_desc, en_t.long_desc
        for kind in LINK_KINDS:
            getattr(form, f"link_{kind}").data = item.get_link(kind)

    if form.validate_on_submit():
        clash = App.query.filter(App.slug == form.slug.data.strip(), App.id != (item.id or 0)).first()
        if clash:
            form.slug.errors.append("Ya existe otra app con ese slug.")
        else:
            try:
                _save_app(form, item)
                if is_new:
                    db.session.add(item)
                db.session.commit()
            except ImageError as exc:
                db.session.rollback()
                flash(str(exc), "error")
            except IntegrityError:
                db.session.rollback()
                flash("No se pudo guardar: datos duplicados.", "error")
            else:
                flash("App guardada correctamente.", "success")
                return redirect(url_for(".app_edit", app_id=item.id))

    link_fields = [(getattr(form, f"link_{k}"), LINK_FIELD_LABELS[k]) for k in LINK_KINDS]
    return render_template("admin/app_form.html", form=form, item=item, is_new=is_new, link_fields=link_fields)


@bp.route("/apps/new", methods=["GET", "POST"])
@login_required
def app_new():
    return _app_form_view(App(visible=True))


@bp.route("/apps/<int:app_id>", methods=["GET", "POST"])
@login_required
def app_edit(app_id):
    item = db.session.get(App, app_id) or abort(404)
    return _app_form_view(item)


@bp.route("/apps/<int:app_id>/delete", methods=["POST"])
@login_required
def app_delete(app_id):
    item = db.session.get(App, app_id) or abort(404)
    if EmptyForm().validate_on_submit():
        storage = get_storage()
        urls = [item.icon_url] + [s.image_url for s in item.screenshots]
        db.session.delete(item)
        db.session.commit()
        for url in urls:
            storage.delete(url)
        flash("App eliminada.", "success")
    return redirect(url_for(".apps"))


@bp.route("/screenshots/<int:shot_id>/delete", methods=["POST"])
@login_required
def screenshot_delete(shot_id):
    shot = db.session.get(Screenshot, shot_id) or abort(404)
    app_id = shot.app_id
    if EmptyForm().validate_on_submit():
        get_storage().delete(shot.image_url)
        db.session.delete(shot)
        db.session.commit()
        flash("Captura eliminada.", "success")
    return redirect(url_for(".app_edit", app_id=app_id) + "#capturas")


@bp.route("/screenshots/<int:shot_id>/move/<direction>", methods=["POST"])
@login_required
def screenshot_move(shot_id, direction):
    shot = db.session.get(Screenshot, shot_id) or abort(404)
    if EmptyForm().validate_on_submit():
        shots = list(shot.app.screenshots)
        i = shots.index(shot)
        j = i - 1 if direction == "up" else i + 1
        if 0 <= j < len(shots):
            shots[i], shots[j] = shots[j], shots[i]
            for n, s in enumerate(shots):
                s.sort_order = n
            db.session.commit()
    return redirect(url_for(".app_edit", app_id=shot.app_id) + "#capturas")


# ------------------------------------------------------------ categorías / etiquetas
TAXONOMIES = {
    "categories": (Category, "Categorías", "Categoría"),
    "tags": (Tag, "Etiquetas", "Etiqueta"),
}


@bp.route("/<any(categories,tags):kind>", methods=["GET", "POST"])
@login_required
def taxonomy(kind):
    model, title, singular = TAXONOMIES[kind]
    edit_id = request.args.get("edit", type=int)
    editing = db.session.get(model, edit_id) if edit_id else None
    form = TaxonomyForm(obj=editing)
    if form.validate_on_submit():
        item = editing or model()
        clash = model.query.filter(model.slug == form.slug.data, model.id != (item.id or 0)).first()
        if clash:
            form.slug.errors.append("Ese slug ya existe.")
        else:
            item.slug, item.name_es, item.name_en = form.slug.data, form.name_es.data, form.name_en.data
            if hasattr(item, "sort_order"):
                item.sort_order = form.sort_order.data or 0
            db.session.add(item)
            db.session.commit()
            flash(f"{singular} guardada.", "success")
            return redirect(url_for(".taxonomy", kind=kind))
    order = (model.sort_order, model.name_es) if hasattr(model, "sort_order") else (model.name_es,)
    items = model.query.order_by(*order).all()
    return render_template(
        "admin/taxonomy.html", kind=kind, title=title, singular=singular, items=items, form=form, editing=editing
    )


@bp.route("/<any(categories,tags):kind>/<int:item_id>/delete", methods=["POST"])
@login_required
def taxonomy_delete(kind, item_id):
    model, _title, singular = TAXONOMIES[kind]
    item = db.session.get(model, item_id) or abort(404)
    if EmptyForm().validate_on_submit():
        if kind == "categories":
            for a in item.apps:
                a.category_id = None
        db.session.delete(item)
        db.session.commit()
        flash(f"{singular} eliminada.", "success")
    return redirect(url_for(".taxonomy", kind=kind))


# ------------------------------------------------------------------------- páginas
@bp.route("/pages/about", methods=["GET", "POST"])
@login_required
def page_about():
    page = Page.query.filter_by(key="about").first()
    if page is None:
        page = Page(key="about", body_es="", body_en="")
        db.session.add(page)
    form = PageForm(obj=page)
    if form.validate_on_submit():
        page.body_es, page.body_en = form.body_es.data or "", form.body_en.data or ""
        db.session.commit()
        flash("Página guardada.", "success")
        return redirect(url_for(".page_about"))
    return render_template("admin/page_form.html", form=form, title="Acerca de")


# ------------------------------------------------------------------------ mensajes
@bp.route("/messages")
@login_required
def messages():
    items = Message.query.order_by(Message.read, Message.created_at.desc()).all()
    return render_template("admin/messages.html", items=items)


@bp.route("/messages/<int:msg_id>")
@login_required
def message_view(msg_id):
    msg = db.session.get(Message, msg_id) or abort(404)
    if not msg.read:
        msg.read = True
        db.session.commit()
    return render_template("admin/message.html", msg=msg)


@bp.route("/messages/<int:msg_id>/unread", methods=["POST"])
@login_required
def message_unread(msg_id):
    msg = db.session.get(Message, msg_id) or abort(404)
    if EmptyForm().validate_on_submit():
        msg.read = False
        db.session.commit()
    return redirect(url_for(".messages"))


@bp.route("/messages/<int:msg_id>/delete", methods=["POST"])
@login_required
def message_delete(msg_id):
    msg = db.session.get(Message, msg_id) or abort(404)
    if EmptyForm().validate_on_submit():
        db.session.delete(msg)
        db.session.commit()
        flash("Mensaje eliminado.", "success")
    return redirect(url_for(".messages"))
