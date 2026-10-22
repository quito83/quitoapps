"""Soporte de idiomas: prefijo /es/ o /en/ en las URLs públicas."""
from flask import g, redirect, request, url_for

from . import DEFAULT_LANGUAGE, LANGUAGES, select_locale

LANGUAGE_NAMES = {"es": "Español", "en": "English"}


def register_i18n(app):
    @app.url_value_preprocessor
    def pull_lang_code(endpoint, values):
        if values and "lang_code" in values:
            g.lang_code = values.pop("lang_code")

    @app.url_defaults
    def add_lang_code(endpoint, values):
        if "lang_code" in values or not getattr(g, "lang_code", None):
            return
        if app.url_map.is_endpoint_expecting(endpoint, "lang_code"):
            values["lang_code"] = g.lang_code

    @app.before_request
    def ensure_lang():
        if not getattr(g, "lang_code", None):
            g.lang_code = select_locale()

    @app.route("/")
    def root():
        lang = request.accept_languages.best_match(LANGUAGES) or DEFAULT_LANGUAGE
        return redirect(url_for("public.index", lang_code=lang))

    @app.context_processor
    def inject_i18n():
        return {
            "current_lang": getattr(g, "lang_code", DEFAULT_LANGUAGE),
            "languages": LANGUAGES,
            "language_names": LANGUAGE_NAMES,
            "lang_switch_url": lang_switch_url,
        }


def lang_switch_url(code):
    """URL de la página actual en otro idioma (conserva parámetros)."""
    rule = request.url_rule
    if request.endpoint and rule is not None and "lang_code" in rule.arguments:
        args = dict(request.view_args or {})
        args.update(request.args.to_dict())
        args["lang_code"] = code
        return url_for(request.endpoint, **args)
    return url_for("public.index", lang_code=code)
