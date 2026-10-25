"""Credenciales locales de KILLCleaner.

Ninguna credencial se guarda en el código ni se versiona. Se resuelven en este
orden, usando el primer valor disponible:

1. Variables de entorno:
   - ``KILLCLEANER_FEEDBACK_KEY``
   - ``KILLCLEANER_DONATION_EMAIL``
2. ``secrets.json`` en la carpeta de datos:
   - desde fuente: ``data/secrets.json``
   - desde .exe: ``%LOCALAPPDATA%\\KILLCleaner\\secrets.json``
3. ``secrets.json`` empaquetado en el .exe o situado junto a él.

Plantilla lista para copiar: ``data/secrets.example.json``.
"""

import json
import os
import sys
from functools import lru_cache

from core.app_paths import data_dir

ENV_FEEDBACK_KEY = "KILLCLEANER_FEEDBACK_KEY"
ENV_DONATION_EMAIL = "KILLCLEANER_DONATION_EMAIL"


def _candidate_files():
    files = [os.path.join(data_dir(), "secrets.json")]
    if getattr(sys, "frozen", False):
        bundle = getattr(sys, "_MEIPASS", "")
        if bundle:
            files.append(os.path.join(bundle, "secrets.json"))
        files.append(os.path.join(os.path.dirname(sys.executable), "secrets.json"))
    return files


@lru_cache(maxsize=1)
def _load():
    """Devuelve el primer secrets.json válido que se encuentre."""
    for path in _candidate_files():
        try:
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def get_feedback_key() -> str:
    """Clave de Web3Forms para el buzón de sugerencias ('' si no hay)."""
    value = os.environ.get(ENV_FEEDBACK_KEY) or _load().get("feedback_access_key") or ""
    return str(value).strip()


def get_donation_email() -> str:
    """Cuenta de Mercado Pago para donaciones ('' si no hay)."""
    value = os.environ.get(ENV_DONATION_EMAIL) or _load().get("donation_email") or ""
    return str(value).strip()


def reload():
    """Olvida los valores cacheados (útil si el archivo cambia en caliente)."""
    _load.cache_clear()
