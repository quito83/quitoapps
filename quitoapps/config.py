"""Configuración de QuitoApps.

Todas las credenciales se leen de variables de entorno (o de un archivo `.env`
en desarrollo). Ver `.env.example`.
"""
import os

from dotenv import load_dotenv
from sqlalchemy.pool import NullPool

load_dotenv()

DEV_SECRET = "dev-insecure-change-me"
FALLBACK_PROD_DB = "postgresql://neondb_owner:npg_6SdVl2YjvwFp@ep-dark-firefly-b7f7h8ue-pooler.c-13.us-east-1.aws.neon.tech/neondb?channel_binding=require&sslmode=require"


def _database_url():
    """Devuelve la URL de la BD normalizada para el driver psycopg 3."""
    url = (
        os.environ.get("POSTGRES_URL")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRESQL_URL")
        or os.environ.get("NEON_DATABASE_URL")
    )
    if not url and os.environ.get("VERCEL"):
        url = FALLBACK_PROD_DB

    if not url:
        return None  # create_app usará SQLite dentro de /instance

    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET)
    IS_VERCEL = bool(os.environ.get("VERCEL"))

    # Base de datos
    SQLALCHEMY_DATABASE_URI = _database_url()
    # En serverless cada invocación es efímera: sin pool de conexiones.
    SQLALCHEMY_ENGINE_OPTIONS = {"poolclass": NullPool} if IS_VERCEL else {"pool_pre_ping": True}

    # Almacenamiento de imágenes: "blob" (Vercel Blob) o "local" (instance/uploads)
    BLOB_READ_WRITE_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN")
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND") or ("blob" if BLOB_READ_WRITE_TOKEN else "local")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER")  # por defecto instance/uploads

    # Vercel limita el cuerpo de las peticiones a 4.5 MB
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024 + 400 * 1024

    # Idiomas
    LANGUAGES = ("es", "en")
    BABEL_DEFAULT_LOCALE = "es"
    BABEL_TRANSLATION_DIRECTORIES = "translations"

    # Sesión / seguridad
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_VERCEL
    REMEMBER_COOKIE_SECURE = IS_VERCEL
    REMEMBER_COOKIE_HTTPONLY = True

    # Sitio
    SITE_NAME = "QuitoApps"
    SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")  # p.ej. https://quitoapps.vercel.app
    ANALYTICS_ENABLED = IS_VERCEL or os.environ.get("ANALYTICS_ENABLED") == "1"

    # Límites anti-abuso
    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_WINDOW_MINUTES = 15
    CONTACT_MAX_MESSAGES = 3
    CONTACT_WINDOW_MINUTES = 10


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    STORAGE_BACKEND = "local"
    IS_VERCEL = False
    ANALYTICS_ENABLED = False
    SESSION_COOKIE_SECURE = False
