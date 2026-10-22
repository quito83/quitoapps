"""sitemap.xml, robots.txt y feeds RSS."""
from email.utils import format_datetime
from datetime import timezone

from flask import Blueprint, Response, g, render_template, url_for

from .. import LANGUAGES
from ..filters import absolute_url
from ..models import App

bp = Blueprint("seo", __name__)


def _visible():
    return App.query.filter(App.visible.is_(True))


@bp.route("/robots.txt")
def robots():
    body = f"User-agent: *\nDisallow: /admin/\nSitemap: {absolute_url(url_for('seo.sitemap'))}\n"
    return Response(body, mimetype="text/plain")


@bp.route("/sitemap.xml")
def sitemap():
    pages = []  # cada entrada: {lastmod, alternates: {lang: url}}
    for endpoint in ("public.index", "public.catalog", "public.about", "public.contact"):
        pages.append(
            {"lastmod": None, "alternates": {l: absolute_url(url_for(endpoint, lang_code=l)) for l in LANGUAGES}}
        )
    for a in _visible().order_by(App.sort_order).all():
        pages.append(
            {
                "lastmod": a.updated_at.date().isoformat(),
                "alternates": {
                    l: absolute_url(url_for("public.detail", lang_code=l, slug=a.slug)) for l in LANGUAGES
                },
            }
        )
    xml = render_template("seo/sitemap.xml", pages=pages)
    return Response(xml, mimetype="application/xml")


@bp.route("/<any(es,en):lang_code>/feed.xml")
def feed():
    apps = _visible().order_by(App.created_at.desc()).limit(30).all()
    items = [
        {
            "title": a.tr(g.lang_code).name,
            "description": a.tr(g.lang_code).short_desc,
            "link": absolute_url(url_for("public.detail", slug=a.slug)),
            "pub_date": format_datetime(a.created_at.replace(tzinfo=timezone.utc)),
        }
        for a in apps
    ]
    xml = render_template("seo/feed.xml", items=items)
    return Response(xml, mimetype="application/rss+xml")
