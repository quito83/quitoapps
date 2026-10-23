"""Punto de entrada de QuitoApps (Vercel detecta `app` en este archivo)."""
from quitoapps import create_app

app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
