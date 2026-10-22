"""Punto de entrada de QuitoApps con diagnóstico automático de errores de arranque."""
import traceback

try:
    from quitoapps import create_app

    app = create_app()
except Exception as exc:  # noqa: BLE001
    from flask import Flask, Response

    tb_text = traceback.format_exc()
    app = Flask(__name__)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def boot_error(path):
        return Response(f"STARTUP ERROR:\n\n{tb_text}", status=500, mimetype="text/plain")


if __name__ == "__main__":
    app.run(debug=True)
