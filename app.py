"""Punto de entrada de QuitoApps.

- Local:  .venv\\Scripts\\flask run --debug
- Vercel: detecta automáticamente la variable `app` de este archivo.
"""
from quitoapps import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
