"""Formularios del panel de administración (interfaz en español)."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, MultipleFileField
from wtforms import (
    BooleanField,
    IntegerField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
    URLField,
)
from wtforms.validators import DataRequired, Length, Optional, Regexp, URL
from wtforms.widgets import CheckboxInput, ListWidget

from ..models import LINK_KINDS, STATUSES

SLUG = Regexp(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", message="Solo minúsculas, números y guiones (ej. mi-app).")
IMAGES = FileAllowed(["png", "jpg", "jpeg", "webp", "gif"], "Solo imágenes PNG, JPG, WEBP o GIF.")

STATUS_CHOICES = [("dev", "En desarrollo"), ("beta", "Beta"), ("published", "Publicada")]
assert [c[0] for c in STATUS_CHOICES] == list(STATUSES)

LINK_FIELD_LABELS = {
    "demo": "Demo en vivo",
    "web": "Sitio web",
    "download": "Descarga",
    "repo": "Repositorio / código",
    "play_store": "Google Play",
    "app_store": "App Store",
    "ms_store": "Microsoft Store",
}


class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class LoginForm(FlaskForm):
    username = StringField("Usuario", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    remember = BooleanField("Recordarme")


class AppForm(FlaskForm):
    slug = StringField("Slug (URL)", validators=[DataRequired(), Length(max=120), SLUG])
    status = SelectField("Estado", choices=STATUS_CHOICES)
    category_id = SelectField("Categoría", coerce=int)
    tag_ids = MultiCheckboxField("Etiquetas", coerce=int)
    featured = BooleanField("Destacada en portada")
    visible = BooleanField("Visible en el sitio", default=True)
    sort_order = IntegerField("Orden (menor = primero)", default=0, validators=[Optional()])

    name_es = StringField("Nombre (ES)", validators=[DataRequired(), Length(max=120)])
    short_es = StringField("Descripción corta (ES)", validators=[DataRequired(), Length(max=300)])
    long_es = TextAreaField("Descripción larga (ES, Markdown)")
    name_en = StringField("Name (EN)", validators=[DataRequired(), Length(max=120)])
    short_en = StringField("Short description (EN)", validators=[DataRequired(), Length(max=300)])
    long_en = TextAreaField("Long description (EN, Markdown)")

    icon = FileField("Icono / logo", validators=[IMAGES])
    remove_icon = BooleanField("Quitar icono actual")
    screenshots = MultipleFileField("Agregar capturas", validators=[IMAGES])


# Un campo URL por cada tipo de enlace: link_demo, link_repo, ...
for _kind in LINK_KINDS:
    setattr(
        AppForm,
        f"link_{_kind}",
        URLField(LINK_FIELD_LABELS[_kind], validators=[Optional(), URL(require_tld=False), Length(max=500)]),
    )


class TaxonomyForm(FlaskForm):
    """Categorías y etiquetas comparten estructura."""

    slug = StringField("Slug", validators=[DataRequired(), Length(max=80), SLUG])
    name_es = StringField("Nombre (ES)", validators=[DataRequired(), Length(max=80)])
    name_en = StringField("Nombre (EN)", validators=[DataRequired(), Length(max=80)])
    sort_order = IntegerField("Orden", default=0, validators=[Optional()])


class PageForm(FlaskForm):
    body_es = TextAreaField("Contenido (ES, Markdown)")
    body_en = TextAreaField("Content (EN, Markdown)")


class EmptyForm(FlaskForm):
    """Solo para el token CSRF en botones POST (borrar, etc.)."""
