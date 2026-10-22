"""Filtros de plantilla, utilidades y manejadores de error."""
import re
from datetime import datetime

import markdown as md_lib
import nh3
from flask import current_app, g, render_template, request
from markupsafe import Markup

from . import select_locale

ALLOWED_TAGS = {
    "p", "br", "hr", "strong", "em", "b", "i", "u", "s", "del", "code", "pre", "blockquote",
    "ul", "ol", "li", "h2", "h3", "h4", "h5", "h6", "a", "img", "table", "thead", "tbody",
    "tr", "th", "td",
}
ALLOWED_ATTRIBUTES = {"a": {"href", "title"}, "img": {"src", "alt", "title"}, "th": {"align"}, "td": {"align"}}


def render_markdown(text):
    """Markdown → HTML sanitizado (sin scripts ni atributos peligrosos)."""
    html = md_lib.markdown(text or "", extensions=["extra", "sane_lists", "nl2br"])
    clean = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer nofollow",
    )
    return Markup(clean)


def plain_text(text, length=160):
    """Quita marcas básicas de Markdown y recorta (para meta descripciones)."""
    text = re.sub(r"[#*_`>\[\]()!-]", "", text or "")
    text = " ".join(text.split())
    return text if len(text) <= length else text[: length - 1].rstrip() + "…"


def absolute_url(path):
    base = current_app.config.get("SITE_URL") or request.host_url.rstrip("/")
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return base + path


def register_filters(app):
    app.jinja_env.filters["markdown"] = render_markdown
    app.jinja_env.filters["plain"] = plain_text
    app.jinja_env.globals["absolute_url"] = absolute_url

    @app.context_processor
    def inject_site():
        return {
            "site_name": app.config["SITE_NAME"],
            "analytics_enabled": app.config.get("ANALYTICS_ENABLED", False),
            "current_year": datetime.now().year,
        }

    def _error(template, code):
        if not getattr(g, "lang_code", None):
            g.lang_code = select_locale()
        return render_template(template), code

    @app.errorhandler(404)
    def not_found(e):
        return _error("errors/404.html", 404)

    @app.errorhandler(413)
    def too_large(e):
        return _error("errors/413.html", 413)

    @app.errorhandler(500)
    def server_error(e):
        return _error("errors/500.html", 500)
