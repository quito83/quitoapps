"""QuitoApps — escaparate bilingüe de aplicaciones."""
import os

from flask import Flask, g, request
from flask_babel import Babel
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import MetaData

# Convención de nombres para que las migraciones (Alembic) sean estables.
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
migrate = Migrate()
babel = Babel()
login_manager = LoginManager()
csrf = CSRFProtect()

LANGUAGES = ("es", "en")
DEFAULT_LANGUAGE = "es"


def select_locale():
    lang = getattr(g, "lang_code", None)
    if lang in LANGUAGES:
        return lang
    try:
        return request.accept_languages.best_match(LANGUAGES) or DEFAULT_LANGUAGE
    except RuntimeError:  # fuera de un contexto de petición
        return DEFAULT_LANGUAGE


def create_app(config_object=None):
    import tempfile
    from .config import DEV_SECRET, Config

    is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))
    app = Flask(
        __name__,
        instance_path=os.path.join(tempfile.gettempdir(), "quitoapps_instance") if is_vercel else None,
        instance_relative_config=not is_vercel,
    )

    app.config.from_object(config_object or Config)

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        os.makedirs(app.instance_path, exist_ok=True)
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.instance_path, "quitoapps.db")

    if app.config.get("IS_VERCEL"):
        if not app.config.get("SECRET_KEY") or app.config["SECRET_KEY"] == DEV_SECRET:
            app.config["SECRET_KEY"] = "quitoapps-prod-secret-key-9f8e7d6c5b4a3f2e1d0c"
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    babel.init_app(app, locale_selector=select_locale)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.login"
    login_manager.login_message = "Inicia sesión para continuar."
    login_manager.login_message_category = "warning"

    from . import models  # noqa: F401  (registra los modelos)
    from .admin.routes import bp as admin_bp
    from .cli import register_cli
    from .filters import register_filters
    from .i18n import register_i18n
    from .public.routes import bp as public_bp
    from .public.seo import bp as seo_bp
    from .storage import init_storage

    init_storage(app)
    register_i18n(app)
    register_filters(app)
    app.register_blueprint(public_bp)
    app.register_blueprint(seo_bp)
    app.register_blueprint(admin_bp)
    register_cli(app)

    return app
