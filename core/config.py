"""Configuración persistente de KILLCleaner (``config.json``).

Se guarda en la carpeta de datos (``data/`` desde fuente,
``%LOCALAPPDATA%\\KILLCleaner`` desde el .exe). El archivo es opcional: si falta
o está dañado se usan los valores por defecto.

Claves conocidas:
- ``theme``: "Dark", "Light" o "System".
- ``exclusions``: carpetas que la limpieza nunca debe tocar.
- ``restore_point_before_clean``: crear un punto de restauración antes de la
  limpieza profunda.
"""

import json
import os
import threading

from core.app_paths import data_dir

_LOCK = threading.RLock()

DEFAULTS = {
    "theme": "Dark",
    "exclusions": [],
    "restore_point_before_clean": True,
}

VALID_THEMES = ("Dark", "Light", "System")


def config_path():
    """Ruta absoluta del archivo de configuración."""
    return os.path.join(data_dir(), "config.json")


def _sanitize(data):
    """Devuelve una copia válida de la configuración, conservando claves extra."""
    merged = dict(DEFAULTS)
    if isinstance(data, dict):
        merged.update(data)

    if merged.get("theme") not in VALID_THEMES:
        merged["theme"] = DEFAULTS["theme"]

    exclusions = merged.get("exclusions")
    clean = []
    if isinstance(exclusions, list):
        for item in exclusions:
            if not isinstance(item, str) or not item.strip():
                continue
            try:
                value = os.path.normpath(item.strip())
            except Exception:
                continue
            if value not in clean:
                clean.append(value)
    merged["exclusions"] = clean
    merged["restore_point_before_clean"] = bool(
        merged.get("restore_point_before_clean", True)
    )
    return merged


def load_config():
    """Lee la configuración; nunca lanza excepciones."""
    with _LOCK:
        try:
            with open(config_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        return _sanitize(data)


def save_config(data):
    """Escribe la configuración de forma atómica. Devuelve True si tuvo éxito."""
    payload = _sanitize(data)
    with _LOCK:
        try:
            folder = os.path.dirname(config_path())
            if folder:
                os.makedirs(folder, exist_ok=True)
            tmp = config_path() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
            os.replace(tmp, config_path())
            return True
        except Exception:
            return False


def get_value(key, default=None):
    return load_config().get(key, default)


def set_value(key, value):
    data = load_config()
    data[key] = value
    return save_config(data)


def get_exclusions():
    """Lista de carpetas excluidas de análisis y limpieza."""
    return load_config()["exclusions"]


def add_exclusion(path):
    """Añade una carpeta a las exclusiones. Devuelve (ok, mensaje)."""
    if not path:
        return False, "No se seleccionó ninguna carpeta."
    try:
        full = os.path.abspath(path)
    except Exception as e:
        return False, f"Ruta no válida: {e}"

    if not os.path.isdir(full):
        return False, "La carpeta no existe o no es accesible."
    if os.path.splitdrive(full)[1] in ("\\", "/"):
        return False, "No se puede excluir la raíz de una unidad completa."

    data = load_config()
    exclusions = data["exclusions"]
    for existing in exclusions:
        if os.path.normcase(existing) == os.path.normcase(full):
            return False, "Esa carpeta ya está en la lista."

    exclusions.append(full)
    data["exclusions"] = exclusions
    if not save_config(data):
        return False, "No se pudo guardar la configuración."
    return True, f"Carpeta excluida: {full}"


def remove_exclusion(path):
    """Quita una carpeta de las exclusiones. Devuelve (ok, mensaje)."""
    data = load_config()
    try:
        target = os.path.normcase(os.path.abspath(path))
    except Exception:
        return False, "Ruta no válida."

    remaining = [
        item
        for item in data["exclusions"]
        if os.path.normcase(os.path.abspath(item)) != target
    ]
    if len(remaining) == len(data["exclusions"]):
        return False, "La carpeta no estaba en la lista."

    data["exclusions"] = remaining
    if not save_config(data):
        return False, "No se pudo guardar la configuración."
    return True, "Exclusión eliminada."
