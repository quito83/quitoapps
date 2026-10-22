"""Almacenamiento de imágenes: disco local (desarrollo) o Vercel Blob (producción)."""
import io
import os
import uuid

from flask import current_app, send_from_directory, url_for
from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP", "GIF"}
ICON_MAX = 512
SCREENSHOT_MAX = 1600


class ImageError(ValueError):
    """La imagen subida no es válida."""


def process_image(stream, max_size):
    """Valida, corrige orientación, redimensiona y convierte a WebP."""
    try:
        img = Image.open(stream)
        if img.format not in ALLOWED_FORMATS:
            raise ImageError(f"Formato no permitido: {img.format}")
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageError("El archivo no es una imagen válida.") from exc
    img = ImageOps.exif_transpose(img)
    has_alpha = img.mode in ("RGBA", "LA", "P") and ("transparency" in img.info or img.mode != "P")
    img = img.convert("RGBA" if has_alpha else "RGB")
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=85, method=6)
    return buf.getvalue()


class LocalStorage:
    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def save(self, data, prefix):
        name = f"{prefix}-{uuid.uuid4().hex[:12]}.webp"
        with open(os.path.join(self.folder, name), "wb") as fh:
            fh.write(data)
        return f"/media/{name}"

    def delete(self, url):
        if not url or not url.startswith("/media/"):
            return
        path = os.path.join(self.folder, os.path.basename(url))
        if os.path.isfile(path):
            os.remove(path)


class BlobStorage:
    """Vercel Blob mediante el SDK oficial de Python (`pip install vercel`).

    Las credenciales se leen de la variable de entorno BLOB_READ_WRITE_TOKEN,
    que Vercel inyecta al conectar el store Blob al proyecto.
    """

    def save(self, data, prefix):
        from vercel.blob.sync import put_blob

        result = put_blob(
            f"quitoapps/{prefix}-{uuid.uuid4().hex[:12]}.webp",
            data,
            access="public",
            content_type="image/webp",
            cache_control_max_age=60 * 60 * 24 * 365,
        )
        return result.url

    def delete(self, url):
        if not url or "blob.vercel-storage.com" not in url:
            return
        from vercel.blob.sync import delete_blob

        try:
            delete_blob(url)
        except Exception:  # noqa: BLE001 — no bloquear el borrado en BD
            current_app.logger.exception("No se pudo borrar %s de Vercel Blob", url)


def init_storage(app):
    import tempfile
    backend = app.config.get("STORAGE_BACKEND", "local")
    if backend == "blob":
        storage = BlobStorage()
    else:
        default_dir = os.path.join(tempfile.gettempdir(), "quitoapps_uploads") if app.config.get("IS_VERCEL") else os.path.join(app.instance_path, "uploads")
        folder = app.config.get("UPLOAD_FOLDER") or default_dir
        storage = LocalStorage(folder)

        @app.route("/media/<path:filename>")
        def media(filename):
            return send_from_directory(storage.folder, filename, max_age=60 * 60 * 24 * 30)

    app.extensions["storage"] = storage


def get_storage():
    return current_app.extensions["storage"]


def save_image(file_or_bytes, prefix, max_size):
    """Procesa una imagen (FileStorage o bytes) y la guarda. Devuelve la URL."""
    stream = io.BytesIO(file_or_bytes) if isinstance(file_or_bytes, (bytes, bytearray)) else file_or_bytes.stream
    data = process_image(stream, max_size)
    return get_storage().save(data, prefix)
