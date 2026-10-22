"""Modelos de datos de QuitoApps."""
from datetime import datetime, timezone

from flask_babel import lazy_gettext as _l
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import DEFAULT_LANGUAGE, db, login_manager


def utcnow():
    """Fecha/hora UTC sin zona (compatible con SQLite y Postgres)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


STATUSES = ("dev", "beta", "published")
STATUS_LABELS = {
    "dev": _l("In development"),
    "beta": _l("Beta"),
    "published": _l("Published"),
}

LINK_KINDS = ("demo", "web", "download", "repo", "play_store", "app_store", "ms_store")
LINK_LABELS = {
    "demo": _l("Live demo"),
    "web": _l("Website"),
    "download": _l("Download"),
    "repo": _l("Source code"),
    "play_store": "Google Play",
    "app_store": "App Store",
    "ms_store": "Microsoft Store",
}


class BilingualNameMixin:
    def name(self, lang=DEFAULT_LANGUAGE):
        return getattr(self, f"name_{lang}", None) or self.name_es


app_tags = db.Table(
    "app_tags",
    db.Column("app_id", db.Integer, db.ForeignKey("apps.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Category(BilingualNameMixin, db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name_es = db.Column(db.String(80), nullable=False)
    name_en = db.Column(db.String(80), nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    apps = db.relationship("App", back_populates="category")


class Tag(BilingualNameMixin, db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name_es = db.Column(db.String(80), nullable=False)
    name_en = db.Column(db.String(80), nullable=False, default="")
    apps = db.relationship("App", secondary=app_tags, back_populates="tags")


class App(db.Model):
    __tablename__ = "apps"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="dev")
    icon_url = db.Column(db.String(500))
    featured = db.Column(db.Boolean, nullable=False, default=False)
    visible = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    category = db.relationship("Category", back_populates="apps")
    tags = db.relationship("Tag", secondary=app_tags, back_populates="apps", order_by="Tag.slug")
    translations = db.relationship(
        "AppTranslation", back_populates="app", cascade="all, delete-orphan", lazy="selectin"
    )
    screenshots = db.relationship(
        "Screenshot", back_populates="app", cascade="all, delete-orphan", order_by="Screenshot.sort_order"
    )
    links = db.relationship("Link", back_populates="app", cascade="all, delete-orphan", order_by="Link.id")

    def tr(self, lang=DEFAULT_LANGUAGE):
        """Traducción en `lang`, con respaldo al idioma por defecto."""
        by_lang = {t.lang: t for t in self.translations}
        for candidate in (lang, DEFAULT_LANGUAGE, *by_lang.keys()):
            t = by_lang.get(candidate)
            if t and t.name:
                return t
        return AppTranslation(lang=lang, name=self.slug, short_desc="", long_desc="")

    def set_translation(self, lang, name, short_desc, long_desc):
        t = next((t for t in self.translations if t.lang == lang), None)
        if t is None:
            t = AppTranslation(lang=lang)
            self.translations.append(t)
        t.name, t.short_desc, t.long_desc = name or "", short_desc or "", long_desc or ""

    def get_link(self, kind):
        return next((l.url for l in self.links if l.kind == kind), "")

    def set_link(self, kind, url):
        existing = next((l for l in self.links if l.kind == kind), None)
        url = (url or "").strip()
        if not url:
            if existing:
                self.links.remove(existing)
        elif existing:
            existing.url = url
        else:
            self.links.append(Link(kind=kind, url=url))

    @property
    def status_label(self):
        return STATUS_LABELS.get(self.status, self.status)


class AppTranslation(db.Model):
    __tablename__ = "app_translations"
    __table_args__ = (db.UniqueConstraint("app_id", "lang", name="uq_app_translations_app_lang"),)
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False)
    lang = db.Column(db.String(5), nullable=False)
    name = db.Column(db.String(120), nullable=False, default="")
    short_desc = db.Column(db.String(300), nullable=False, default="")
    long_desc = db.Column(db.Text, nullable=False, default="")
    app = db.relationship("App", back_populates="translations")


class Screenshot(db.Model):
    __tablename__ = "screenshots"
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    app = db.relationship("App", back_populates="screenshots")


class Link(db.Model):
    __tablename__ = "links"
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False)
    kind = db.Column(db.String(30), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    app = db.relationship("App", back_populates="links")

    @property
    def label(self):
        return LINK_LABELS.get(self.kind, self.kind)


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    ip = db.Column(db.String(64))
    lang = db.Column(db.String(5))
    read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Page(db.Model):
    """Páginas editables desde el admin (p. ej. 'about')."""

    __tablename__ = "pages"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    body_es = db.Column(db.Text, nullable=False, default="")
    body_en = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def body(self, lang=DEFAULT_LANGUAGE):
        return getattr(self, f"body_{lang}", None) or self.body_es


class RateEvent(db.Model):
    """Eventos para limitar intentos (login fallido, envíos de contacto).

    Se guardan en BD porque en serverless no hay memoria compartida.
    """

    __tablename__ = "rate_events"
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(30), nullable=False)
    key = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
