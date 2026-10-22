"""Punto de entrada estándar de QuitoApps para Vercel Serverless."""
import sys
import os

# Asegura que el directorio raíz del proyecto esté en sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from quitoapps import create_app

app = create_app()
