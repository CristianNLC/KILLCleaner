"""Rutas de datos de KILLCleaner.

Funciona igual ejecutando desde el código fuente y desde el .exe empaquetado:
- Desde fuente: todo queda dentro del proyecto (carpeta ``data/`` y ``logs/``).
- Desde .exe: se usa %LOCALAPPDATA%\\KILLCleaner para no intentar escribir
  dentro de "Program Files", donde no hay permisos de escritura.
"""

import os
import re
import sys

APP_NAME = "KILLCleaner"


def project_dir() -> str:
    """Directorio raíz del proyecto (donde vive app.pyw)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_frozen() -> bool:
    """True si se está ejecutando como binario empaquetado con PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def _user_data_base() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


def data_dir() -> str:
    """Carpeta de configuración (config.json)."""
    if is_frozen():
        return _user_data_base()
    return os.path.join(project_dir(), "data")


def logs_dir() -> str:
    """Carpeta de registros de las limpiezas automáticas."""
    if is_frozen():
        return os.path.join(_user_data_base(), "logs")
    return os.path.join(project_dir(), "logs")


def ensure_dir(path: str) -> str:
    """Crea la carpeta si no existe y la devuelve."""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return path


def system_drive() -> str:
    """Letra de la unidad donde está instalado Windows, por ejemplo ``C:``.

    Evita asumir ``C:`` en equipos con Windows en otra unidad o letra.
    """
    drive = os.environ.get("SystemDrive", "C:").strip().upper()
    return drive if re.fullmatch(r"[A-Z]:", drive) else "C:"


MAX_PATH = 260


def extended_path(path: str) -> str:
    """Devuelve una ruta absoluta con prefijo ``\\\\?\\`` si supera MAX_PATH.

    El prefijo permite que las API de Windows trabajen con rutas de más de 260
    caracteres aunque la directiva ``LongPathsEnabled`` esté desactivada. Para
    rutas cortas se devuelve la ruta absoluta sin prefijo.
    """
    if not path:
        return path
    if path.startswith("\\\\?\\"):
        return path

    absolute = os.path.abspath(path)
    if len(absolute) < MAX_PATH:
        return absolute
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute[2:]
    return "\\\\?\\" + absolute


def display_path(path: str) -> str:
    """Quita el prefijo ``\\\\?\\`` para mostrar la ruta al usuario."""
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[8:]
    if path.startswith("\\\\?\\"):
        return path[4:]
    return path
