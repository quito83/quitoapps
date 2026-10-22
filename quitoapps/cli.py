"""Comandos de terminal: `flask create-admin`, `flask seed`, `flask translations`."""
import io
import os
import subprocess
import sys

import click
from PIL import Image, ImageDraw, ImageFont

from . import db
from .models import App, Category, Page, Screenshot, Tag, User
from .storage import ICON_MAX, SCREENSHOT_MAX, save_image


def register_cli(app):
    @app.cli.command("create-admin")
    @click.option("--username", prompt="Usuario")
    @click.password_option("--password", prompt="Contraseña", confirmation_prompt="Repite la contraseña")
    def create_admin(username, password):
        """Crea el administrador o cambia su contraseña."""
        if len(password) < 10:
            raise click.ClickException("La contraseña debe tener al menos 10 caracteres.")
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(username=username)
            db.session.add(user)
            action = "creado"
        else:
            action = "actualizado"
        user.set_password(password)
        db.session.commit()
        click.secho(f"Administrador '{username}' {action}.", fg="green")

    @app.cli.command("seed")
    @click.option("--force", is_flag=True, help="Cargar aunque ya existan apps.")
    def seed(force):
        """Carga categorías, etiquetas, 3 apps de ejemplo y la página 'Acerca de'."""
        if App.query.count() and not force:
            raise click.ClickException("Ya hay apps en la base de datos. Usa --force para cargar igualmente.")
        seed_data()
        click.secho("Datos de ejemplo cargados.", fg="green")

    @app.cli.command("translations")
    @click.argument("action", type=click.Choice(["extract", "update", "compile"]))
    def translations(action):
        """Gestiona las traducciones (pybabel): extract → update → compile."""
        root = os.path.dirname(app.root_path)
        tdir = os.path.join(app.root_path, "translations")
        pot = os.path.join(root, "messages.pot")
        cmds = {
            "extract": ["extract", "-F", os.path.join(root, "babel.cfg"), "-k", "_l", "-o", pot, app.root_path],
            "update": ["update", "-i", pot, "-d", tdir],
            "compile": ["compile", "-d", tdir],
        }
        subprocess.run([sys.executable, "-m", "babel.messages.frontend", *cmds[action]], check=True)


# ---------------------------------------------------------------------- seed data
PALETTE = [((30, 64, 175), (14, 116, 144)), ((180, 83, 9), (217, 119, 6)), ((21, 128, 61), (13, 148, 136))]


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow antiguo
        return ImageFont.load_default()


def _placeholder(width, height, text, colors, subtitle=""):
    """Imagen PNG con degradado y texto, para las apps de ejemplo."""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    (r1, g1, b1), (r2, g2, b2) = colors
    for y in range(height):
        t = y / max(height - 1, 1)
        draw.line([(0, y), (width, y)], fill=(int(r1 + (r2 - r1) * t), int(g1 + (g2 - g1) * t), int(b1 + (b2 - b1) * t)))
    font = _font(int(min(width, height) * (0.38 if not subtitle else 0.12)))
    draw.text((width / 2, height / 2 - (20 if subtitle else 0)), text, fill="white", font=font, anchor="mm")
    if subtitle:
        draw.text((width / 2, height / 2 + height * 0.1), subtitle, fill=(255, 255, 255), font=_font(int(height * 0.05)), anchor="mm")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


SAMPLE_APPS = [
    {
        "slug": "gastos-claros",
        "status": "published",
        "featured": True,
        "category": "productividad",
        "tags": ["python", "finanzas", "escritorio"],
        "initials": "GC",
        "es": (
            "Gastos Claros",
            "Controla tus gastos personales y visualiza en qué se va tu dinero.",
            "## ¿Qué es?\n\n**Gastos Claros** es una app de escritorio para registrar gastos e ingresos.\n\n"
            "### Funciones\n\n- Categorías personalizables\n- Gráficos mensuales\n- Exportación a Excel\n",
        ),
        "en": (
            "Clear Expenses",
            "Track your personal expenses and see where your money goes.",
            "## What is it?\n\n**Clear Expenses** is a desktop app to record expenses and income.\n\n"
            "### Features\n\n- Custom categories\n- Monthly charts\n- Excel export\n",
        ),
        "links": {"download": "https://example.com/gastos-claros", "repo": "https://github.com/example/gastos-claros"},
    },
    {
        "slug": "ruta-quito",
        "status": "beta",
        "featured": True,
        "category": "movilidad",
        "tags": ["web", "mapas"],
        "initials": "RQ",
        "es": (
            "Ruta Quito",
            "Planifica tus viajes en transporte público por Quito.",
            "Encuentra la mejor combinación de buses, Metro y Trolebús para llegar a tu destino.\n\n"
            "> Actualmente en beta: ¡tus comentarios son bienvenidos!",
        ),
        "en": (
            "Quito Route",
            "Plan your public transport trips around Quito.",
            "Find the best combination of buses, Metro and Trolleybus to reach your destination.\n\n"
            "> Currently in beta: feedback welcome!",
        ),
        "links": {"demo": "https://example.com/ruta-quito"},
    },
    {
        "slug": "nota-rapida",
        "status": "dev",
        "featured": False,
        "category": "productividad",
        "tags": ["python", "web"],
        "initials": "NR",
        "es": (
            "Nota Rápida",
            "Toma notas en Markdown y sincronízalas entre tus dispositivos.",
            "Una app minimalista de notas con soporte **Markdown**, etiquetas y búsqueda instantánea.",
        ),
        "en": (
            "Quick Note",
            "Take Markdown notes and sync them across your devices.",
            "A minimalist notes app with **Markdown** support, tags and instant search.",
        ),
        "links": {"repo": "https://github.com/example/nota-rapida"},
    },
]

ABOUT_ES = """## Hola 👋

Bienvenido a **QuitoApps**, el lugar donde presento las aplicaciones que voy creando.

Cada app nace de una necesidad real: simplificar tareas, aprender algo nuevo o resolver un problema concreto.

¿Tienes una idea o comentario? [Escríbeme](../contact/).
"""

ABOUT_EN = """## Hi there 👋

Welcome to **QuitoApps**, the place where I showcase the apps I build.

Every app starts from a real need: simplifying tasks, learning something new or solving a specific problem.

Have an idea or feedback? [Get in touch](../contact/).
"""


def seed_data():
    cats = {}
    for i, (slug, es, en) in enumerate(
        [("productividad", "Productividad", "Productivity"), ("movilidad", "Movilidad", "Mobility")]
    ):
        cats[slug] = Category.query.filter_by(slug=slug).first() or Category(slug=slug, name_es=es, name_en=en, sort_order=i)
        db.session.add(cats[slug])
    tags = {}
    for slug, es, en in [
        ("python", "Python", "Python"),
        ("web", "Web", "Web"),
        ("escritorio", "Escritorio", "Desktop"),
        ("finanzas", "Finanzas", "Finance"),
        ("mapas", "Mapas", "Maps"),
    ]:
        tags[slug] = Tag.query.filter_by(slug=slug).first() or Tag(slug=slug, name_es=es, name_en=en)
        db.session.add(tags[slug])

    for n, data in enumerate(SAMPLE_APPS):
        if App.query.filter_by(slug=data["slug"]).first():
            continue
        colors = PALETTE[n % len(PALETTE)]
        a = App(
            slug=data["slug"],
            status=data["status"],
            featured=data["featured"],
            visible=True,
            sort_order=n,
            category=cats[data["category"]],
            tags=[tags[t] for t in data["tags"]],
        )
        a.set_translation("es", *data["es"])
        a.set_translation("en", *data["en"])
        for kind, url in data["links"].items():
            a.set_link(kind, url)
        a.icon_url = save_image(_placeholder(512, 512, data["initials"], colors), f"{a.slug}-icon", ICON_MAX)
        for i in range(3):
            png = _placeholder(1280, 800, data["es"][0], colors, subtitle=f"Captura {i + 1} · Screenshot {i + 1}")
            a.screenshots.append(Screenshot(image_url=save_image(png, f"{a.slug}-shot", SCREENSHOT_MAX), sort_order=i))
        db.session.add(a)

    if not Page.query.filter_by(key="about").first():
        db.session.add(Page(key="about", body_es=ABOUT_ES, body_en=ABOUT_EN))
    db.session.commit()
